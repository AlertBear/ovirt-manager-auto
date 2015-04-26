#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics helper file
"""

import config as c
import logging
import shlex
import rhevmtests.helpers as global_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Helper")


def get_vm_exec(vm):
    """
    Get VM executor

    :param vm: VM name
    :type vm: str
    :return: VM executor
    :rtype: resource_vds
    """
    logger.info("Get IP for: %s", vm)
    rc, ip = ll_vms.waitForIP(vm=vm, timeout=c.TIMEOUT)
    if not rc:
        raise c.NET_EXCEPTION("Failed to get IP for: %s" % vm)
    ip = ip["ip"]
    return global_helper.get_host_executor_with_root_user(
        ip, c.VMS_LINUX_PW
    )


def config_temp_ip(vms_and_ips):
    """
    Configure temp IP on VMs

    :param vms_and_ips: List of VMs and IPs (list of tuples)
    :type vms_and_ips: list
    :raise: Network exception
    """
    int_cmd = "ls -la /sys/class/net | grep 'pci' | grep -o '[^/]*$'"
    for vm_and_ip in vms_and_ips:
        vm = vm_and_ip[0]
        ip = vm_and_ip[1]
        vm_exec = get_vm_exec(vm)
        logger.info("Getting interfaces list from %s", vm)
        rc, out, err = vm_exec.run_cmd(shlex.split(int_cmd))
        if rc:
            raise c.NET_EXCEPTION(
                "Failed to run command to get interface list from %s. ERR: "
                "%s, %s" % (vm, err, out)
            )
        interface = filter(lambda x: x != c.ETH0, out.splitlines())
        if not interface:
            raise c.NET_EXCEPTION("Failed to get interface from %s" % vm)

        logger.info("Setting temp IP on %s for %s", interface[0], vm)
        rc, out, err = vm_exec.run_cmd(["ifconfig", interface[0], ip])
        if rc:
            raise c.NET_EXCEPTION(
                "Failed to set temp IP on %s for %s. ERR: %s, %s" % (
                    interface[0], vm, err, out
                )
            )


def ping_from_to_vms(vms_and_ips):
    """
    Ping from and to VMs.
    send [ (vm1, ip1) (vm2, ip2) ] to ping from vm1 to vm2 and from vm2 to vm1

    :param vms_and_ips: List of VMs and IPs (list of tuples)
    :type vms_and_ips: list
    """
    ping_cmd = "ping -c 5 %s"
    first_ip = vms_and_ips[0][1]
    second_ip = vms_and_ips[1][1]
    vms_exec = [get_vm_exec(vm[0]) for vm in vms_and_ips]
    for vm_exec in vms_exec:
        logger.info("Ping %s from %s", first_ip, second_ip)
        vm_exec.run_cmd((ping_cmd % first_ip).split())
        logger.info("Ping %s from %s", second_ip, first_ip)
        vm_exec.run_cmd((ping_cmd % second_ip).split())


def check_if_nic_stat_reset(nic, vm, total_rx, total_tx):
    """
    Check if NIC stats have been reset

    :param nic: NIC name
    :type nic: str
    :param vm: VM name
    :type vm: str
    :param total_rx: Total RX stats to check against
    :type total_rx: int
    :param total_tx: Total TX stats to check against
    :type total_tx: int
    :raise: Network exception
    """
    logger.info("Get %s statistics on %s", nic, vm)
    nic_stat = hl_networks.get_nic_statistics(nic=nic, vm=vm, keys=c.STAT_KEYS)
    if not (
        nic_stat["data.total.rx"] >= total_rx and
        nic_stat["data.total.tx"] >= total_tx
    ):
        raise c.NET_EXCEPTION(
            "Total stats are not saved after hot unplugged NIC"
        )


def plug_unplug_vnic(vm, plug=True):
    """
    Plug or unplug VNIC

    :param vm: VM name
    :type vm: str
    :param plug: True for plug, False for unplug
    :type plug: bool
    :raise: Network exception
    """
    plugged = "plug" if plug else "unplugged"
    logger.info("Hot %s %s from %s", plugged, c.NIC_1, vm)
    if not ll_vms.updateNic(True, vm, c.NIC_1, plugged=plug):
        raise c.NET_EXCEPTION(
            "Failed to hot %s %s from %s" % (plugged, c.NIC_1, vm)
        )
