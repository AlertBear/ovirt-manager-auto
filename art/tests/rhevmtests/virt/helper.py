#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for virt and network migration job
"""
import os
import shlex
import time
import logging
import xmltodict

from utilities import jobs
from art import test_handler
import art.core_api.validator as validator
from rhevmtests import helpers
from rhevmtests.networking import config
from art.unittest_lib import testflow
from art.test_handler import exceptions
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.utils import test_utils
import art.rhevm_api.resources as resources
import art.unittest_lib.network as lib_network
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    networks as ll_networks,
    storagedomains as ll_sd,
    vms as ll_vms,
    vmpools as ll_vmpools,
    clusters as ll_clusters,
    general as ll_general,
    disks as ll_disks,
)
import config as config_virt

logger = logging.getLogger("Virt_Helper")

VDSM_LOG = "/var/log/vdsm/vdsm.log"
SERVICE_STATUS = "id"
LOAD_MEMORY_FILE = "tests/rhevmtests/virt/migration/memoryLoad.py"
DESTINATION_PATH = "/tmp/memoryLoad.py"
DELAY_FOR_SCRIPT = 120
MEMORY_USAGE = 60
DELAY_FOR_SNAPSHOT = 60
RUN_SCRIPT_COMMAND = (
    'python /tmp/memoryLoad.py -s %s -r %s &> /tmp/OUT1 & echo $!'
)
LOAD_VM_COMMAND = (
    '/home/loadTool -v -p 1 -t 1 -m %s -l mem -s %s &> /tmp/OUT1 & echo $!'
)
VIRSH_VM_LIST_CMD = "virsh -r list | grep "
VIRSH_VM_DUMP_XML_CMD = "virsh -r dumpxml "
VIRSH_VM_IOTHREADS_NUMBER_CMD = (
    "virsh -r dumpxml %s | grep -oP '(?<=<iothreads>).*?(?=</iothreads>)'"
)
VIRSH_VM_IOTHREADS_DRIVERS_CMD = "virsh -r dumpxml %s | grep 'iothread='"

test_handler.find_test_file.__test__ = False


def get_origin_host(vm):
    """
    Check where VM is located

    Args:
    vm (str): vm on the host

    Returns:
        tuple: host obj and host name where the VM is located
    """
    orig_host = lib_network.get_host(vm)
    if orig_host not in config.HOSTS[:2]:
        logger.error("VM doesn't reside on provided hosts")
        return None, None
    orig_host_ip = ll_hosts.get_host_ip_from_engine(orig_host)
    orig_host_obj = resources.VDS(orig_host_ip, config.HOSTS_PW)
    return orig_host_obj, orig_host


def get_dst_host(orig_host_obj):
    """
    Check what is dst Host for migration

    Args:
    orig_host_obj (host): Origin host object

    Returns:
        tuple: host obj and host name where to migrate VM
    """
    dst_host_obj = filter(
        lambda x: x.ip != orig_host_obj.ip, config.VDS_HOSTS[:2]
    )[0]
    dst_host = ll_hosts.get_host_name_from_engine(dst_host_obj)
    return dst_host_obj, dst_host


def migrate_vms_and_check_traffic(
    vms, nic_index=1, vlan=None, bond=None, req_nic=None, maintenance=False,
    non_vm=False
):
    """
    Check migration by putting required network down or put host to maintenance
    and check migration traffic via tcpdump.
    Send only req_nic or maintenance

    Args:
        vms (list): VMs to migrate
        nic_index (int): index for the nic where the migration happens
        vlan (str): Network VLAN
        bond (str): Network Bond
        req_nic (int): index for nic with required network
        maintenance (bool): Migrate by set host to maintenance
        non_vm (bool): True if network is Non-VM network
    Raises:
            AssertionError: if migration failed
    """
    (
        orig_host_obj,
        orig_host,
        dst_host_obj,
        dst_host
    ) = get_orig_and_dest_hosts(vms)

    if req_nic:
        log_msg = "by putting %s down" % req_nic
    elif maintenance:
        log_msg = "by putting %s to maintenance" % orig_host
    else:
        log_msg = ""

    logger.info(
        "Getting src IP and dst IP from %s", " and ".join(config.HOSTS[:2])
    )
    if nic_index == 0:
        src, dst = orig_host_obj.ip, dst_host_obj.ip
    else:
        src, dst = lib_network.find_ip(
            vm=vms[0], host_list=config.VDS_HOSTS[:2], nic_index=nic_index,
            vlan=vlan, bond=bond
        )
        network_helper.send_icmp_sampler(host_resource=orig_host_obj, dst=dst)

    logger.info("Found: src IP: %s. dst IP: %s", src, dst)

    nic = orig_host_obj.nics[nic_index] if not bond else bond
    nic = "%s.%s" % (nic, vlan) if vlan else nic
    nic = nic if non_vm else ll_networks.get_network_on_host_nic(
        orig_host, nic
    )
    logger.info(
        "Start migration from %s to %s over %s (%s)", orig_host, dst_host,
        nic, src
    )
    if bond:
        logger.info("Migrate over BOND, sleep for 30 seconds")
        time.sleep(30)
    err = "Couldn't migrate %s over %s %s" % (vms, nic, log_msg)
    assert check_traffic_while_migrating(
        vms=vms, orig_host_obj=orig_host_obj, orig_host=orig_host,
        dst_host=dst_host, nic=nic, src_ip=src, dst_ip=dst,
        req_nic=req_nic, maintenance=maintenance
    ), err


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


def check_traffic_while_migrating(
    vms, orig_host_obj, orig_host, dst_host, nic, src_ip, dst_ip,
    req_nic=None, maintenance=False
):
    """
    Search for packets in tcpdump output during migration

    Args:
        vms (list): VMs to migrate
        orig_host_obj (resources.VDS object): Host object of original Host
        orig_host (str): orig host
        dst_host (str): destination host
        nic (str): NIC where IP is configured for migration
        src_ip (str): IP from where the migration should be sent
        dst_ip (str): IP where the migration should be sent
        req_nic (int): NIC with required network
        maintenance (bool): Migrate by set host to maintenance

    Returns:
        bool: True is migrate succeed, otherwise False
    """
    dump_timeout = config.TIMEOUT * 3 if not req_nic else config.TIMEOUT * 4
    req_nic = orig_host_obj.nics[req_nic] if req_nic else None
    check_vm_migration_kwargs = {
        "vms_list": vms,
        "src_host": orig_host,
        "vm_user": config.HOSTS_USER,
        "vm_password": config.VMS_LINUX_PW,
        "vm_os_type": "rhel"
    }
    tcpdump_kwargs = {
        "host_obj": orig_host_obj,
        "nic": nic,
        "src": src_ip,
        "dst": dst_ip,
        "numPackets": config_virt.NUM_PACKETS,
    }
    if req_nic:
        func = hl_vms.migrate_by_nic_down
        check_vm_migration_kwargs["nic"] = req_nic
        check_vm_migration_kwargs["password"] = config.HOSTS_PW
        tcpdump_kwargs["timeout"] = str(config.TIMEOUT * 4)

    elif maintenance:
        func = hl_vms.migrate_by_maintenance

    else:
        func = hl_vms.migrate_vms
        check_vm_migration_kwargs["dst_host"] = dst_host

    tcpdump_job = jobs.Job(test_utils.run_tcp_dump, (), tcpdump_kwargs)
    migration_job = jobs.Job(func, (), check_vm_migration_kwargs)
    job_set = jobs.JobsSet()
    job_set.addJobs([tcpdump_job, migration_job])
    job_set.start()
    job_set.join(dump_timeout)
    return tcpdump_job.result and migration_job.result


def get_orig_and_dest_hosts(vms):
    """
    Get orig_host_obj, orig_host, dst_host_obj, dst_host for VMs and check
    that all VMs are started on the same host

    Args:
        vms (list): VMs to check

    Returns
        tuple: orig_host_obj, orig_host, dst_host_obj, dst_host
    """
    orig_hosts = [ll_vms.get_vm_host(vm) for vm in vms]
    logger.info("Checking if all VMs are on the same host")
    res = (orig_hosts[1:] == orig_hosts[:-1])
    assert res, "Not all VMs are on the same host"

    orig_host_obj, orig_host = get_origin_host(vms[0])
    dst_host_obj, dst_host = get_dst_host(orig_host_obj)
    return orig_host_obj, orig_host, dst_host_obj, dst_host


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


def create_vm_from_glance_image(image_name, vm_name):
    """
    Create VM with glance image on NFS storage domain

    Args:
        image_name (str): The image name in glance
        vm_name (str): VM name to create

    Returns:
        bool: True if VM created else False
    """
    sd_name = ll_sd.getStorageDomainNamesForType(
        datacenter_name=config.DC_NAME[0],
        storage_type=config.STORAGE_TYPE
    )[0]
    return hl_vms.create_vm_using_glance_image(
        vmName=vm_name, vmDescription=vm_name,
        cluster=config.CLUSTER_NAME[0], nic=config.NIC_NAME[0],
        storageDomainName=sd_name, network=config.MGMT_BRIDGE,
        glance_storage_domain_name=config.GLANCE_DOMAIN,
        glance_image=image_name

    )


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
        int: Process id
    """
    logger.info(
        "Run load %s MB on vm %s for %s sec",
        load, vm_name, time_to_run
    )
    cmd = LOAD_VM_COMMAND % (load, time_to_run)
    vm_resource = helpers.get_vm_resource(vm=vm_name, start_vm=start_vm)
    if start_vm:
        assert wait_for_vm_fqdn(vm_name)
    ps_id = vm_resource.run_command(command=shlex.split(cmd))[1]
    time.sleep(5)
    return ps_id


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


