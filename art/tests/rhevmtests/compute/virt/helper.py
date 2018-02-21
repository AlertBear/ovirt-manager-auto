#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for virt and network migration job
"""
import itertools
import os
import shlex
import time

import re
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from art.rhevm_api.data_struct import data_structures as data_struct
import art.core_api.validator as validator
import art.rhevm_api.resources as resources
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config as config_virt
import rhevmtests.storage.helpers as storage_helpers
from art import test_handler
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
    vmpools as ll_vmpools,
    clusters as ll_clusters,
    general as ll_general,
    disks as ll_disks,
    events as ll_events,
)
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.unittest_lib import testflow
from rhevmtests import helpers
from rhevmtests.networking import config
from utilities import utils
from art.rhevm_api.utils import jobs
from utilities.rhevm_tools import errors

logger = logging.getLogger("Virt_Helper")

DEFAULT_JOB_TIMEOUT = 600
VDSM_LOG = "/var/log/vdsm/vdsm.log"
SERVICE_STATUS = "id"
LOAD_MEMORY_FILE = "tests/rhevmtests/compute/virt/migration/memoryLoad.py"
DESTINATION_PATH = "/tmp/memoryLoad.py"
DELAY_FOR_SCRIPT = 120
MEMORY_USAGE = 60
DELAY_FOR_SNAPSHOT = 60
RUN_SCRIPT_COMMAND = (
    'python /tmp/memoryLoad.py -s %s -r %s &> /tmp/OUT1 & echo $!'
)
VIRSH_VM_LIST_CMD = "virsh -r list | grep "
V2V_IMPORT_TIMEOUT = 1500

# cloud init settings
NIC_CONFIGURATION = data_struct.NicConfiguration(
    name=config_virt.CLOUD_INIT_NIC_NAME, ip=None, boot_protocol='dhcp',
    on_boot=True
)
SCRIPT_CONTENT = "test_cloud_init"
CUSTOM_SCRIPT = (
    """#custom cloud_init_script
write_files:
- content: %s
  path: /tmp/test.txt
  permissions: '0644'
runcmd:
 - [ systemctl, restart, network]
