#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics helper file
"""

import logging
import operator

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as rx_tx_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Helper")


def get_vm_resource(vm):
    """
    Get VM executor

    :param vm: VM name
    :type vm: str
    :return: VM executor
    :rtype: resource_vds
    """
    logger.info("Get IP for: %s", vm)
    rc, ips = ll_vms.waitForIP(vm=vm, timeout=conf.TIMEOUT, get_all_ips=True)
    if not rc:
        raise conf.NET_EXCEPTION("Failed to get IP for: %s" % vm)
    ips = ips["ip"]
    ip = [ip for ip in ips if "5.5" not in ip][0]
    return global_helper.get_host_resource(ip, conf.VMS_LINUX_PW)


def config_ip(vms_and_ips):
    """
    Configure temp IP on VMs

    :param vms_and_ips: List of VMs and IPs (list of tuples)
    :type vms_and_ips: list
    :raise: Network exception
    """
    ifcfg_params = {
        "ONBOOT": "yes",
        "NETMASK": "255.255.0.0"
    }
    for vm_and_ip in vms_and_ips:
        vm = vm_and_ip[0]
        ip = vm_and_ip[1]
        vm_resource = get_vm_resource(vm)
        interface = network_helper.get_vm_interfaces_list(
            vm_resource, exclude_nics=[rx_tx_conf.ETH0]
        )
        if not interface:
            raise conf.NET_EXCEPTION("Failed to get interface from %s" % vm)
        interface = interface[0]

        ifcfg_params["IPADDR"] = ip
        logger.info("Setting IP %s on %s for %s", ip, interface, vm)
        vm_resource.network.create_ifcfg_file(
            nic=interface, params=ifcfg_params
        )
        if vm_resource.run_command(command=["ifup", interface])[0]:
            raise conf.NET_EXCEPTION()


def send_icmp(device_and_ips):
    """
    Ping from and to VMs or hosts.
    send [ (vm1/host1, ip1) (vm2/host2, ip2) ] to ping from
    vm1/host1 to vm2/host2 and from vm2 to vm1

    :param device_and_ips: List of devices and IPs (list of tuples)
    :type device_and_ips: list
    """
    device_and_ips[0][0].network.send_icmp(dst=device_and_ips[1][1])
    device_and_ips[1][0].network.send_icmp(dst=device_and_ips[0][1])


def compare_nic_stats(
    nic, vm=None, host=None, total_rx=None, total_tx=None, oper=">="
):
    """
    Compare NIC statistics for VM or Host

    :param nic: NIC name
    :type nic: str
    :param vm: VM name
    :type vm: str
    :param host: Host name
    :type host: str
    :param total_rx: Total RX stats to check against
    :type total_rx: int
    :param total_tx: Total TX stats to check against
    :type total_tx: int
    :param oper: The operator to compare with
    :type oper: str
    :raise: Network exception
    """
    # logger.info("Get %s statistics on %s", nic, vm)
    nic_stat = hl_networks.get_nic_statistics(
        nic=nic, vm=vm, host=host, keys=rx_tx_conf.STAT_KEYS
    )
    comp_oper = operator.ge if oper == ">=" else operator.gt
    logger.info("--------------------------------------------------")
    logger.info("%s, %s", nic_stat["data.total.rx"], total_rx)
    logger.info("%s, %s", nic_stat["data.total.tx"], total_tx)
    logger.info("--------------------------------------------------")
    if not (
        comp_oper(nic_stat["data.total.rx"], total_rx) and
        comp_oper(nic_stat["data.total.tx"], total_tx)
    ):

        logger.error("Comparing NIC statistics failed")
        return False
    return True