def create_file_in_vm(vm, vm_resource, path=config_virt.TEMP_PATH):
    """
    Create an empty file in vm using vm resource entity

    Args:
        vm (str): Vm name
        vm_resource (Host resource): Resource for the vm
        path (str): path to locate the file

    Raises:
        VMException: If failed to create file
    """
    logger.info("attempting to create an empty file in vm: %s", vm)
    full_path = os.path.join(path, config_virt.FILE_NAME)
    if not vm_resource.fs.touch(full_path):
        raise exceptions.VMException(
            "Failed to create an empty file on vm: '%s'" % vm
        )


def check_if_file_exist(
    positive,
    vm,
    vm_resource,
    path=config_virt.TEMP_PATH
):
    """
    Checks if file (name of file in config) exist or not in the vm using vm
    resource entity

    Args:
        positive (bool): Signifies the expected result
        vm (str): Vm name
        vm_resource (host resource): Command executor for the vm
        path (str): path where to find the file

    Raises:
        VMException: If file exist
    """
    testflow.step(
        "checking if file: %s exists in vm: %s. expecting result: %s",
        config_virt.FILE_NAME, vm, positive
    )
    full_path_to_file = os.path.join(
        path, config_virt.FILE_NAME
    )
    file_exists = vm_resource.fs.exists(full_path_to_file)
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
    cmd = shlex.split(" ".join((VIRSH_VM_LIST_CMD, vm_name)))
    rc, out, err = host_resource.executor().run_cmd(cmd)
    if rc:
        raise exceptions.HostException(
            "Failed to run virsh cmd: %s on: %s, err: %s"
            % (host_resource, cmd, err)
        )
    vm_id = out.split()[0]
    logger.info("VM pid is %s", vm_id)
    return vm_id


