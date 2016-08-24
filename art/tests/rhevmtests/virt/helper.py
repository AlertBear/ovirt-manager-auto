#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for virt and network migration job
"""
import os
import shlex
import time
import logging

from utilities import jobs
from art import test_handler
from rhevmtests import helpers
import art.core_api.apis_utils as utils
from rhevmtests.networking import config
from art.unittest_lib import testflow
from art.test_handler import exceptions
from art.rhevm_api.utils import test_utils
import art.rhevm_api.resources as resources
import art.unittest_lib.network as lib_network
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
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
NETMASK = "255.255.0.0"
LOAD_VM_COMMAND = (
    '/home/loadTool -v -p 1 -t 1 -m %s -l mem -s %s &> /tmp/OUT1 & echo $!'
)
test_handler.find_test_file.__test__ = False


def get_origin_host(vm):
    """
    Check where VM is located

    :param vm: vm on the host
    :type vm: str
    :return: host obj and host name where the VM is located
    :rtype: tuple
    """
    orig_host = lib_network.get_host(vm)
    if orig_host not in config.HOSTS[:2]:
        logger.error("VM doesn't reside on provided hosts")
        return None, None
    orig_host_ip = hosts.get_host_ip_from_engine(orig_host)
    orig_host_obj = resources.VDS(orig_host_ip, config.HOSTS_PW)
    return orig_host_obj, orig_host


def get_dst_host(orig_host_obj):
    """
    Check what is dst Host for migration

    :param orig_host_obj: Origin host object
    :type orig_host_obj: Resources.VDS
    :return: host obj and host name where to migrate VM
    :rtype: tuple
    """
    dst_host_obj = filter(
        lambda x: x.ip != orig_host_obj.ip, config.VDS_HOSTS[:2]
    )[0]
    dst_host = hosts.get_host_name_from_engine(dst_host_obj)
    return dst_host_obj, dst_host


def migrate_vms_and_check_traffic(
    vms, nic_index=1, vlan=None, bond=None, req_nic=None, maintenance=False,
    non_vm=False
):
    """
    Check migration by putting required network down or put host to maintenance
    and check migration traffic via tcpdump.
    Send only req_nic or maintenance

    :param vms: VMs to migrate
    :type vms: list
    :param nic_index: index for the nic where the migration happens
    :type nic_index: int
    :param vlan: Network VLAN
    :type vlan: str
    :param bond: Network Bond
    :type bond: str
    :param req_nic: index for nic with required network
    :type req_nic: int
    :param maintenance: Migrate by set host to maintenance
    :type maintenance: bool
    :param non_vm: True if network is Non-VM network
    :type non_vm: bool
    :raise: config.NET_EXCEPTION
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

    if not check_traffic_while_migrating(
        vms=vms, orig_host_obj=orig_host_obj, orig_host=orig_host,
        dst_host=dst_host, nic=nic, src_ip=src, dst_ip=dst,
        req_nic=req_nic, maintenance=maintenance
    ):
        raise config.NET_EXCEPTION(
            "Couldn't migrate %s over %s %s" % (vms, nic, log_msg)
        )


def set_host_status(activate=False):
    """
    Set host to operational/maintenance state

    :param activate: activate Host if True, else put into maintenance
    :type activate: bool
    :raise: exceptions.NetworkException
    """
    host_state = "active" if activate else "maintenance"
    func = "activateHost" if activate else "deactivateHost"
    if not activate:
        ll_hosts.select_host_as_spm(
            positive=True,
            host=config.HOSTS[0],
            data_center=config.DC_NAME[0]
        )
    call_func = getattr(hosts, func)
    logger.info("Putting hosts besides first two to %s", host_state)
    for host in config.HOSTS[2:]:
        if not call_func(True, host):
            raise exceptions.HostException(
                "Couldn't put %s into %s" % (host, host_state)
            )


def check_traffic_while_migrating(
    vms, orig_host_obj, orig_host, dst_host, nic, src_ip, dst_ip,
    req_nic=None, maintenance=False
):
    """
    Search for packets in tcpdump output during migration

    :param vms: VMs to migrate
    :type vms: list
    :param orig_host_obj: Host object of original Host
    :type orig_host_obj: resources.VDS object
    :param orig_host: orig host
    :type orig_host: str
    :param dst_host: destination host
    :type dst_host: str
    :param nic: NIC where IP is configured for migration
    :type nic: str
    :param src_ip: IP from where the migration should be sent
    :type src_ip: str
    :param dst_ip: IP where the migration should be sent
    :type dst_ip: str
    :param req_nic: NIC with required network
    :type req_nic: int
    :param maintenance: Migrate by set host to maintenance
    :type maintenance: bool
    :return True/False
    :rtype: bool
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
        "numPackets": config.NUM_PACKETS,
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

    :param vms: VMs to check
    :type vms: list
    :return: orig_host_obj, orig_host, dst_host_obj, dst_host
    :rtype: object
    :raise: exceptions.NetworkException
    """
    orig_hosts = [ll_vms.get_vm_host(vm) for vm in vms]
    logger.info("Checking if all VMs are on the same host")
    if not orig_hosts[1:] == orig_hosts[:-1]:
        raise config.NET_EXCEPTION("Not all VMs are on the same host")

    orig_host_obj, orig_host = get_origin_host(vms[0])
    dst_host_obj, dst_host = get_dst_host(orig_host_obj)
    return orig_host_obj, orig_host, dst_host_obj, dst_host


