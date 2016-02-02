#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for MultiHost
"""

import logging
import config as conf
from art.rhevm_api.utils import test_utils
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("MultiHost_Helper")


def update_network_and_check_changes(
    net, nic, hosts=None, vds_hosts=None, matches=1, **kwargs
):
    """
    Update network and check that the updated network params are reflected
    on engine and on the host

    :param net: Network name
    :type net: str
    :param nic: Host NIC name
    :type nic: str
    :param hosts: Hosts list to check the changes on
    :type hosts: list
    :param vds_hosts: VDS resources list to check the changes on
    :type vds_hosts: list
    :param matches: Number of matches to find in events
    :type matches: int
    :param kwargs: Params for update network function
        :vlan: VLAN id (str)
        :mtu: MTU value (int)
        :bridge: Bridge value (True for VM network, False for non-VM) (bool)
    :type kwargs: dict
    :raise: NetworkException
    """
    vlan_id = kwargs.get("vlan_id")
    mtu = kwargs.get("mtu")
    bridge = kwargs.get("bridge")
    if bridge is not None:
        kwargs.pop("bridge")
        kwargs["usages"] = "vm" if bridge else ""

    hosts = hosts if hosts else [conf.HOST_NAME_0]
    vds_hosts = vds_hosts if vds_hosts else [conf.VDS_HOST_0]
    network_helper.call_function_and_wait_for_sn(
        func=ll_networks.updateNetwork, content=net, positive=True,
        network=net, matches=matches, **kwargs
    )
    for host, vds_host in zip(hosts, vds_hosts):
        if mtu:
            check_mtu(
                net=net, mtu=mtu, nic=nic, host=host, vds_host=vds_host
            )
        if vlan_id:
            check_vlan(
                net=net, vlan=vlan_id, nic=nic, host=host, vds_host=vds_host
            )
        if bridge:
            check_bridge(
                net=net, bridge=bridge, nic=nic, host=host, vds_host=vds_host
            )


def check_mtu(net, mtu, nic, host, vds_host):
    """
    Check that the updated network MTU is reflected on engine and on
    the host

    :param net: Network name
    :type net: str
    :param mtu: MTU value
    :type mtu: int
    :param nic: Host NIC name
    :type nic: str
    :param host: Host name to check the changes on
    :type host: str
    :param vds_host: VDS resource to check the changes on
    :type vds_host: resources.VDS
    :raise: NetworkException
    """
    mtu_dict = {
        "mtu": mtu
    }
    logger.info(conf.UPDATE_CHANGES_ENGINE)
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **mtu_dict
    ):
        raise conf.NET_EXCEPTION()

    logger.info(conf.UPDATE_CHANGES_HOST)
    logger.info(
        "Checking logical layer of bridged network %s on host %s", net, host
    )

    if not test_utils.check_mtu(
        vds_resource=vds_host, mtu=mtu, physical_layer=False,
        network=net, nic=nic
    ):
        raise conf.NET_EXCEPTION("Logical layer: MTU should be %s" % mtu)

    logger.info(
        "Checking physical layer of bridged network %s on host %s", net, host
    )
    if not test_utils.check_mtu(vds_resource=vds_host, mtu=mtu, nic=nic):
        raise conf.NET_EXCEPTION("Physical layer: MTU should be %s" % mtu)


def check_vlan(net, vlan, nic, host, vds_host):
    """
    Check that the updated network VLAN is reflected on engine and on
    the host

    :param net: Network name
    :type net: str
    :param vlan: VLAN value
    :type vlan: str
    :param nic: Host NIC name
    :type nic: str
    :param host: Host name to check the changes on
    :type host: str
    :param vds_host: VDS resource to check the changes on
    :type vds_host: resources.VDS
    :raise: NetworkException
    """
    vlan_dict = {
        "vlan_id": vlan
    }
    logger.info(conf.UPDATE_CHANGES_ENGINE)
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **vlan_dict
    ):
        raise conf.NET_EXCEPTION()

    logger.info(conf.UPDATE_CHANGES_HOST)
    if not ll_networks.is_vlan_on_host_network(
        vds_resource=vds_host, interface=nic, vlan=vlan
    ):
        raise conf.NET_EXCEPTION()


def check_bridge(net, bridge, nic, host, vds_host):
    """
    Check that the updated network bridge is reflected on engine and on
    the host

    :param net: Network name
    :type net: str
    :param bridge: Bridge value
    :type bridge: bool
    :param nic: Host NIC name
    :type nic: str
    :param host: Host name to check the changes on
    :type host: str
    :param vds_host: VDS resource to check the changes on
    :type vds_host: resources.VDS
    :raise: NetworkException
    """
    bridge_dict = {
        "bridge": bridge
    }
    logger.info(conf.UPDATE_CHANGES_ENGINE)
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **bridge_dict
    ):
        raise conf.NET_EXCEPTION()

    logger.info(conf.UPDATE_CHANGES_HOST)
    if not ll_networks.is_host_network_is_vm(
        vds_resource=vds_host, net_name=net,
    ):
        raise conf.NET_EXCEPTION()
