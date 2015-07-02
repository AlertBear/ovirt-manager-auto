#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for network migration job
"""

import logging
from utilities.jobs import Job, JobsSet
from rhevmtests.networking import config
from rhevmtests.virt import config as config_virt
from art.rhevm_api.utils import log_listener
from art.rhevm_api.tests_lib.low_level import hosts
from art.unittest_lib.network import find_ip, get_host
import art.rhevm_api.tests_lib.high_level.datacenters as hl_data_center
import art.rhevm_api.tests_lib.low_level.clusters as ll_cluster
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.templates as ll_template
import art.test_handler as test_handler
import art.rhevm_api.resources as resources
import art.core_api.apis_utils as utils
import art.rhevm_api.resources.user as users
import rhevmtests.helpers as helpers

logger = logging.getLogger("Virt_Network_Migration_Helper")
VDSM_LOG = "/var/log/vdsm/vdsm.log"
LOG_MSG = ":starting migration to qemu\+tls://%s/system with miguri tcp://%s"
service_status = "id"
LOAD_MEMORY_FILE = "tests/rhevmtests/virt/migration/memoryLoad.py"
DESTINATION_PATH = "/tmp/memoryLoad.py"
DELAY_FOR_SCRIPT = 70
MEMORY_USAGE = 70
run_script_command = 'python /tmp/memoryLoad.py -s %s &> /tmp/OUT1 & echo $!'


test_handler.find_test_file.__test__ = False


def get_origin_host(vm):
    """
    Check where VM is located
    :param vm: vm on the host
    :type vm: str
    :return: host obj and host name where the VM is located
    :rtype: tuple
    """
    orig_host = get_host(config.VM_NAME[0])
    orig_host_ip = hosts.get_host_ip_from_engine(orig_host)
    for host in config.VDS_HOSTS[:2]:
        if host.ip == orig_host_ip:
            return host, orig_host
    logger.error("VM doesn't reside on provided hosts")


def get_dst_host(orig_host_obj, orig_host):
    """
    Check what is dst Host for migration
    :param orig_host_obj: Origin host object
    :type orig_host_obj: object
    :param orig_host: Origin host name
    :type orig_host: str
    :return: host obj and host name where to migrate VM
    :rtype: tuple
    """
    dst_host_obj = config.VDS_HOSTS[1]
    if orig_host_obj == config.VDS_HOSTS[1]:
        dst_host_obj = config.VDS_HOSTS[0]
    dst_host = config.HOSTS[0]
    if orig_host == config.HOSTS[0]:
        dst_host = config.HOSTS[1]
    return dst_host_obj, dst_host


def migrate_unplug_required(vms, nic_index=1, vlan=None, bond=None, req_nic=2):
    """
    Check dedicated network migration by putting req net down
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
    :return: None or Exception if fails
    """
    (
        orig_host_obj,
        orig_host,
        dst_host_obj,
        dst_host
    ) = get_orig_and_dest_hosts(vms)

    logger.info("Returning VMs back to original host over migration net")
    logger.info("Start migration from %s ", orig_host)
    src, dst = find_ip(
        vm=vms[0], host_list=config.VDS_HOSTS[:2],
        nic_index=nic_index, vlan=vlan, bond=bond
    )

    if not search_log(
        vms=vms, orig_host_obj=orig_host_obj, orig_host=orig_host,
        dst_host_obj=dst_host_obj, dst_host=dst_host, dst_ip=dst,
        req_nic=req_nic
    ):
        raise exceptions.NetworkException(
            "Couldn't migrate %s over %s by putting %s to maintenance" %
            (vms, orig_host_obj.nics[nic_index], orig_host)
        )


def dedicated_migration(
    vms, nic_index=1, vlan=None, bond=None, maintenance=False
):
    """
    Check dedicated network migration
    :param vms: VMs to migrate
    :type vms: list
    :param nic_index: index for the nic where the migration happens
    :type nic_index: int
    :param vlan: Network VLAN
    :type vlan: str
    :param bond: Network Bond
    :type bond: str
    :param maintenance: Migrate by set host to maintenance
    :type maintenance: bool
    :return: None or Exception if fail
    """
    (
        orig_host_obj,
        orig_host,
        dst_host_obj,
        dst_host
    ) = get_orig_and_dest_hosts(vms)

    logger.info("Start migration from %s ", orig_host)
    logger.info("Migrating VM over migration network")
    src, dst = find_ip(
        vm=vms[0], host_list=config.VDS_HOSTS[:2],
        nic_index=nic_index, vlan=vlan, bond=bond
    )

    if not hl_networks.checkICMPConnectivity(
        host=orig_host_obj.ip, user=config.HOSTS_USER,
        password=config.HOSTS_PW, ip=dst
    ):
        logger.error("ICMP wasn't established")

    if not search_log(
        vms=vms, orig_host_obj=orig_host_obj, orig_host=orig_host,
        dst_host_obj=dst_host_obj, dst_host=dst_host, dst_ip=dst,
        maintenance=maintenance
    ):
        raise exceptions.NetworkException(
            "Couldn't migrate %s over %s " %
            (vms, orig_host_obj.nics[nic_index])
        )


def set_host_status(activate=False):
    """
    Set host to operational/maintenance state
    :param activate: activate Host if True, else put into maintenance
    :type activate: bool
    :return: None
    """
    host_state = "active" if activate else "maintenance"
    func = "activateHost" if activate else "deactivateHost"
    call_func = getattr(hosts, func)
    logger.info("Putting hosts besides first two to %s", host_state)
    host_list = hosts.HOST_API.get(absLink=False)
    for host in host_list:
        host_cluster = hosts.getHostCluster(host.name)
        if (
            host_cluster == config.CLUSTER_NAME[0] and
            host.name not in config.HOSTS[:2]
        ):
            if not call_func(True, host.name):
                raise exceptions.NetworkException(
                    "Couldn't put %s into %s" % (host.name, host_state)
                )


def search_log(
    vms, orig_host_obj, orig_host, dst_host_obj, dst_host, dst_ip,
    req_nic=None, maintenance=False
):
    """
    Search log for migration print during migration
    :param vms: VMs to migrate
    :type vms: list
    :param orig_host_obj: Host object of original Host
    :type orig_host_obj: object
    :param orig_host: orig host
    :type orig_host: str
    :param dst_host_obj: Host object of destination Host
    :type dst_host_obj: object
    :param dst_host: destination host
    :type dst_host: str
    :param dst_ip: IP where the migration should be sent
    :type dst_ip: str
    :param req_nic: NIC with required network
    :type req_nic: int
    :param maintenance: Migrate by set host to maintenance
    :type maintenance: bool
    :return True/False
    :rtype: bool
    """
    logger_timeout = config.TIMEOUT * 3 if not req_nic else config.TIMEOUT * 4
    log_msg = LOG_MSG % (dst_host_obj.ip, dst_ip)
    req_nic = orig_host_obj.nics[req_nic] if req_nic else None
    check_vm_migration_kwargs = {
        "vms_list": vms,
        "src_host": orig_host,
        "vm_user": config.HOSTS_USER,
        "vm_password": config.VMS_LINUX_PW,
        "vm_os_type": "rhel"
    }
    watch_logs_kwargs = {
        "ip_for_files": orig_host_obj.ip,
        "username": config.HOSTS_USER,
        "password": config.HOSTS_PW,
        "time_out": logger_timeout,
        "files_to_watch": VDSM_LOG,
        "regex": log_msg,
        "ip_for_execute_command": None,
        "remote_username": None,
        "remote_password": None
    }

    if req_nic:
        func = hl_vms.migrate_by_nic_down
        check_vm_migration_kwargs["nic"] = req_nic
        check_vm_migration_kwargs["password"] = config.HOSTS_PW

    elif maintenance:
        func = hl_vms.migrate_by_maintenance

    else:
        func = hl_vms.migrate_vms
        check_vm_migration_kwargs["dst_host"] = dst_host

    job1 = Job(log_listener.watch_logs, (), watch_logs_kwargs)
    job2 = Job(func, (), check_vm_migration_kwargs)
    job_set = JobsSet()
    job_set.addJobs([job1, job2])
    job_set.start()
    job_set.join(logger_timeout)
    return job1.result[0] and job2.result


def get_orig_and_dest_hosts(vms):
    """
    Get orig_host_obj, orig_host, dst_host_obj, dst_host for VMs and check
    that all VMs are started on the same host
    :param vms: VMs to check
    :type vms: list
    :return: orig_host_obj, orig_host, dst_host_obj, dst_host
    :rtype: object
    """
    orig_hosts = [get_origin_host(vm) for vm in vms]
    logger.info("Checking if all VMs are on the same host")
    if not all([i[1] == orig_hosts[0][1] for i in orig_hosts]):
        raise exceptions.NetworkException("Not all VMs are on the same host")

    orig_host_obj, orig_host = get_origin_host(vms[0])
    dst_host_obj, dst_host = get_dst_host(orig_host_obj, orig_host)
    return orig_host_obj, orig_host, dst_host_obj, dst_host


def create_template():
    """
    create template
    :return: True: if template created else return false
    :rtype: bool
    """
    logger.info("Create VM for Template ")
    if not ll_vms.createVm(
        positive=True,
        vmName=config_virt.MIGRATION_BASE_VM,
        vmDescription=config_virt.VM_DESCRIPTION,
        cluster=config_virt.CLUSTER_NAME[0],
        storageDomainName=config_virt.STORAGE_NAME[0],
        size=config_virt.DISK_SIZE,
        nic=config.NIC_NAME[0],
        network=config_virt.MGMT_BRIDGE,
        user=config_virt.VMS_LINUX_USER,
        password=config_virt.VMS_LINUX_PW,
    ):
        logger.error(
            exceptions.VMException(
                "Failed to create VM %s" %
                config_virt.MIGRATION_BASE_VM
            )
        )
        return False
    logger.info("Create template")
    if not hl_vms.prepare_vm_for_rhel_template(
        config_virt.MIGRATION_BASE_VM,
        config_virt.VMS_LINUX_PW,
        config_virt.RHEL_IMAGE
    ):
        logger.error(exceptions.VMException("Failed to seal VM for template"))
        return False
    if not ll_template.createTemplate(
        True,
        vm=config_virt.MIGRATION_BASE_VM,
        cluster=config_virt.CLUSTER_NAME[0],
        name=config_virt.MIGRATION_TEMPLATE_NAME
    ):
        logger.error(exceptions.TemplateException("Failed to create Template"))
        return False
    logger.info("VM template is ready")
    return True


def add_setup_components():
    """
    Add to setup: New Data Center, Clusters , Hosts
    :return: True: if setup created else returns false
    :rtype: bool
    """
    logger.info("Create new setup...")
    if not hl_data_center.build_setup(
        config_virt.PARAMETERS,
        config_virt.PARAMETERS,
        config_virt.STORAGE_TYPE,
        config_virt.TEST_NAME
    ):
        logger.error("Setup environment failed")
        return False
    logger.info(
        "Add one more cluster %s to data center %s",
        config_virt.CLUSTER_NAME[1],
        config_virt.DC_NAME[0]
    )
    if not ll_cluster.addCluster(
        True,
        name=config_virt.CLUSTER_NAME[1],
        version=config_virt.COMP_VERSION,
        data_center=config_virt.DC_NAME[0],
        cpu=config_virt.CPU_NAME
    ):
        logger.error(
            "Cluster %s creation failed ",
            config_virt.CLUSTER_NAME[1]
        )
        return False
    return True


def prepare_environment():
    """
    Prepare environment
     1. Create DC, Cluster, hosts
     2. Create template
     3. Create VMs from template
    :return: True if setup is ready else return False
    :rtype: bool
    """
    logger.info("Prepare environment")
    if not add_setup_components():
        raise exceptions.TestException("Failed create setup")
    if not create_template():
        logger.error("Failed to create Template")
        return False
    logger.info(
        'Create vms: %s %s',
        config.VM_NAME[:5],
        " from template"
    )
    for vm_name in config.VM_NAME[:5]:
        if not ll_vms.cloneVmFromTemplate(
            True, name=vm_name,
            template=config_virt.MIGRATION_TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        ):
            logger.error("Failed to clone VM")
            return False
    return True


def copy_file_to_vm(
    vm_ip,
    source_file_path,
    destination_path
):
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
        host.users.append(users.RootUser(config.VMS_LINUX_PW))
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


def load_vm_memory(vm_name, memory_size):
    """
     1. Copy load memory python script to VM
     2. Run it, wait for 60 sec to memory be capture by script.

    :param vm_name: vm that run the script
    :type vm_name: str
    :param memory_size:  memory size for script
    :type memory_size: str
    """
    command = run_script_command % memory_size
    logger.info(
        "Run load on VM memory, till usage is:%s percent, script command: %s ",
        MEMORY_USAGE,
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
            'Failed to copy script to VM:%s' %
            vm_name
        )
    logger.info('Running script')
    run_command(vm_ip, command)
    logger.info('Wait till memory is catch by script')
    return monitor_vm_load_status(vm_ip, MEMORY_USAGE)


def run_command(vm_ip, cmd):
    """
    running command using resource HOST, if command failed
    it returns 0 (False) . Command is string send to run as list
    usage: 1. To run load memory script in BG - No output
           2. To run free - output memory usage

    :param vm_ip: VM IP
    :type: vm_ip: str
    :param cmd: Command to run
    :type cmd: str
    :return: If command success returns command out
    else returns 0 (False)
    :rtype: int
    """
    cmd_array = cmd.split()

    vm_exec = helpers.get_host_executor_with_root_user(
        vm_ip, config.VMS_LINUX_PW
    )
    rc, out, error = vm_exec.run_cmd(cmd_array)
    if rc:
        logger.error(
            "Failed to run command on VM:%s ,error:%s ,output:%s",
            vm_ip,
            error,
            out
        )
        return 0
    logger.info("output: %s", out)
    return int(out)


def check_vm_memory_load(vm_ip, memory_usage):
    """
     checks VM memory status using free command
     compare with expected memory.

    :param vm_ip: vm ip to monitor
    :type: vm_name: str
    :param memory_usage: memory usage in percents
    :type: memory_usage:int
    :return: True if VM load is as expected else False
    :rtype: bool
    """
    total_mem_cmd = "free | grep Mem | awk '{ print $2 }'"
    use_mem_cmd = "free | grep Mem | awk '{ print $3 }'"
    total = run_command(vm_ip, total_mem_cmd)
    use = run_command(vm_ip, use_mem_cmd)
    if total and use:
        current_usage = int((use/float(total))*100)
        logger.info("current usage is: %d", current_usage)
        if int(current_usage) >= memory_usage:
            return True
        else:
            return False
    else:
        return False


def monitor_vm_load_status(vm_ip, memory_usage):
    """
     uses timer to monitor VM load status
     calls check_vm_memory_load method in 5 sec
     intervals, time out after 70 sec.

    :param vm_ip: vm IP to monitor
    :type: vm_ip: str
    :param memory_usage: memory usage in percents
    :type: memory_usage: int
    :return: True if VM load is as expected else False
    :rtype: bool
    """
    sample = utils.TimeoutingSampler(
        timeout=DELAY_FOR_SCRIPT,
        sleep=5,
        func=check_vm_memory_load,
        vm_ip=vm_ip,
        memory_usage=memory_usage
    )
    return sample.waitForFuncStatus(result=True)