"""
) % SCRIPT_CONTENT

# base initialization parameters
initialization_params = {
    'host_name': config_virt.CLOUD_INIT_HOST_NAME,
    'root_password': config.VDC_ROOT_PASSWORD,
    'user_name': config_virt.VM_USER_CLOUD_INIT,
    'timezone': config_virt.NEW_ZEALAND_TZ,
    'dns_servers': config_virt.DNS_SERVER,
    'dns_search': config_virt.DNS_SEARCH,
    'nic_configurations': data_struct.NicConfigurations(
        nic_configuration=[NIC_CONFIGURATION]
    ),
    'custom_script': CUSTOM_SCRIPT
}


test_handler.find_test_file.__test__ = False


def set_host_status(activate=False):
    """
    Set host to operational/maintenance state

    Args:
        activate (bool): activate Host if True, else put into maintenance
    Raises:
            AssertionError: if failed operation
    """

    host_state = "active" if activate else "maintenance"
    func = "activate_host" if activate else "deactivate_host"
    call_func = getattr(ll_hosts, func)
    logger.info("Putting hosts besides first two to %s", host_state)
    for host in config.HOSTS[2:]:
        err = "Couldn't put %s into %s" % (host, host_state)
        assert call_func(True, host), err


def copy_file_to_vm(vm_ip, source_file_path, destination_path):
    """
    Copy file to VM using Machine.

    Args:
        vm_ip (str): VM ip
        source_file_path (str): File location at ART
        destination_path (str): destination path on VM

    Returns:
        bool: Returns False if copy to VM failed, otherwise True
    """
    logger.info(
        "Copy file %s to vm-%s:%s",
        source_file_path,
        vm_ip,
        destination_path
    )
    try:
        host = resources.Host(vm_ip)
        host.users.append(resources.RootUser(config.VMS_LINUX_PW))
        host.copy_to(
            config.ENGINE_HOST,
            test_handler.find_test_file(source_file_path),
            destination_path
        )
    except Exception, e:
        logger.error("Failed to copy file to vm:%s", vm_ip)
        logger.error(e.message)
        return False
    return True


def migration_vms_to_diff_hosts(vms):
    """
    Migrate vms that are on different hosts
    using Jobs, wait for all migration till timeout is finished.
    and check that all vm migrated to different host.

    Args:
        vms (list): Vms list

    Returns:
        bool: True if all finish on time, and migrated to different host
    """
    vm_to_host_before = map_vms_to_hosts(vms)
    my_jobs = []
    for vm in vms:
        migration_kwargs = {"positive": True, "vm": vm}
        job = jobs.Job(ll_vms.migrateVm, (), migration_kwargs)
        my_jobs.append(job)
    logger.info("Start migration for all vms %s", vms)
    job_set = jobs.JobsSet()
    job_set.addJobs(my_jobs)
    job_set.start()
    job_set.join(config.TIMEOUT * len(vms))
    logger.info("Finish migration for all vms %s", vms)
    vm_to_host_after = map_vms_to_hosts(vms)
    logger.info("VM status before: %s", vm_to_host_before)
    logger.info("VM status after: %s", vm_to_host_after)
    if vm_to_host_before != vm_to_host_after:
        logger.info("Migration pass, all vms migrate")
        return True
    return False


def map_vms_to_hosts(vms):
    """"
    Maps between Vms and their hosts

    Args:
        vms (list): VMs list

    Returns
        dict: VMs to Hosts
    """

    vm_to_host_list = {}
    for vm in vms:
        host = ll_vms.get_vm_host(vm)
        vm_to_host_list[vm] = host
    return vm_to_host_list


def compare_resources_lists(before_list, after_list):
    """
    Compare between list pending resources on hosts

    Args:
        before_list (list): list of hosts with their resources
        after_list (list): list of hosts with their resources

    Returns:
        bool: True if list are equals else False
    """

    logging.info("Compare pending resources on hosts")
    for host_status_before in before_list:
        for host_status_after in after_list:
            if host_status_before[0] is host_status_after[0]:
                if cmp(host_status_before, host_status_after) != 0:
                    logging.error("Host: %s resources did not clear",
                                  host_status_before[0])
                    return False
    logging.info("Resources cleaned from hosts")
    return True


def load_vm_memory_with_load_tool(
    vm_name,
    load=500,
    time_to_run=60,
    start_vm=True
):
    """
    Load VM memory with load tool that install on VM

    Args:
        vm_name (str): VM name
        load (int): Load value in MB
        time_to_run (int): Time to run memory load in sec
        start_vm (bool): start vm if down

    Returns:
        bool: True if load set on VM, False is fail to load VM
    """
    logger.info(
        "Run load %s MB on vm %s for %s sec",
        load, vm_name, time_to_run
    )
    cmd = config_virt.LOAD_VM_COMMAND % (load, time_to_run)
    vm_resource = helpers.get_vm_resource(vm=vm_name, start_vm=start_vm)
    if vm_resource.executor().wait_for_connectivity_state(positive=True):
        ps_id = vm_resource.run_command(command=shlex.split(cmd))[1]
        time.sleep(5)
        logger.info("ps id: %s", ps_id)
        return True
    else:
        logger.error("Failed to connect to vm %s", vm_name)
        return False


def create_base_vm(
    vm_name,
    cluster=config_virt.CLUSTER_NAME[0], memory=config.GB,
    os_type=config_virt.VM_OS_TYPE, vm_type=config_virt.VM_TYPE,
    display_type=config_virt.VM_DISPLAY_TYPE,
    disk_type=config.DISK_TYPE_DATA, storage_domain=None,
    add_disk=False, vm_parameters=None
):
    """
    Create vm with disk or nic

    Args:
        vm_name (str): VM name
        cluster (str): cluster name
        memory (int): memory size
        os_type (str): vm os type
        vm_type (str): vm type
        display_type (str): display type
        vm_parameters (dict): vm parameter to update after creation
        add_disk (bool): If True add disk to VM after creation
        disk_type (str): disk type, default set to data
        storage_domain (str): master storage domain

    Returns:
        bool: True if all operations succeed Else False
    """

    if not ll_vms.addVm(
        positive=True, name=vm_name,
        cluster=cluster,
        memory=memory,
        os_type=os_type,
        type=vm_type,
        display_type=display_type

    ):
        return False
    if add_disk:
        logger.info("Add disk to vm %s", vm_name)
        if not storage_domain:
            storage_domain, _, _ = get_storage_domains()
        if not ll_vms.addDisk(
            True,
            vm=vm_name,
            provisioned_size=config.GB,
            storagedomain=storage_domain,
            type=disk_type,
            format=config.DISK_FORMAT_COW,
            interface=config.INTERFACE_VIRTIO,
            bootable=True
        ):
            logger.error("Failed to add disk to vm %s" % vm_name)
            return False

    if vm_parameters:
        if not ll_vms.updateVm(
            positive=True, vm=vm_name, **vm_parameters
        ):
            return False
    return True


def create_vm_from_template(
    vm_name,
    cluster=config.CLUSTER_NAME[0],
    template=config.TEMPLATE_NAME[0],
    vm_parameters=None
):
    """
    Create VM from given template, with optional parameters

    Args:
        vm_name (str): VM name
        cluster (str): cluster name
        template (str): template name
        vm_parameters (dict): vm parameter to update after creation

    Returns:
        bool: True if all operations succeed, Else False
    """

    if not ll_vms.addVm(
        True,
        name=vm_name,
        cluster=cluster,
        template=template,
    ):
        return False

    if vm_parameters:
        if not ll_vms.updateVm(
            positive=True, vm=vm_name, **vm_parameters
        ):
            return False
    return True


def check_display_parameters(vm_name, display_type):
    """
    Check display parameters

    Args:
        vm_name (str): VM name
        display_type (str): display type on vm

    Returns:
         bool: True if display port/address exists, else False
    """

    if display_type != config_virt.SPICE:
        logger.info("Check if display port exist")
        if not ll_vms.get_vm_display_port(vm_name):
            logger.info("Vm %s display port does not exist", vm_name)
            return False
    logger.info("Check if display address exist")
    if not ll_vms.get_vm_display_address(vm_name):
        logger.info("Vm %s display address does not exist", vm_name)
        return False
    return True


def create_file_in_vm(
    vm, vm_resource, path=config_virt.TEMP_PATH, size_in_mb=1, all_disks=False
):
    """
    Create an empty file in vm using vm resource entity

    Args:
        vm (str): Vm name
        vm_resource (Host resource): Resource for the vm
        path (str): path to locate the file
        size_in_mb (int): size of create file in MB
        all_disks (bool): True if files should be created on all vm's
            disks, False if only on boot device

    Returns:
        list: list of paths to the file/s created on the vm

    Raises:
        VMException: If failed to create file
    """
    files_paths = list()
    logger.info(
        "attempting to create a file of size: %sMB in vm: %s", size_in_mb, vm
    )
    full_path = os.path.join(path, config_virt.FILE_NAME)
    files_paths.append(full_path)
    write_file_with_dd_command(full_path, size_in_mb, vm, vm_resource)
    if all_disks:
        vm_disks = ll_vms.getVmDisks(vm)
        disks_aliases = [
            disk.get_alias() for disk in vm_disks if not
            ll_vms.is_bootable_disk(vm, disk.get_id())
        ]
        for disk_alias in disks_aliases:
            result, target_path = storage_helpers.create_fs_on_disk(
                vm, disk_alias, vm_resource.executor()
            )
            if not result:
                raise exceptions.VMException(
                    "Failed to create a file system for disk: %s on vm %s" %
                    disk_alias, vm
                )
            full_path = os.path.join(target_path, config_virt.FILE_NAME)
            files_paths.append(full_path)
            write_file_with_dd_command(full_path, size_in_mb, vm, vm_resource)
    return files_paths


def write_file_with_dd_command(full_path, size_in_mb, vm, vm_resource):
    """
    Write to given file with dd command

    Args:
    full_path (str): File path
    size_in_mb (int): Amount of MB to write to file
    vm (str): VM name
    vm_resource (Host resource): VM resource

    Raises:
        VMException: If failed to create file
    """
    cmd = config_virt.DD_CREATE_FILE_CMD % (full_path, size_in_mb)
    if vm_resource.run_command(shlex.split(cmd))[0]:
        raise exceptions.VMException(
            "Failed to create an empty file on vm: '%s'" % vm
        )


def check_if_file_exist(
    positive,
    vm,
    vm_resource,
    path=config_virt.TEMP_PATH,
    full_path=False
):
    """
    Checks if file (name of file in config) exist or not in the vm using vm
    resource entity

    Args:
        positive (bool): Signifies the expected result
        vm (str): Vm name
        vm_resource (host resource): Command executor for the vm
        path (str): path where to find the file
        full_path (bool): True if the given path is a full path, False if path
            is only path to file's folder

    Raises:
        VMException: If file exist
    """
    if not full_path:
        path = os.path.join(path, config_virt.FILE_NAME)
    testflow.step(
        "checking if file: %s exists in vm: %s. expecting result: %s",
        path, vm, positive
    )
    file_exists = vm_resource.fs.exists(path)
    if not (file_exists == positive):
        raise exceptions.VMException("Error: file exists on vm: '%s'" % vm)


def reboot_stateless_vm(vm_name):
    """
    Reboot stateless VM:
    1. Stop VM
    2. Wait until stateless snapshot removed
    3. Start VM

    Args:
        vm_name (str): Vm name

    Returns:
        bool: True if VM successfully rebooted else False
    """

    logger.info("Reboot stateless VM, vm name: %s", vm_name)
    if hl_vms.stop_stateless_vm(vm_name):
        if ll_vms.startVm(positive=True, vm=vm_name, wait_for_ip=True):
            return True
    return False


def get_storage_domains():
    """
    Get the storage domains: master,export,non master

    Returns
        tuple: returns storage domains (master,export,non master)
    """

    master_domain = (
        ll_sd.get_master_storage_domain_name(config.DC_NAME[0])
    )
    non_master_domains = (
        ll_sd.findNonMasterStorageDomains(
            True, config.DC_NAME[0]
        )[1]['nonMasterDomains']
    )
    export_domain = (
        ll_sd.findExportStorageDomains(config.DC_NAME[0])[0]
    )
    master_domain_type = ll_sd.get_storage_domain_storage_type(master_domain)
    non_master_domain = None
    for domain in non_master_domains:
        if ll_sd.get_storage_domain_storage_type(domain) == master_domain_type:
            non_master_domain = domain
            break
    if non_master_domain is None:
        logger.error(
            "No storage domain with the same type of master domain (%s)"
            "exists in the system", master_domain_type
        )
    return master_domain, export_domain, non_master_domain


def get_all_vm_in_cluster(cluster_name, skip=None):
    """
    Get all vms in cluster except skip

    Args:
        cluster_name (str): cluster name
        skip (list): list of vms to skip

    Returns:
         list: List of VMs in cluster

    """
    vms_in_cluster = []
    vms_list = ll_vms.get_vms_from_cluster(cluster=cluster_name)
    for vm_name in vms_list:
        if vm_name not in skip:
            vms_in_cluster.append(vm_name)
    return vms_in_cluster


def get_err_msg(action=None, vm_name=None):
    """
    Get error massage according to action and vm name, or action

    Args:
        action (str): action name
        vm_name (str): vm name

    Returns:
        str: return error massage
    """
    if vm_name:
        return "Failed to %s on VM: %s", action, vm_name
    else:
        return "Failed to %s", action


def get_vm_id(vm_name):
    """
    Get running vm id from virsh

    Args:
        vm_name (str): VM name

    Return:
        str: vm id

    Raise:
         HostException: If failed to run command
    """
    host_resource = helpers.get_host_resource_of_running_vm(vm_name)
    cmd = shlex.split(" ".join((config_virt.VIRSH_VM_LIST_CMD, vm_name)))
    rc, out, err = host_resource.executor().run_cmd(cmd)
    if rc:
        raise exceptions.HostException(
            "Failed to run virsh cmd: %s on: %s, err: %s"
            % (host_resource, cmd, err)
        )
    vm_id = out.split()[0]
    logger.info("VM pid is %s", vm_id)
    return vm_id


def compare_dictionaries(expected, actual):
    """
    Gets two dictionaries with similar keys and compares the values.
    Returns True if the dictionaries are similar and False otherwise.

    Args:
        expected (dict): The dictionary with expected values.
        actual (dict): The dictionary with actual values.

    Returns:
        True if expected == actual, False otherwise.
    """
    diff_keys = [k for k in expected if expected[k] != actual[k]]
    for k in diff_keys:
        logger.error(
            "Wrong result for key: %s. Expected: %s, Actual: %s.",
            k, expected[k], actual[k]
        )
    return not diff_keys


@ll_general.generate_logs()
def remove_all_pools_from_cluster(cluster):
    """
    Removes all pools in a given cluster

    Args:
        cluster (str): Name of the chosen cluster.
    """
    vm_pools_in_cluster = ll_clusters.get_all_vm_pools_in_cluster(cluster)
    all_vms_in_cluster_pools = list()
    for pool in vm_pools_in_cluster:
        vms_in_pool = ll_vmpools.get_vms_in_pool_by_name(pool)
        if not ll_vmpools.removeVmPool(True, pool):
            continue
        all_vms_in_cluster_pools.extend(vms_in_pool)
    if all_vms_in_cluster_pools:
        try:
            ll_vms.waitForVmsGone(True, all_vms_in_cluster_pools)
        except APITimeout:
            logger.error(
                "Could not remove all pool vms from cluster: %s", cluster
            )


@ll_general.generate_logs()
def wait_for_vm_fqdn(
    vm_name, timeout=config.VM_IP_TIMEOUT, sleep=config.SAMPLER_SLEEP
):
    """
    Wait for vm's fqdn.

    Args:
        vm_name (str): Name of the vm.
        timeout (int): Timeout for sampling the result.
        sleep (int): Time to wait between samples.

    Returns:
         True if got vm's fqdn within the timeout period, False otherwise.
    """
    sampler = test_utils.TimeoutingSampler(
        timeout=timeout, sleep=sleep, func=ll_vms.get_vm_obj, vm_name=vm_name
    )
    try:
        for vm_object in sampler:
            if vm_object.get_fqdn():
                return True
    except APITimeout:
        return False


def run_command_on_host(cmd, host_resource):
    """
    Run command on host resource and return output, in case of error
    return None.

    Args:
        cmd (list): command to run
        host_resource (Host): host resource

    Returns:
        str: return command out, in case of error returns None.
    """
    rc, out, err = host_resource.executor().run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to run cmd: %s on: %s, err: %s"
            % (cmd, host_resource, err)
        )
        return None
    return out


def check_drivers(driver_list_input, number_of_disks, number_of_threads):
    """
    Check thread allocation for disks.

    Args:
        driver_list_input (str): 'virsh' command output
        number_of_disks (int): expected number of disks
        number_of_threads (int): configure number of threads

    Returns:
        bool: True if thread allocate to each disk and number of disks is
              as expected, otherwise False
    """

    counter = 1
    drivers_list = []
    drivers = driver_list_input.strip().split("\n")
    logger.info("Disk drivers lists: %s", drivers)
    for driver_info in drivers:
        drivers_list.append(
            int(shlex.split(driver_info)[6].split("=")[1].split("/")[0])
        )
    actual_number_of_disks = len(drivers_list)
    if number_of_disks != actual_number_of_disks:
        logger.error(
            "Number of disks is not as expected\n"
            "[Disk numbers: actual#:%d ,expected#:%d]",
            actual_number_of_disks, number_of_disks
        )
        return False
    if number_of_threads >= actual_number_of_disks:
        for driver in drivers_list:
            if check_thread_number(disk_id=driver, counter=counter):
                counter += 1
            else:
                return False
    else:  # number of threads is less then disks
        for driver in drivers_list:
            if check_thread_number(disk_id=driver, counter=counter):
                counter += 1
            else:
                return False
            if counter > number_of_threads:
                counter = 1
    return True


def check_thread_number(disk_id, counter):
    """
    check that disk is attached to expected thread number.

    Args:
        disk_id (int): disk id
        counter (int): thread number

    Returns:
        bool: Return True if disk is attached to expected thread number,
        otherwise False

    """
    if disk_id != counter:
        logger.error("Thread not attached to disk")
        return False
    return True


def check_clone_vm(clone_vm_name, base_vm_name):
    """
    Check clone vm
        1. Check Nic: check the MAC address is diff then base
        2. Check that clone vm has the same attributes as base vm

    Args:
        clone_vm_name (str): clone vm name
        base_vm_name (str): base vm name

    Returns:
         bool: Return True if all checks pass, else return False
    """
    logger.info("Check Nic info")
    clone_vm_mac_address = ll_vms.get_vm_nic_mac_address(vm=clone_vm_name)
    base_vm_mac_address = ll_vms.get_vm_nic_mac_address(vm=base_vm_name)
    if clone_vm_mac_address == base_vm_mac_address:
        logger.error(
            "MAC addresses are the same,\n"
            "clone vm mac address: %s\n"
            "base vm mac address:  %s",
            clone_vm_mac_address, base_vm_mac_address
        )
        return False
    logger.info("Check VM attributes")
    logger.info("Check disks ids")
    base_vm_disks_ids = ll_vms.getObjDisks(
        name=base_vm_name, get_href=False
    )
    clone_vm_disks_ids = ll_disks.getObjDisks(
        name=base_vm_name, get_href=False
    )
    if base_vm_disks_ids == clone_vm_disks_ids:
        logger.error(
            "Disks ids are the same, should have different ids, see ids:\n"
            "base vm: %s \nclone vm: %s",
            base_vm_disks_ids, clone_vm_disks_ids
        )
        return False
    vm_obj_clone_vm = ll_vms.get_vm_obj(clone_vm_name)
    vm_obj_base_vm = ll_vms.get_vm_obj(base_vm_name)
    return validator.compareElements(
        vm_obj_base_vm, vm_obj_clone_vm, logger=logger, root='Comparator',
        ignore=config_virt.VALIDATOR_IGNORE_LIST
    )


def check_disk_contents_on_clone_vm(clone_vm_name):
    """
    Check disk content:
    start clone and check that new disk contains the same file as in base disk

    Args:
        clone_vm_name (str): clone vm name

    Raises:
        VMException: If file don't exist
    """
    assert ll_vms.startVm(
        positive=True, vm=clone_vm_name, wait_for_status=config.VM_UP
    )
    logger.info("Check disk content")
    vm_resource = helpers.get_vm_resource(clone_vm_name)
    testflow.step("Verify that file exists after vm restart")
    check_if_file_exist(True, clone_vm_name, vm_resource, path='/home/')


def clone_same_vm_twice(base_vm_name, clone_vm_list):
    """
    Clone same vm simultaneous

    Args:
        base_vm_name (str): vm that we clone from
        clone_vm_list(list): list of vm name to clone
    """
    testflow.step("Clone vm")
    job_list_parameters = {}
    clone_jobs = {}
    for i, clone_vm_name in zip(range(0, len(clone_vm_list)), clone_vm_list):
        wait = True if i == 0 else False
        job_list_parameters["clone_job_kwargs_{0}".format(i)] = {
            'positive': True,
            'vm': base_vm_name,
            'clone_vm_name': clone_vm_name,
            'wait': wait
        }
    logger.info(job_list_parameters)
    for i in range(0, len(clone_vm_list)+1):
        clone_jobs["job_{0}".format(i)] = jobs.Job(
            hl_vms.clone_vm,
            (),
            job_list_parameters["clone_job_kwargs_{0}".format(i)]
        )
    logger.info(clone_jobs)
    job_set = jobs.JobsSet()
    jobs_list = clone_jobs.values()
    job_set.addJobs(jobs_list)
    job_set.start()
    job_set.join()
    return jobs_list[0].result and not jobs_list[1].result


def remove_vm_from_storage_domain(vm_name, export_domain):
    """
    Remove the VM from export storage

    Args:
        vm_name (str): name of the vm
        export_domain (str): export domain name

    Returns:
        bool: Return True if vm removed form export domain, otherwise False
    """

    if ll_vms.is_vm_exists_in_export_domain(vm_name, export_domain):
        return ll_vms.remove_vm_from_export_domain(
            True, vm_name, config.DC_NAME[0], export_domain
        )


def job_runner(
    job_name,
    kwargs_info,
    job_method_name,
    vms_list,
    timeout=config_virt.DEFAULT_JOB_TIMEOUT
):
    """
    Create job set according to given name and parameters,
    And run the jobs on vms list. Returns status in the end

    Args:
        job_name (str): Job name
        kwargs_info (dict): Execute method parameters
        job_method_name (obj): Method to execute
        vms_list (list): List of vms to run the method on
        timeout (int): timeout for each job
            Note: Job will raise exception if the jobs don't finish
            after the specified timeout.

    Returns:
        bool: True if all jobs pass, otherwise False
    """
    jobs_info = {}
    for vm_name in vms_list:
        jobs_info['{0}_{1}_job'.format(vm_name, job_name)] = jobs.Job(
            job_method_name, (), kwargs_info[vm_name]
        )
    logger.info("jobs info:")
    for job_key in jobs_info.keys():
        logging.info("name: %s\ninfo: %s", job_key, jobs_info[job_key])

    job_set = jobs.JobsSet()
    job_set.addJobs(jobs_info.values())
    job_set.start()
    job_set.join(timeout)
    for job_key in jobs_info.keys():
        if not jobs_info[job_key].result:
            logger.error(
                "Job %s failed\nSee exception info: %s",
                job_key,
                jobs_info[job_key].exception
            )
            return False
    return True


def test_basic_search_params(positive, api, query, resource_name):
    """
    Test that preform basic Vm queries.
    Args:
        positive (bool): The test type, True for positive and False
                         Negative.
        api (object): getApi object, Example: VM_API
        query(str): The query to preform
        resource_name (str): test resource name Example: vm, template

    Returns:
        bool: True if resource found, else False
    """
    log = "POSITIVE" if positive else "NEGATIVE"
    testflow.step(
        "Performing %s Test, query: %s", log, query
    )
    vms = helpers.search_object(
        util=api,
        query=query
    )
    return positive == (resource_name in vms)


@ll_general.generate_logs()
def verify_ssh(vm_name):
    """
    Verify if SSH is working correctly.

    Args:
        vm_name (str): Name of VM to verify ssh on.

    Returns:
        bool: True if SSH works fine, otherwise - False.

    """
    host_resource = helpers.get_vm_resource(vm_name)
    return host_resource.executor().is_connective()


def wait_for_v2v_import_event(vm_name, cluster, timeout=V2V_IMPORT_TIMEOUT):
    """
    Waits until engine reports a successful import of the vm via v2v

    Args:
        vm_name (str): Name given to the imported vm
        cluster (str): Cluster name to which the vm is imported
        timeout (int): Time to wait until vm import is done

    Returns:
        bool: True if the event was find within timeout
    """
    data_center = ll_clusters.get_cluster_data_center_name(cluster)
    event_message = (
        "Vm %s was imported successfully to Data Center %s, Cluster %s" %
        (vm_name, data_center, cluster)
    )
    last_event = ll_events.get_max_event_id()
    return ll_events.wait_for_event(
        query=event_message, start_id=last_event, timeout=timeout
    )


def compare_vm_parameters(param_name, param_value, expected_config):
    """
    Compares two vm parameters taking into account mac address range.
    It checks if actual[nic_mac_address] falls into
    expected[nic_mac_address][start] : expected[nic_mac_address][end] range

    Args:
        param_name (str): vm parameter name
        param_value (str): vm parameter value
        expected_config (dict): expected vm parameters

    Returns:
        bool: True if parameters equal, False otherwise
    """
    if param_name == 'nic_mac_address':
        return utils.MAC(param_value) in utils.MACRange(
                mac_start=utils.MAC(expected_config[param_name]['start']),
                mac_end=utils.MAC(expected_config[param_name]['end'])
            )
    return expected_config[param_name] == param_value


def verify_vm_disk_not_corrupted(vm):
    """
    Connects to vm check if disk is corrupted

    Args:
        vm (str): Name of vm
    """
    logger.info("Start vm %s", vm)
    ll_vms.start_vms([vm])
    vm_resource = helpers.get_vm_resource(vm)
    disk_logical_name = ll_vms.get_vm_disk_logical_name(
        vm_name=vm, disk=ll_vms.get_vm_disks_ids(vm)[0], key='id'
    )
    cmd = shlex.split(config_virt.BAD_BLOCKS_CMD % disk_logical_name)
    rc, out, err = vm_resource.run_command(cmd)
    logger.info("Disk check output:\n%s\n%s", out, err)
    assert not rc, "Failed to run disk check output"
    assert "(0/0/0 errors)" in err, "Bad block check failed"


def get_disk_size_from_file_storage(host_resource, disk_path):
    """
    Connects to spm host and checks the actual disk size of the given disk
    by calling 'du -sh' on the path to the image folder in the domain's mount
    point on the host

    Args:
        host_resource (Host resource): spm host resource
        disk_path (str): the path to the disk's image folder under the host's
            /rhev/data-center folder.


    Returns:
        float: The actual used space in the given lun, in GB
    """
    full_path = os.path.join('/rhev/data-center', disk_path)
    cmd = "du -sh %s" % full_path
    rc, out, _ = host_resource.run_command(shlex.split(cmd))
    if rc:
        logger.error("Failed to get disk actual size of %s", disk_path)
    logger.info("actual used space of disk: %s is: %s", disk_path, out[0])
    return float(out.split()[0].replace('G', ''))


def fetch_actual_disk_size(storage_manager, lun_id=None, disk_path=None):
    """
    This method unifies the calls to methods that get the disk actual size on
    the specific storage domain (different implementation for block storages
    and file storage).

    Args:
        storage_manager (StorageManager or Host resource):
            Instance of StorageManager from storage_api repository in case of
            ISCSI/FC storage, spm host resource in case of NFS/GlusterFS
        lun_id (str): lun id in the storage provider (in case of iscsi/fc)
        disk_path (str): Path to disk in the host's mount point to the SD

    Returns:
        float: The actual used space in the given lun, in GB
    """
    if lun_id:
        return helpers.get_lun_actual_size(storage_manager, lun_id)
    if disk_path:
        return get_disk_size_from_file_storage(storage_manager, disk_path)


def verify_sparsify_success(
    previous_used_space, storage_manager,  lun_id=None, disk_path=None
):
    """
    Checks actual used space in the lun after running the sparsify action.
    And compares between the used space before the action.

    Args:
        previous_used_space (float): used disk size before
        file deleted and sparsify action
        storage_manager (StorageManager or Host resource):
            Instance of StorageManager from storage_api repository in case of
            ISCSI/FC storage, spm host resource in case of NFS/GlusterFS
        lun_id (str): The new lud id create in the test
        disk_path (str): For NFS and gluster file path on disk

    Returns:
        bool: True if the actual size restored, else False
    """
    actual_used_space = fetch_actual_disk_size(
        storage_manager, lun_id, disk_path
    )
    logger.info(
        "Used space on (lun/disk path)after sparsification: %s",
        actual_used_space
    )
    if actual_used_space < previous_used_space:
        logger.info("Sparsification check pass")
        return True
    else:
        logger.error("Sparsification did not restore disk size")
        logger.error(
            "actual_used_space: %s , previous_used_space: %s",
            actual_used_space, previous_used_space
        )
        return False


def get_disk_path(vm_name, storage_domain_name):
    """
    Return disk/s path and id/s according to vma name and storage domain

    Args:
    vm_name (str): VM name
    storage_domain_name (str): Storage domain name

    Returns:
        tuple (str,str): disk path, disk id/s
    """
    disks_ids = ll_vms.get_vm_disks_ids(vm_name)
    disk_path = hl_sd.get_file_storage_disks_paths(
        disks_ids, storage_domain_name
    ).values()[0]
    return disk_path, disks_ids


def delete_file_from_vm(vm, vm_resource, path=config_virt.FULL_PATH):
    """
    Removes file (name of file in config) from the vm

    Args:
        vm (str): Name of vm
        vm_resource (host resource): Command executor for the vm
        path (str): Path to the file

    Returns:
         bool: True if file was removed successfully, False otherwise
    """
    check_if_file_exist(True, vm, vm_resource, path, full_path=True)
    logger.info("Removing file: %s from vm: %s", path, vm)
    return vm_resource.fs.remove(path)


def stop_and_remove_vm_(vm_name):
    """
    Stop and remove VM
    Args:
        vm_name (str): vm name
    Returns:
        bool: True is remove vm successfully
    """

    testflow.teardown("Remove vm %s", vm_name)
    return ll_vms.safely_remove_vms([vm_name])


def prepare_vm_for_sparsification(
    vm_name,
    storage_manager,
    storage_domain_name,
    file_size=config_virt.FILE_SIZE_IN_MB,
    all_disks=False,
    lun_id=None
):
    """
    Prepares the vm for sparsify test.
    This includes starting the vm, creating a file on it, deleting file
    and stopping the vm.

    Args:
        vm_name (vm_name): VM name
        storage_manager (StorageManager or Host resource):
            Instance of StorageManager from storage_api repository in case of
            ISCSI/FC storage, spm host resource in case of NFS/GlusterFS
        storage_domain_name (str): Storage domain name
        file_size (int): Size of the file that will be created on the VM
            (in MB)
        all_disks (bool): Should write to all VM disks
        lun_id (str): Lun id

    Returns:
        tuple(new_used_space, disks_ids)
   """

    disk_path, disks_ids = get_disk_path(
        vm_name=vm_name, storage_domain_name=storage_domain_name
    )
    testflow.step("Start vm %s", vm_name)
    ll_vms.start_vms([vm_name])
    vm_resource = helpers.get_vm_resource(vm_name)
    lun_space = fetch_actual_disk_size(
        storage_manager, lun_id, disk_path
    )
    logger.info("use space before create file: %s", lun_space)
    testflow.step(
        "Write a %sMB file on vm: %s", config_virt.FILE_SIZE_IN_MB, vm_name
    )
    new_files = create_file_in_vm(
        vm=vm_name, vm_resource=vm_resource, size_in_mb=file_size,
        all_disks=all_disks
    )
    lun_space = fetch_actual_disk_size(
        storage_manager=storage_manager,
        lun_id=lun_id,
        disk_path=disk_path
    )
    assert bool(lun_space), (
        "Failed to get lun used space for lun: %s" % lun_id
    )
    logger.info("Used space on lun after file creation: %s", lun_space)
    testflow.step("removing the files: %s", new_files)
    for file_path in new_files:
        assert delete_file_from_vm(
            vm=vm_name, vm_resource=vm_resource, path=file_path
        )
    new_used_space = fetch_actual_disk_size(
        storage_manager=storage_manager,
        lun_id=lun_id,
        disk_path=disk_path
    )
    testflow.step("Used space on lun after file deletion: %2f", new_used_space)
    testflow.step("Stopping vm: %s", vm_name)
    assert ll_vms.stop_vms_safely([vm_name])
    return new_used_space, disks_ids


def get_cluster_hosts_resources(cluster_name):
    """
    Get a mapping between host name of Resource object for hosts in a given
    cluster.

    Args:
        cluster_name (str): Name of the cluster

    Returns:
         dict: Return a dictionary of resources.VDS objects or empty dict if no
            hosts were found in the cluster
    """
    cluster_hosts = ll_hosts.get_cluster_hosts(cluster_name)
    return {
        host_name: helpers.get_host_resource_by_name(host_name=host_name)
        for host_name in cluster_hosts
    }


def get_cpu_model_name_for_rest_api(cpu_model_full_name):
    """
    Convert the cpu model name that is returned from vdsClient getVdsCaps to
    the one that is acceptable in REST API

    Args:
        cpu_model_full_name (str): Name of cpu model as reported in vdsm

    Returns:
        str: Name of the cpu model as expected in REST API or None if the name
            isn't a valid one
    """
    cpu_model_full_name = cpu_model_full_name.split(' ')
    if 'AMD' in cpu_model_full_name:
        return '%s_%s' % (cpu_model_full_name[1], cpu_model_full_name[2])
    elif 'Intel' in cpu_model_full_name:
        return cpu_model_full_name[1]
    else:
        logger.error(
            "cpu model: %s is no supported in the system", cpu_model_full_name
        )
    return ""


def check_vm_machine_type(vm_name, host_resource, expected_machine_type):
    """
    Check if vm domain xml is set with the expected value for emulated machine
    flag upon vm creation.

    Args:
        vm_name (str): Name of the vm.
        host_resource (Host): resource of the host running the vm
        expected_machine_type (str): Expected value of the machine type

    Returns:
         bool: True if the vm was set with the expected value, False otherwise
    """
    vm_id = get_vm_id(vm_name)
    cmd = shlex.split(
        config_virt.VIRSH_VM_EMULATED_MACHINE_CMD % vm_id, posix=False
    )
    machine_type_output = host_resource.run_command(cmd)[1]
    if not machine_type_output:
        return False
    actual_machine_type = machine_type_output.split("=")[1]
    logger.info(
        "Expected machine type: %s, Actual machine type: %s" %
        (expected_machine_type, actual_machine_type)
    )
    return expected_machine_type in actual_machine_type


def check_vm_cpu_model(vm_name, host_resource, expected_cpu_model):
    """
    Check if vm domain xml is set with the expected value for cpu model
    upon vm creation.

    Args:
        vm_name (str): Name of the vm.
        host_resource (Host): resource of the host running the vm
        expected_cpu_model (str): Expected value of the cpu model type

    Returns:
         bool: True if the vm was set with the expected value, False otherwise
    """
    vm_id = get_vm_id(vm_name)
    cmd = shlex.split(config_virt.VIRSH_VM_CPU_MODEL_CMD % vm_id, posix=False)
    cpu_model_output = host_resource.run_command(cmd)[1]
    if not cpu_model_output:
        return False
    logger.info(
        "Expected cpu type: %s, cpu type from virsh output: %s" %
        (expected_cpu_model, cpu_model_output)
    )
    return expected_cpu_model in cpu_model_output


def get_hosts_by_cpu_model(cpu_model_name, cluster):
    """
    Get all hosts in cluster with specific cpu model

    Args:
        cpu_model_name (str): Name of cpu model to filter from
        cluster (str): Name of the cluster from which to get the hosts

    Returns:
        list: List of host names in the cluster with the given cpu_model_name
    """
    hosts = list()
    hosts_dict = get_cluster_hosts_resources(cluster)
    for name, resource in hosts_dict.iteritems():
        host_cpu = config_virt.CPU_MODEL_DENOM.get_maximal_cpu_model(
            hosts=[resource], version=config.COMP_VERSION
        ).get('cpu', '')
        if host_cpu == cpu_model_name:
            hosts.append(name)
    return hosts


def highest_common_cpu_model_host_pair_from_cluster(cluster):
    """
    Looks for a pair of hosts with the highest common cpu model in a given
    Cluster. e.g. if we have a cluster with 1 host with Conroe model and 2
    Penryn, the common cpu model is Conroe, but the hosts with highest cpu
    models are the 2 with Penryn.

    Args:
        cluster (str): Name of the cluster

    Returns:
         dict: cpu info dict for specific model which is common to the 2 host
            with the highest cpu model in the cluster.
    """
    hosts_dict = get_cluster_hosts_resources(cluster)
    if len(hosts_dict) < 2:
        return None
    min_cpu_model = config_virt.CPU_MODEL_DENOM.get_common_cpu_model(
        hosts_dict.values()
    )
    while len(hosts_dict) > 2:
        min_host = get_hosts_by_cpu_model(min_cpu_model.get('cpu'), cluster)[0]
        hosts_dict.pop(min_host)
    return config_virt.CPU_MODEL_DENOM.get_common_cpu_model(
        hosts_dict.values()
    )


def verify_number_of_disks_on_vm(vm_resource, number_of_disks=1):
    """
    Verifies that the vm has the given number of disk in it's file system

    Args:
        vm_resource (VDS): Vm resource to issue command with
        number_of_disks (int): Expected number of disks on the vm

    Returns:
         bool: True if number_of_disks == number of disks found in vm, False
            otherwise
    """
    cmd = shlex.split(config_virt.LSBLK_CMS, posix=False)
    cmd_output = (vm_resource.run_command(cmd)[1]).strip().split('\n')
    return len(cmd_output) == number_of_disks


def get_default_tz_from_db(engine):
    """
    Gets default values for DefaultGeneralTimeZone and DefaultWindowsTimeZone
    from the DB

    Args:
        engine: Engine resource

    Returns:
        dict: dictionary in format {DefaultWindowsTimeZone: value}
    """
    sql = ("SELECT option_name, option_value FROM vdc_options WHERE "
           "option_name like '%s';")
    pattern = 'Default%TimeZone'
    try:
        res = engine.db.psql(sql, pattern)
        return {r[0]: r[1] for r in res}
    except errors.ExecuteDBQueryError:
        return dict()


def get_vm_qemu_process_args(vm_name):
    """
    Get args for qemu process of given vm
    Args:
        vm_name(str): virtual machine

    Returns:
        dict: dict with qemu process args, empty dict otherwise
    """
    result = {}
    vds_host = helpers.get_host_resource_of_running_vm(vm_name)
    cmd = [
        'ps', '-eo', 'args', '|',
        'grep', '-v', 'grep', '|',
        'grep', vm_name
    ]
    rc, out, err = vds_host.run_command(cmd)
    if rc == 0:
        rtc_base = re.search('(?<=rtc base=)[a-zA-Z0-9\-:]+', out).group(0)
        result['rtc_base'] = datetime.strptime(rtc_base, '%Y-%m-%dT%H:%M:%S')
    else:
        logger.error(
            msg='Failed to get qemu process args with {err}'.format(err=err)
        )
    return result


def execute_multi_sparsify(disks_ids, storage_domain_name):
    """
    Execute sparsify disk action on given disks id list.
    And checks that all actions succeeded

    Args:
        disks_ids (list): disks id list
        storage_domain_name (str): storage domain name

    """
    results = []
    with ThreadPoolExecutor(max_workers=len(disks_ids)) as executor:
        for disk in disks_ids:
            results.append(
                executor.submit(
                    ll_disks.sparsify_disk, disk_id=disk,
                    storage_domain_name=storage_domain_name
                )
            )
    for result in results:
        assert result.result()


@ll_general.generate_logs(step=True)
def snapshot_vm(
    vm_name, snapshot_description, with_memory=False, start_vm=False
):
    """
    Create, restore, remove snapshots

    Args:
        vm_name (str): VM name
        snapshot_description (list): List of snapshot description
        with_memory (bool): Create snapshot with memory
        start_vm (bool): start vm before create snapshot

    Raises:
         AssertionError: if failed operation
    """

    if start_vm:
        assert ll_vms.startVm(True, vm_name)
    for description in snapshot_description:
        assert ll_vms.addSnapshot(
            positive=True,
            vm=vm_name,
            description=description,
            persist_memory=with_memory,
        ), "Failed to add snapshot to VM."
    testflow.step(
        "Restore vm %s from snapshot %s", vm_name, snapshot_description[1]
    )
    assert ll_vms.restore_snapshot(
        positive=True,
        vm=vm_name,
        description=snapshot_description[1],
        restore_memory=with_memory,
        ensure_vm_down=True
    )
    for snapshot in snapshot_description:
        testflow.step("Remove snapshot %s of vm %s", snapshot, vm_name)
        assert ll_vms.removeSnapshot(
            positive=True,
            vm=vm_name,
            description=snapshot,
            timeout=config_virt.VM_REMOVE_SNAPSHOT_TIMEOUT

        )
    return True


@ll_general.generate_logs(step=True)
def clone_vm(base_vm_name, clone_vm_name):
    """
    Clone VM

    Args:
        base_vm_name (str): VM name which will be clone (source vm)
        clone_vm_name (str): Clone VM name (destination vm)

    Raises:
         AssertionError: if failed operation
    """

    assert ll_vms.stop_vms_safely([base_vm_name])
    assert hl_vms.clone_vm(
        positive=True, vm=base_vm_name,
        clone_vm_name=clone_vm_name
    )
    assert check_clone_vm(
        clone_vm_name=clone_vm_name,
        base_vm_name=base_vm_name
    )
    check_disk_contents_on_clone_vm(
        clone_vm_name=clone_vm_name
    )
    assert ll_vms.startVm(
        positive=True, vm=base_vm_name,
        wait_for_status=config.VM_UP
    )


@ll_general.generate_logs(step=True)
def check_cloud_init_parameters(
    vm_name=config_virt.CLOUD_INIT_VM_NAME,
    dns_search=None, dns_servers=None, time_zone=None, script_content=None,
    hostname=None, check_nic=True
):
    """
    Checks cloud init parameters on VM

    Args:
        vm_name: VM name to check
        dns_search (str): DNS search configured
        dns_servers (str):  DNS server/s configured
        time_zone (list): list of possible time zones configured
        script_content (str): file content configured by script
        hostname (str): configured hostname
        check_nic (bool): check nic configuration

    Returns:
        bool: True if all checks pass Else False
    """
    logger.info('Get ip for VM: %s', vm_name)
    config_virt.VM_IP = hl_vms.get_vm_ip(
        vm_name=vm_name, start_vm=False
    )
    logger.info('VM: %s , IP:%s', vm_name, config_virt.VM_IP)
    network_status = check_networks_configuration(
        vm_name=vm_name,
        check_nic=check_nic,
        dns_search=dns_search,
        dns_servers=dns_servers
    )
    authentication_status = check_authentication_configuration(vm_name)
    script_status = check_custom_script(vm_name, script_content=script_content)
    general_status = check_general(
        vm_name, time_zone=time_zone, hostname=hostname
    )
    if (
        network_status and
        authentication_status and
        script_status and
        general_status
    ):
        return True
    else:
        logger.error("The guest check failed")
        return False


def check_general(vm_name, time_zone=None, hostname=None):
    """
    Check general data on VM

    Args:
        time_zone (list): list of possible Time zone on guest
        (Daylight vs Standard) e.g. NZST and NZDT
        hostname (str): configured hostname

    Returns:
        bool: True if general parameters are as expected else False
    """
    status = True
    if time_zone:
        for tz in time_zone:
            logger.info("Check time zone, expected: %s", tz)
            if check_data_on_vm(
                    vm_name, config_virt.CHECK_TIME_ZONE_IN_GUEST, tz
            ):
                logger.info("time zone check pass")
                status = True
                break
            else:
                logger.error("time zone check failed")
                status = False
    if hostname:
        logger.info("Check hostname, expected: %s", hostname)
        if check_data_on_vm(vm_name, config_virt.CHECK_HOST_NAME, hostname):
            logger.info("hostname check pass")
        else:
            logger.error("hostname check failed")
            status = False
    return status


def check_custom_script(vm_name, script_content):
    """
    Check custom script content

    Args:
        script_content (str): expected script content

    Returns
        bool: True if content on guest equals to expected content
    """

    if script_content:
        logger.info("Check script content, expected: %s", script_content)
        if check_data_on_vm(
                vm_name, config_virt.CHECK_FILE_CONTENT, script_content
        ):
            logger.info("script content check pass")
            return True
        else:
            logger.error("script content check failed")
            return False
    else:
        return True


def check_authentication_configuration(vm_name):
    """
    Check user authentication

    Returns:
        bool: True if user name matches the user name on guest else False
    """
    logger.info(
        "Check user name, expected: %s", config_virt.VM_USER_CLOUD_INIT
    )
    cmd = config_virt.CHECK_USER_IN_GUEST % config_virt.VM_USER_CLOUD_INIT
    if check_data_on_vm(vm_name, cmd, config_virt.VM_USER_CLOUD_INIT):
        logger.info("user name check pass")
        return True
    else:
        logger.error("user name check failed")
        return False


def check_networks_configuration(
    vm_name, check_nic=False, dns_search=None, dns_servers=None
):
    """
    Check networks configuration, first check that NIC exists

    Args:
        check_nic (bool): check nic configuration
        dns_search (str): DNS search configured
        dns_servers (str): DNS server/s configured

    Returns:
        bool: True if networks check pass else False

    Raises:
         AssertionError: if failed operation
    """
    status = True
    if check_nic:
        logger.info("Check the NIC file name exists")
        cmd = config_virt.CHECK_NIC_EXIST
        if check_data_on_vm(vm_name, cmd, config_virt.CLOUD_INIT_NIC_NAME):
            logger.info("NIC file name exist")
        else:
            logger.error("NIC file name doesn't exist")
            status = False
    if dns_search:
        logger.info("Check DNS search, expected: %s", dns_search)
        cmd = config_virt.CHECK_DNS_IN_GUEST % dns_search
        if check_data_on_vm(vm_name, cmd, dns_search):
            logger.info("DNS search check pass")
        else:
            logger.error("DNS search check failed")
            status = False
    if dns_servers:
        logger.info("Check DNS servers, expected: %s", dns_servers)
        cmd = config_virt.CHECK_DNS_IN_GUEST % dns_servers
        if check_data_on_vm(vm_name, cmd, dns_servers):
            logger.info("DNS servers check pass")
        else:
            logger.error("DNS servers check failed")
            status = False
    return status


@ll_general.generate_logs(step=True)
def suspend_resume_vm_test(vm_name):
    """
    Suspend vm and resume vm, and check that status is up

    Args:
        vm_name (str): vm name
    Returns:
        bool: True if all actions pass
    Raises:
        AssertionError: if failed operation
    """
    assert ll_vms.suspendVm(True, vm_name), "Failed to suspend vm"
    logging.info("VM status: %s", ll_vms.get_vm_state(vm_name=vm_name))
    assert ll_vms.startVm(
        positive=True, vm=vm_name,
        wait_for_status=config.VM_UP,
        timeout=2 * config_virt.VM_ACTION_TIMEOUT
    )
    return True


@ll_general.generate_logs(step=True)
def detach_iso_domains(dc_name):
    """
    Detach every ISO storage domain from a data center.

    Args:
        dc_name(str): name of the data center
    """
    dc_isos = ll_sd.findIsoStorageDomains(dc_name)
    for domain in dc_isos:
        logger.info(
            "Move ISO Domain %s to maintenance", domain)
        assert ll_sd.deactivateStorageDomain(
            positive=True,
            datacenter=dc_name,
            storagedomain=domain
        )
        logger.info("Detach ISO domain %s", domain)
        assert ll_sd.detachStorageDomain(
            positive=True,
            datacenter=dc_name,
            storagedomain=domain
        )


def get_vm_nic_config(vm_name, iface_name):
    """
    Gets VM NIC configuration for given interface name

    Args:
        vm_name(str): name of the VM
        iface_name(str): interface name to get configuration

    Returns:
        dict: dictionary with parsed configuration, e.g.
            {ip:data_structure, boot_protocol: boot_protocol, etc}

    """
    cmd = 'cat /etc/sysconfig/network-scripts/ifcfg-{}'.format(iface_name)
    result = {}
    status, ips = ll_vms.wait_for_vm_ip(
        vm=vm_name,
        get_all_ips=True
    )
    logger.info('VM IPs are: {}'.format(ips))
    if status:
        config_virt.VM_IP = ips['ip'][0]
    rc, out, err = get_vm_data(vm_name, cmd)
    if rc == 0:
        aliases = {
            'name': 'DEVICE',
            'ip': 'IPADDR',
            'ipv6': 'IPV6ADDR',
            'gateway_v4': 'GATEWAY',
            'gateway_v6': 'IPV6_DEFAULTGW',
            'netmask_v4': 'NETMASK',
            'boot_protocol': 'BOOTPROTO',
            'dhcp_v6': 'DHCPV6C',
            'on_boot': 'ONBOOT',
        }
        parsed = {}
        for k, v in aliases.iteritems():
            try:
                actual_value = re.search(
                    '(?<=\n{}=)[a-zA-Z0-9.:/]+'.format(v),
                    out
                ).group(0)
                if k == 'ipv6':
                    parsed[k], parsed['netmask_v6'] = actual_value.split('/')
                else:
                    parsed[k] = actual_value
            except (AttributeError, ValueError):
                parsed[k] = None
        ipv4_boot_proto = parsed.pop('boot_protocol', None)
        if parsed.get('ip', False):
            result['boot_protocol'] = 'static'
        elif ipv4_boot_proto:
            result['boot_protocol'] = ipv4_boot_proto
        else:
            result['boot_protocol'] = 'none'
        ipv6_dhcp = parsed.pop('dhcp_v6', False)
        if ipv6_dhcp:
            result['ipv6_boot_protocol'] = 'dhcp'
        elif parsed.get('ipv6', False):
            result['ipv6_boot_protocol'] = 'static'
        else:
            result['ipv6_boot_protocol'] = 'none'

        result['ip'] = data_struct.Ip(
                address=parsed.pop('ip', None),
                gateway=parsed.pop('gateway_v4', None),
                netmask=parsed.pop('netmask_v4', None),
                version='v4'
            )
        result['ipv6'] = data_struct.Ip(
            address=parsed.pop('ipv6', None),
            gateway=parsed.pop('gateway_v6', None),
            netmask=parsed.pop('netmask_v6', None),
            version='v6'
        )
        result['name'] = parsed.pop('name', False)

        return result
    else:
        return {
            'boot_protocol': 'none',
            'ipv6_boot_protocol': 'none',
            'name': iface_name
        }


def compare_nic_configs(vm_name, expected):
    """
    Compares VM NIC configuration with expected

    Args:
        vm_name(str): name of the VM
        expected(dict): dictionary with expected NIC configuration

    Returns:
        tuple: check_status(bool), separate checks status(dict)
    """
    actual = get_vm_nic_config(vm_name, expected['name'])
    res = {}

    for key in expected:
        logger.info(
            'Comparing {key} : {actual} with  expected: {expected}'.format(
                key=key, actual=actual, expected=expected
            )
        )
        res[key] = {}
        res[key]['actual'], res[key]['expected'] = actual[key], expected[key]
        if key in ['ip', 'ipv6']:
            res[key]['status'] = validator.compareElements(
                expElm=expected[key],
                actElm=actual[key],
                logger=logger,
                root='Comparator')
        else:
            res[key]['status'] = expected[key] == actual[key]
    return all([val['status'] for _, val in res.iteritems()]), res


def generate_network_configs(networking_options):
    """
    Helper function to generate network configs for the test parametrization

    Returns:
        tuple: all possible network configs(list), ids for pytest(list)

    """
    opts = networking_options
    res = list(
        (dict(zip(opts, x)) for x in itertools.product(*opts.values()))
    )
    for variant in res:
        if variant['ipv6_boot_protocol'] != 'static':
            del variant['ipv6']
        if variant['boot_protocol'] != 'static':
            del variant['ip']
    unique, ids = [], []
    for variant in res:
        if variant not in unique:
            unique.append(variant)
            ipv4_boot_proto = variant.get('boot_protocol', 'None')
            ipv6_boot_proto = variant.get('ipv6_boot_protocol', 'None')
            variant_name = 'ipv4_{boot_proto}_ipv6_{v6_boot_proto}'.format(
                boot_proto=ipv4_boot_proto,
                v6_boot_proto=ipv6_boot_proto
            )
            ids.append(variant_name)
    return unique, ids


def to_bool(value):
    """
    Converts value to boolean. 'true', 'yes', 'y', '1', True are converted
    to True, anything other to False

    Args:
        value (any): Value to convert

    Returns:
        bool: converted value
    """
    val_true = ['true', 'yes', 'y', '1', True]
    if value.isalnum():
        return value.lower() in val_true
    else:
        return value in val_true


def get_nic_config(config_dict):
    """
    Convert dict with network config into data_structure.NicConfigurations

    Args:
        config_dict(dict): dictionary with config, for example
            {'ip': art.rhevm_api.data_struct.data_structures.Ip,
             'boot_protocol': 'static',
             'ipv6_boot_protocol': 'static',
             'name': 'eth1',
             'ipv6': art.rhevm_api.data_struct.data_structures.Ip
             }

    Returns:
        dict: dictionary with NIC configurations

    """
    return {
        'nic_configurations': data_struct.NicConfigurations(
            nic_configuration=[
                data_struct.NicConfiguration(on_boot=True, **config_dict)
            ]
        )
    }


def get_vm_data(vm_name, command_to_run):
    """
    Check configure data on VM. Runs command on VM and compare it with
    expected output

    Args:
        vm_name (str): Vm name to get data from
        command_to_run (str): command to run on vm
    Returns:
        bool: True if output as expected else False
    """
    vm_ip = hl_vms.get_vm_ip(vm_name, start_vm=False) or config_virt.VM_IP
    logger.info('Connecting to the VM: {} with IP: {}'.format(vm_name, vm_ip))
    if config_virt.VM_USER_CLOUD_INIT:
        logger.info("connect with {}".format(config_virt.VM_USER_CLOUD_INIT))
        executor = helpers.get_host_executor(
            ip=vm_ip,
            username=config_virt.VM_USER_CLOUD_INIT,
            password=config_virt.VDC_ROOT_PASSWORD
        )
    elif config_virt.USER_PKEY:
        logger.info(
            "connect without password as %s", config_virt.VM_USER_CLOUD_INIT
        )
        host = helpers.Host(ip=vm_ip)
        host.users.append(config_virt.VM_USER_CLOUD_INIT)
        user_root = helpers.User(
            name=config_virt.VDC_ROOT_USER,
            password=config_virt.VDC_ROOT_PASSWORD
        )
        executor = host.executor(
            user=user_root, pkey=True
        )
    logger.info("Run command: %s", command_to_run)
    rc, out, err = executor.run_cmd(shlex.split(command_to_run))
    logger.info("output: %s", out)
    return rc, out, err


def check_data_on_vm(vm_name, command_to_run, expected_output):
    """
    Wrapper to generalize checks since all get_vm_data logic was moved to
    separate function

    Args:
        vm_name (str): VM name
        command_to_run (list): command to run on the VM
        expected_output (str): expected output to check for

    Returns:
        bool: True is expected output in command out, False otherwise

    """
    _, out, _ = get_vm_data(vm_name, command_to_run)
    return expected_output in out
