"""
Helper functions for network migration job
"""

import logging
logger = logging.getLogger("Network_Migration")

from art.test_handler.exceptions import NetworkException
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import (
    TrafficMonitor, checkICMPConnectivity
)
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.unittest_lib.network import find_ip, get_host

NUM_PACKETS = config.NUM_PACKETS


def get_origin_host(vm):
    """
    Check where VM is located
    param: vm: vm on the host
    return: Dict of host obj and host name where the VM is located
    """
    orig_host = get_host(config.VM_NAME[0])
    orig_host_ip = hosts.get_host_ip_from_engine(orig_host)
    for host in config.VDS_HOSTS:
        if host.ip == orig_host_ip:
            return host, orig_host
    logger.error("VM doesn't reside on provided hosts")


def migrate_unplug_required(nic_index=1, vlan=None, bond=None, req_nic=2):
    """
    Check dedicated network migration by putting req net down
    :param nic_index: index for the nic to do tcpdump
    :param vlan: vlan of the nic to do tcpdump
    :param bond: bond to do tcpdump
    :param req_nic: index for nic with required network
    :return: Monitor traffic for VM migration or raises exception
    """

    orig_host_obj, orig_host = get_origin_host(config.VM_NAME[0])
    logger.info("Returning VMs back to original host over migration net")
    logger.info("Start migration from %s ", orig_host)
    src, dst = find_ip(vm=config.VM_NAME[0],
                       host_list=config.VDS_HOSTS, nic_index=nic_index,
                       vlan=vlan, bond=bond)
    if not hosts.setHostToNonOperational(orig_host=orig_host,
                                         host_password=config.HOSTS_PW,
                                         nic=orig_host_obj.nics[req_nic]):
        raise NetworkException("Cannot start migration by putting"
                               " Nic %s down", orig_host_obj.nics[req_nic])
    if bond:
        if vlan:
            nic = ".".join([bond, vlan])
        else:
            nic = bond
    else:
        nic = orig_host_obj.nics[nic_index]
    with TrafficMonitor(machine=orig_host_obj.ip, user=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        nic=nic,
                        src=src, dst=dst,
                        protocol='tcp', numPackets=NUM_PACKETS) as monitor:
        monitor.addTask(check_vm_migration,
                        vm_names=config.VM_NAME[0],
                        orig_host=orig_host, vm_user=config.HOSTS_USER,
                        host_password=config.HOSTS_PW,
                        vm_password=config.HOSTS_PW,
                        os_type='rhel', nic=orig_host_obj.nics[req_nic],
                        nic_down=False)
    if not monitor.getResult():
        raise NetworkException("Migration failed")


def dedicated_migration(nic_index=1, vlan=None, bond=None):
    """
    Check dedicated network migration
    :param nic_index: index for the nic to do tcpdump
    :param vlan: vlan of the nic to do tcpdump
    :param bond: bond to do tcpdump
    :return: Monitor traffic for VM migration or raises exception
    """
    orig_host_obj, orig_host = get_origin_host(config.VM_NAME[0])
    dest_host = config.HOSTS[0] if orig_host != config.HOSTS[0] else \
        config.HOSTS[1]
    logger.info("Start migration from %s ", orig_host)
    logger.info("Migrating VM over migration network")
    src, dst = find_ip(vm=config.VM_NAME[0],
                       host_list=config.VDS_HOSTS, nic_index=nic_index,
                       vlan=vlan, bond=bond)
    if not checkICMPConnectivity(host=orig_host_obj.ip,
                                 user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, ip=dst):
        logger.error("ICMP wasn't established")

    if bond:
        if vlan:
            nic = ".".join([bond, vlan])
        else:
            nic = bond
    else:
        nic = orig_host_obj.nics[nic_index]
    with TrafficMonitor(machine=orig_host_obj.ip, user=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        nic=nic,
                        src=src, dst=dst,
                        protocol='tcp', numPackets=NUM_PACKETS) as monitor:
        monitor.addTask(check_vm_migration,
                        vm_names=config.VM_NAME[0],
                        orig_host=orig_host, vm_user=config.HOSTS_USER,
                        host_password=config.HOSTS_PW,
                        vm_password=config.HOSTS_PW,
                        os_type='rhel', dest_host=dest_host)
    if not monitor.getResult():
        raise NetworkException("Dedicated Migration failed")


def set_host_status(activate=False):
    """
    Set host to operational/maintenance state
    :param activate: activate Host if True, else put into maintenance
    :return: None
    """
    host_state = "active" if activate else "maintenance"
    func = "activateHost" if activate else "deactivateHost"
    call_func = getattr(hosts, func)
    logger.info("Putting non-Network hosts to %s", host_state)
    host_list = hosts.HOST_API.get(absLink=False)
    for host in host_list:
        if hosts.getHostCluster(host.name) == config.CLUSTER_NAME[0] and \
                host.name not in config.HOSTS:
            if not call_func(True, host.name):
                raise NetworkException(
                    "Couldn't put %s into %s" % (host.name, host_state)
                )