def copy_file_to_vm(vm_ip, source_file_path, destination_path):
    """
    Copy file to VM using Machine.

    :param vm_ip: VM ip
    :type vm_ip: str
    :param source_file_path: File location at ART
    :type source_file_path: str
    :param destination_path: destination path on VM
    :type destination_path: str
    :return: Returns False if action of copy to VM, otherwise True
    :rtype: bool
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


def load_vm_memory(
    vm_name,
    memory_size,
    reuse_memory='True',
    memory_usage=MEMORY_USAGE
):
    """
     1. Copy load memory python script to VM
     2. Run it, wait for 60 sec to memory be capture by script.

    :param vm_name: VM that run the script
    :type vm_name: str
    :param memory_size:  Memory size for script
    :type memory_size: str
    :param reuse_memory: Re-use allocated memory
    :type reuse_memory: str
    :param memory_usage: Memory usage in percent
    :type: memory_usage: int
    """
    command = RUN_SCRIPT_COMMAND % (memory_size, reuse_memory)
    logger.info(
        "Run VM memory load script,"
        " till usage is:%s percent, script command: %s ",
        memory_usage,
        command
    )
    vm_ip = ll_vms.waitForIP(vm_name)[1]['ip']
    if not vm_ip:
        raise exceptions.VMException('Failed to get IP for VM %s' % vm_name)
    logger.info(
        'Copy script %s to VM: %s',
        LOAD_MEMORY_FILE,
        vm_name
    )
    if not copy_file_to_vm(vm_ip, LOAD_MEMORY_FILE, DESTINATION_PATH):
        raise exceptions.VMException(
            'Failed to copy script %s to VM:%s dst path %s' %
            LOAD_MEMORY_FILE, vm_name, DESTINATION_PATH
        )
    logger.info('Running script')
    run_command(vm_name, command)
    logger.info('Wait till memory is catch by script')
    return monitor_vm_load_status(vm_name, memory_usage)


def run_command(vm_name, cmd):
    """
    running command using resource VM, if command failed
    it returns 0 (False) . Command is string send to run as list
    usage: 1. To run load memory script in BG - No output
           2. To run free - output memory usage

    :param vm_name: VM name
    :type: vm_name: str
    :param cmd: Command to run
    :type cmd: str
    :return: If command success returns command out
    else returns 0 (False)
    :rtype: int
    """
    cmd_array = cmd.split()

    vm_exec = helpers.get_vm_resource(vm_name)
    rc, out, error = vm_exec.run_command(cmd_array)
    logger.info("output: %s", out)
    return int(out)


def check_vm_memory_load(vm_name, memory_usage):
    """
     checks VM memory status using free command
     compare with expected memory.

    :param vm_name: VM name to monitor
    :type: vm_name: str
    :param memory_usage: Memory usage in percents
    :type: memory_usage:int
    :return: True if VM load is as expected else False
    :rtype: bool
    """
    total_mem_cmd = "free | grep Mem | awk '{ print $2 }'"
    use_mem_cmd = "free | grep Mem | awk '{ print $3 }'"
    total = run_command(vm_name, total_mem_cmd)
    use = run_command(vm_name, use_mem_cmd)
    if total and use:
        current_usage = (100 * use) / total
        logger.info("Current usage is : {0}%".format(current_usage))
        if int(current_usage) >= memory_usage:
            return True
        else:
            return False
    else:
        return False


def monitor_vm_load_status(vm_name, memory_usage):
    """
     uses timer to monitor VM load status
     calls check_vm_memory_load method in 5 sec
     intervals, time out after 70 sec.

    :param vm_name: VM name to monitor
    :type: vm_name: str
    :param memory_usage: memory usage in percents
    :type: memory_usage: int
    :return: True if VM load is as expected else False
    :rtype: bool
    """
    sample = utils.TimeoutingSampler(
        timeout=DELAY_FOR_SCRIPT,
        sleep=5,
        func=check_vm_memory_load,
        vm_name=vm_name,
        memory_usage=memory_usage
    )
    return sample.waitForFuncStatus(result=True)


def migration_vms_to_diff_hosts(vms):
    """
    Migrate vms that are on different hosts
    using Jobs, wait for all migration till timeout is finished.
    and check that all vm migrated to different host.

    :param vms: Vms list
    :type vms: list
    :return: True if all finish on time, and migrated to different host
    else return False
    :rtype: bool
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
    :param vms: VMs list
    :type vms: list
    :return: maps between Vms and their hosts
    :rtype: dict
    """

    vm_to_host_list = {}
    for vm in vms:
        host = ll_vms.get_vm_host(vm)
        vm_to_host_list[vm] = host
    return vm_to_host_list


def compare_resources_lists(before_list, after_list):
    """
    Compare between list pending resources on hosts
    :param before_list: list of hosts with their resources
    :type before_list: list
    :param after_list: list of hosts with their resources
    :type after_list: list
    :return: True if list are equals else False
    :rtype: bool
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

    :param image_name: The image name in glance
    :type image_name: str
    :param vm_name: VM name to create
    :type vm_name: str
    :raise VMException in case of failure
    """
    sd_name = ll_sd.getStorageDomainNamesForType(
        datacenter_name=config.DC_NAME[0],
        storage_type=config.STORAGE_TYPE
    )[0]
    if not hl_vms.create_vm_using_glance_image(
        vmName=vm_name, vmDescription=vm_name,
        cluster=config.CLUSTER_NAME[0], nic=config.NIC_NAME[0],
        storageDomainName=sd_name, network=config.MGMT_BRIDGE,
        glance_storage_domain_name=config.GLANCE_DOMAIN,
        glance_image=image_name

    ):
        raise exceptions.VMException()


def load_vm_memory_with_load_tool(vm_name, load=500, time_to_run=60):
    """
    Load VM memory with load tool that install on VM

    :param vm_name: VM name
    :type vm_name: str
    :param load: Load value in MB
    :type load: int
    :param time_to_run: Time to run memory load in sec
    :type time_to_run: int
    :return: Process id
    :rtype: int
    """
    logger.info(
        "Run load %s MB on vm %s for %s sec",
        load, vm_name, time_to_run
    )
    cmd = LOAD_VM_COMMAND % (load, time_to_run)
    vm_resource = helpers.get_vm_resource(vm_name)
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

    :param vm_name: VM name
    :type vm_name: str
    :param cluster: cluster name
    :type cluster: str
    :param memory: memory size
    :type memory: int
    :param os_type: vm os type
    :type os_type: str
    :param vm_type: vm type
    :type vm_type: str
    :param display_type: display type
    :type display_type: str
    :param vm_parameters: vm parameter to update after creation
    :type vm_parameters: dict
    :param add_disk: If True add disk to VM after creation
    :param disk_type: disk type, default set to data
    :type disk_type: str
    :param storage_domain: master storage domain
    :type: storage_domain: str
    :return True if all operations succeed Else False
    :rtype: bool
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

    :param vm_name: VM name
    :type vm_name: str
    :param cluster: cluster name
    :type cluster: str
    :param template: template name
    :type template: str
    :param vm_parameters: vm parameter to update after creation
    :type vm_parameters: dict
    :return: True if all operations succeed, Else False
    :rtype: bool
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

    :param vm_name: VM name
    :type vm_name: str
    :param display_type: display type on vm
    :type display_type: str
    :return: True if display port/address exists, else False
    :rtype: bool
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


def create_file_in_vm(vm, vm_resource):
    """
    Create an empty file in vm using vm resource entity

    :param vm: Vm name
    :type vm: str
    :param vm_resource: Resource for the vm
    :type vm_resource: Host resource
    :raises: VMException
    """
    logger.info("attempting to create an empty file in vm: %s", vm)
    if not vm_resource.fs.touch(config_virt.FILE_NAME, config_virt.TEMP_PATH):
        raise exceptions.VMException(
            "Failed to create an empty file on vm: '%s'" % vm
        )


def check_if_file_exist(positive, vm, vm_resource):
    """
    Checks if file (name of file in config) exist or not in the vm using vm
    resource entity

    :param positive: Signifies the expected result
    :type positive: bool
    :param vm: Vm name
    :type vm: str
    :param vm_resource: Command executor for the vm
    :type vm_resource: Host resource executor
    :raises: VMException
    """
    testflow.step(
        "checking if file: %s exists in vm: %s. expecting result: %s",
        config_virt.FILE_NAME, vm, positive
    )
    full_path_to_file = os.path.join(
        config_virt.TEMP_PATH, config_virt.FILE_NAME
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

    :param vm_name: Vm name
    :type vm_name: str
    :return: True if VM successfully rebooted else False
    :rtype: bool
    """

    logger.info("Reboot stateless VM, vm name: %s", vm_name)
    if hl_vms.stop_stateless_vm(vm_name):
        if ll_vms.startVm(positive=True, vm=vm_name, wait_for_ip=True):
            return True
    return False


def get_storage_domains():
    """
    Returns the storage domains: master,export,non master

    :return: returns storage domains
    :rtype: tuple
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

    cluster_name (str): cluster name
    skip (list): list of vms to skip

    Returns: list of vms in cluster

    """
    vms_in_cluster = []
    vms_list = ll_vms.get_vms_from_cluster(cluster=cluster_name)
    for vm_name in vms_list:
            if vm_name not in skip:
                vms_in_cluster.append(vm_name)
    return vms_in_cluster
