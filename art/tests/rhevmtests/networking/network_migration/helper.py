"""
Helper functions for network migration job
"""

import logging
from utilities.jobs import Job, JobsSet

from rhevmtests.networking import config
from art.rhevm_api.utils import log_listener
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import (
    checkICMPConnectivity
)
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.unittest_lib.network import find_ip, get_host

logger = logging.getLogger("Network_Migration_Helper")
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


def migrate_unplug_required(nic_index=1, vlan=None, bond=None, req_nic=2):
    """
    Check dedicated network migration by putting req net down
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

    orig_host_obj, orig_host = get_origin_host(config.VM_NAME[0])
    dst_host_obj, dst_host = get_dst_host(orig_host_obj, orig_host)
    logger.info("Returning VMs back to original host over migration net")
    logger.info("Start migration from %s ", orig_host)
    src, dst = find_ip(
        vm=config.VM_NAME[0], host_list=config.VDS_HOSTS[:2],
        nic_index=nic_index, vlan=vlan, bond=bond
    )

    if not search_log(
        orig_host_obj, orig_host, dst_host_obj, dst_host, dst, req_nic
    ):
        raise NetworkException(
            "Couldn't migrate %s over %s by putting %s to maintenance" %
            (config.VM_NAME[0], orig_host_obj.nics[nic_index], orig_host)
        )


def dedicated_migration(nic_index=1, vlan=None, bond=None):
    """
    Check dedicated network migration
    :param nic_index: index for the nic to do tcpdump
    :type nic_index: int
    :param vlan: Network VLAN
    :type vlan: str
    :param bond: Network Bond
    :type bond: str
    :return: None or Exception if fail
    """
    orig_host_obj, orig_host = get_origin_host(config.VM_NAME[0])
    dst_host_obj, dst_host = get_dst_host(orig_host_obj, orig_host)
    logger.info("Start migration from %s ", orig_host)
    logger.info("Migrating VM over migration network")
    src, dst = find_ip(
        vm=config.VM_NAME[0], host_list=config.VDS_HOSTS[:2],
        nic_index=nic_index, vlan=vlan, bond=bond
    )

    if not checkICMPConnectivity(
        host=orig_host_obj.ip, user=config.HOSTS_USER,
        password=config.HOSTS_PW, ip=dst
    ):
        logger.error("ICMP wasn't established")

    if not search_log(
        orig_host_obj, orig_host, dst_host_obj, dst_host, dst
    ):
        raise NetworkException(
            "Couldn't migrate %s over %s " %
            (config.VM_NAME[0], orig_host_obj.nics[nic_index])
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
    orig_host_obj, orig_host, dst_host_obj, dst_host, dst_ip, req_nic=None
):
    """
    Search log for migration print during migration
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
    :return True/False
    :rtype: bool
    """
    logger_timeout = config.TIMEOUT * 3
    log_msg = LOG_MSG % (dst_host_obj.ip, dst_ip)
    args1 = (
        VDSM_LOG, log_msg, "", logger_timeout,
        orig_host_obj.ip, config.HOSTS_USER, config.HOSTS_PW)
    job1 = Job(log_listener.watch_logs, args1)
    args2 = (
        config.VM_NAME[0], orig_host,
        config.HOSTS_USER, config.HOSTS_PW, config.HOSTS_PW,
        "rhel", dst_host
    )
    if not req_nic:
        job2 = Job(check_vm_migration, args2)
    else:
        job2 = Job(check_vm_migration, args2 + (orig_host_obj.nics[req_nic],))
    jobset = JobsSet()
    jobset.addJobs([job1, job2])
    jobset.start()
    jobset.join(logger_timeout)
    return job1.result[0] and job2.result
