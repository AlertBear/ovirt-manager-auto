#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for MultiHost
"""

import logging
import config as multi_host_conf
import rhevmtests.networking.config as conf
from art.rhevm_api.utils import test_utils
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("MultiHost_Helper")


def update_network_and_check_changes(
    net, nic=1, hosts=None, vds_hosts=None, matches=1, **kwargs
):
    """
    Update network and check that the updated network params are reflected
    on engine and on the host

    Args:
        net (str): Network name
        nic (int): Host NIC index
        hosts (list): Hosts list to check the changes on
        vds_hosts (list): VDS resources list to check the changes on
        matches (int): Number of matches to find in events
        kwargs (dict): Params for update network function

    Keyword Args:
        vlan (str): VLAN id (str)
        mtu (int): MTU value (int)
        bridge (bool): Bridge value (True for VM network, False for non-VM)

    Returns:
        bool: True/False
    """
    vlan_id = kwargs.get("vlan_id")
    mtu = kwargs.get("mtu")
    bridge = kwargs.get("bridge")
    if bridge is not None:
        kwargs.pop("bridge")
        kwargs["usages"] = "vm" if bridge else ""

    hosts = hosts if hosts else [conf.HOST_0_NAME]
    vds_hosts = vds_hosts if vds_hosts else [conf.VDS_0_HOST]
    network_helper.call_function_and_wait_for_sn(
        func=ll_networks.update_network, content=net, positive=True,
        network=net, matches=matches, **kwargs
    )
    for host, vds_host in zip(hosts, vds_hosts):
        #  Needed when NIC is BOND and not host NIC
        nic = vds_host.nics[nic] if isinstance(nic, int) else nic
        if mtu:
            return check_mtu(
                net=net, mtu=mtu, nic=nic, host=host,
                vds_host=vds_host
            )
        if vlan_id:
            return check_vlan(
                net=net, vlan=vlan_id, nic=nic, host=host,
                vds_host=vds_host
            )
        if bridge is not None:
            return check_bridge(
                net=net, bridge=bridge, nic=nic, host=host,
                vds_host=vds_host
            )


def check_mtu(net, mtu, nic, host, vds_host):
    """
    Check that the updated network MTU is reflected on engine and on
    the host

    Args:
        net (str): Network name
        mtu (int): MTU value
        nic (str): Host NIC name
        host (str): Host name to check the changes on
        vds_host (resources.VDS): VDS resource to check the changes on

    Returns:
        bool: True/False
    """
    mtu_dict = {
        "mtu": mtu
    }
    logger.info(multi_host_conf.UPDATE_CHANGES_ENGINE)
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **mtu_dict
    ):
        return False

    logger.info(multi_host_conf.UPDATE_CHANGES_HOST)
    logger.info(
        "Checking logical layer of bridged network %s on host %s", net, host
    )

    if not test_utils.check_mtu(
        vds_resource=vds_host, mtu=mtu, physical_layer=False,
        network=net, nic=nic
    ):
        logger.error("Logical layer: MTU should be %s" % mtu)
        return False

    logger.info(
        "Checking physical layer of bridged network %s on host %s", net, host
    )
    if not test_utils.check_mtu(vds_resource=vds_host, mtu=mtu, nic=nic):
        logger.error("Physical layer: MTU should be %s" % mtu)
        return False
    return True


def check_vlan(net, vlan, nic, host, vds_host):
    """
    Check that the updated network VLAN is reflected on engine and on
    the host

    Args:
        net (str): Network name
        vlan (str): VLAN value
        nic: Host NIC name
        host (str): Host name to check the changes on
        vds_host (resources.VDS): VDS resource to check the changes on

    Returns:
        bool: True/False
    """
    vlan_dict = {
        "vlan_id": vlan
    }
    logger.info(multi_host_conf.UPDATE_CHANGES_ENGINE)
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **vlan_dict
    ):
        return False

    logger.info(multi_host_conf.UPDATE_CHANGES_HOST)
    if not ll_networks.is_vlan_on_host_network(
        vds_resource=vds_host, interface=nic, vlan=vlan
    ):
        return False
    return True


def check_bridge(net, bridge, nic, host, vds_host):
    """
    Check that the updated network bridge is reflected on engine and on
    the host

    Args:
        net (str): Network name
        bridge (bool): Bridge value
        nic (str): Host NIC name
        host (str): Host name to check the changes on
        vds_host (resources.VDS): VDS resource to check the changes on

    Returns:
        bool: True/False
    """
    bridge_dict = {
        "bridge": bridge
    }
    logger.info(multi_host_conf.UPDATE_CHANGES_ENGINE)
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **bridge_dict
    ):
        return False

    logger.info(multi_host_conf.UPDATE_CHANGES_HOST)
    res = ll_networks.is_host_network_is_vm(
        vds_resource=vds_host, net_name=net,
    )
    return res == bridge
