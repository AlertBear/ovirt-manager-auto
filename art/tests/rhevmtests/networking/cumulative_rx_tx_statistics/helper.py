#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics helper file
"""

import logging
import operator

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import config as rx_tx_conf
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Helper")


def config_ip():
    """
    Configure temp IP on VMs
    """
    ifcfg_params = {
        "ONBOOT": "yes",
        "NETMASK": "255.255.0.0"
    }
    for vm, params in rx_tx_conf.VMS_IPS_PARAMS.iteritems():
        mgmt_ip = params.get("mgmt_ip")
        temp_ip = params.get("temp_ip")
        vm_resource = params.get("resource")
        mgmt_interface = vm_resource.network.find_int_by_ip(ip=mgmt_ip)
        interface = network_helper.get_vm_interfaces_list(
            vm_resource=vm_resource, exclude_nics=[mgmt_interface]
        )
        assert interface, "Failed to get interface from %s" % vm
        interface = interface[0]

        ifcfg_params["IPADDR"] = temp_ip
        logger.info("Setting IP %s on %s for %s", temp_ip, interface, vm)
        vm_resource.network.create_ifcfg_file(
            nic=interface, params=ifcfg_params
        )
        assert not vm_resource.run_command(command=["ifup", interface])[0]


def send_icmp(device_and_ips):
    """
    Ping from and to VMs or hosts.
    send [ (vm1/host1, ip1) (vm2/host2, ip2) ] to ping from
    vm1/host1 to vm2/host2 and from vm2 to vm1

    Args:
        device_and_ips (list): List of devices and IPs (list of tuples)
    """
    device_and_ips[0][0].network.send_icmp(dst=device_and_ips[1][1])
    device_and_ips[1][0].network.send_icmp(dst=device_and_ips[0][1])


def compare_nic_stats(
    nic, vm=None, host=None, total_rx=None, total_tx=None, oper=">="
):
    """
    Compare NIC statistics for VM or Host

    Args:
        nic (str): NIC name
        vm (str): VM name
        host (str): Host name
        total_rx (int): Total RX stats to check against
        total_tx (int): Total TX stats to check against
        oper (str): The operator to compare with

    Raises:
        AssertionError: if comparing NIC statistics failed
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