def get_dump_xml_as_dict(vm_name):
    """
    Return VM dump xml as dict

    Args:
        vm_name (str): VM name

    Returns:
        dict: VM dump xml info as disc

    Raise:
         HostException: If failed to run command
    """

    host_resource = helpers.get_host_resource_of_running_vm(vm_name)
    vm_id = get_vm_id(vm_name)
    cmd = shlex.split(" ".join((VIRSH_VM_DUMP_XML_CMD, vm_id)))
    rc, out, err = host_resource.executor().run_cmd(cmd)
    if rc:
        raise exceptions.HostException(
            "Failed to run virsh cmd: %s on: %s, err: %s"
            % (host_resource, VIRSH_VM_LIST_CMD, err)
        )
    return xmltodict.parse(out)


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


def check_iothreads_of_vm(vm_name, number_of_disks, number_of_threads):
    """
    Check io threads on VM with 'virsh' command.
    1. Check total io threads
    2. Check each disk driver

    Args:
        vm_name (str): VM name
        number_of_disks (int): Number of disks on VM
        number_of_threads (int): expected number of io threads

    Returns:
        bool: True if check succeeded, False otherwise
    """
    logger.info(
        "Expected number of disks: %s, Expected number of threads: %s",
        number_of_disks, number_of_threads
    )
    host_resource = helpers.get_host_resource_of_running_vm(vm_name)
    vm_id = get_vm_id(vm_name)
    cmd = shlex.split(VIRSH_VM_IOTHREADS_NUMBER_CMD % vm_id, posix=False)
    total_threads_output = run_command_on_host(cmd, host_resource)
    total_threads = int(total_threads_output) if total_threads_output else -1
    cmd = shlex.split(VIRSH_VM_IOTHREADS_DRIVERS_CMD % vm_id, posix=False)
    logger.info(
        "Expected disk:%d, Expected threads:%d, Actual threads:%d" %
        (number_of_disks, number_of_threads, total_threads)
    )
    drivers_check = check_drivers(
        run_command_on_host(cmd, host_resource),
        number_of_disks,
        number_of_threads
    )
    return total_threads == number_of_threads and drivers_check


def run_command_on_host(cmd, host_resource):
    """
    Run command on host resource and return output, in case of error
    return None.

    Args:
        cmd (str): command to run
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


def check_clone_vm(
    clone_vm_name,
    base_vm_name,
    check_disk_content=False,
):
    """
    Check clone vm
        1. Check Nic: check the MAC address is diff then base
        2. Check disk content: start vms and check that new disk contains
        the same file as in base disk
        3. Check that clone vm has the same attributes as base vm

    Args:
        clone_vm_name (str): clone vm name
        base_vm_name (str): base vm name
        check_disk_content (bool): If True check clone vm content,
        else don't check

    Returns:
         bool: Return True if all checks pass, else return False
    """
    logger.info(
        "Check clone vm: start vms %s, %s", clone_vm_name, base_vm_name
    )
    ll_vms.start_vms(vm_list=[clone_vm_name, base_vm_name])
    if check_disk_content:
        logger.info("Check disk content")
        vm_resource = helpers.get_vm_resource(clone_vm_name)
        testflow.step("Verify that file exists after vm restart")
        check_if_file_exist(True, clone_vm_name, vm_resource, path='/home/')
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
    testflow.step("stop vms and check vm attributes")
    ll_vms.stop_vms_safely(vms_list=[clone_vm_name, base_vm_name])
    vm_obj_clone_vm = ll_vms.get_vm_obj(clone_vm_name)
    vm_obj_base_vm = ll_vms.get_vm_obj(base_vm_name)
    return validator.compareElements(
        vm_obj_base_vm, vm_obj_clone_vm, logger=logger, root='Comparator',
        ignore=config_virt.VALIDATOR_IGNORE_LIST
    )


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
