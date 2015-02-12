#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for network migration job
"""

import logging
from utilities.jobs import Job, JobsSet
from rhevmtests.networking import config
from art.rhevm_api.utils import log_listener
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level import hosts
from art.unittest_lib.network import find_ip, get_host
from art.rhevm_api.tests_lib.high_level.vms import (
    migrate_vms, migrate_by_nic_down, migrate_by_maintenance
)
from art.rhevm_api.tests_lib.high_level.networks import (
    checkICMPConnectivity
)

logger = logging.getLogger("Virt_Network_Migration_Helper")
VDSM_LOG = "/var/log/vdsm/vdsm.log"
LOG_MSG = ":starting migration to qemu\+tls://%s/system with miguri tcp://%s"


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
        raise NetworkException(
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

    if not checkICMPConnectivity(
        host=orig_host_obj.ip, user=config.HOSTS_USER,
        password=config.HOSTS_PW, ip=dst
    ):
        logger.error("ICMP wasn't established")

    if not search_log(
        vms=vms, orig_host_obj=orig_host_obj, orig_host=orig_host,
        dst_host_obj=dst_host_obj, dst_host=dst_host, dst_ip=dst,
        maintenance=maintenance
    ):
        raise NetworkException(
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
        if (hosts.getHostCluster(host.name) == config.CLUSTER_NAME[0] and
                host.name not in config.HOSTS[:2]):
            if not call_func(True, host.name):
                raise NetworkException(
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
        "command_to_exec": "",
        "ip_for_execute_command": None,
        "remote_username": None,
        "remote_password": None
    }

    if req_nic:
        func = migrate_by_nic_down
        check_vm_migration_kwargs["nic"] = req_nic
        check_vm_migration_kwargs["password"] = config.HOSTS_PW

    elif maintenance:
        func = migrate_by_maintenance

    else:
        func = migrate_vms
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
        raise NetworkException("Not all VMs are on the same host")

    orig_host_obj, orig_host = get_origin_host(vms[0])
    dst_host_obj, dst_host = get_dst_host(orig_host_obj, orig_host)
    return orig_host_obj, orig_host, dst_host_obj, dst_host
