#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for ArbitraryVlanDeviceName job
"""
import logging

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_helper
from art.rhevm_api.tests_lib.low_level import events

logger = logging.getLogger("ArbitraryVlanDeviceName_Helper")


def job_tear_down():
    """
    tear_down for ArbitraryVlanDeviceName job
    """
    host_obj = conf.VDS_0_HOST
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    vlans_to_remove = [
        v for v in conf.VLAN_NAMES if is_interface_on_host(
            host_obj=host_obj, interface=v
        )
    ]
    remove_vlan_and_refresh_capabilities(
        host_obj=host_obj, vlan_name=vlans_to_remove
    )
    for br in conf.BRIDGE_NAMES:
        if net_helper.virsh_is_network_exists(
            vds_resource=conf.VDS_0_HOST, network=br
        ):
            net_helper.virsh_delete_network(
                vds_resource=conf.VDS_0_HOST, network=br
            )

    for bridge in conf.BRIDGE_NAMES:
        logger.info("Checking if %s exists on %s", bridge, host_name)
        if host_obj.network.get_bridge(bridge):
            logger.info("Delete BRIDGE: %s on %s", bridge, host_name)
            try:
                host_obj.network.delete_bridge(bridge=bridge)
            except Exception:
                logger.error(
                    "Failed to delete BRIDGE: %s on %s", bridge, host_name
                )

    hl_host_network.clean_host_interfaces(host_name=conf.HOST_0_NAME)


def host_add_vlan(host_obj, vlan_id, vlan_name, nic):
    """
    Create VLAN interface on hosts

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param vlan_id: VLAN ID
    :type vlan_id: str
    :param nic: Interface index (from host_obj.nics) or str (for bond nic)
    :type nic: int or str
    :param vlan_name: VLAN name
    :type vlan_name: str
    :return: True/False
    :rtype: bool
    """
    interface = host_obj.nics[nic] if isinstance(nic, int) else nic
    cmd = [
        "ip", "link", "add", "dev", vlan_name, "link", interface, "name",
        vlan_name, "type", "vlan", "id", vlan_id
    ]
    return not host_obj.run_command(cmd)[0]


def host_delete_vlan(host_obj, vlan_name):
    """
    Delete VLAN from host

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param vlan_name: VLAN name
    :type vlan_name: str
    :return: True/False
    :rtype: bool
    """
    cmd = ["ip", "link", "delete", "dev", vlan_name]
    return not host_obj.run_command(cmd)[0]


def check_if_nic_in_host_nics(nic, host):
    """
    Check if NIC is among the host NICs collection

    :param nic: NIC name
    :type nic: str
    :param host: Host name (in engine)
    :type host: str
    :return: True/False
    :rtype: bool
    """
    logger.info("Check that %s exists on %s via engine", nic, host)
    host_nics = ll_hosts.get_host_nics_list(host=host)
    return nic in [i.name for i in host_nics]


def add_bridge_on_host_and_virsh(host_obj, bridge, network):
    """
    Create bridge on host and create the bridge on virsh as well

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param bridge: Bridge name
    :type bridge: list
    :param network: Network name
    :type network: list
    :return: True/False
    :rtype: bool
    """
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    for br, net in zip(bridge, network):
        logger.info("Attaching %s to %s on %s", net, br, host_name)
        if not host_obj.network.add_bridge(bridge=br, network=net):
            return False

        logger.info("Adding %s to %s via virsh", br, host_name)
        if not net_helper.virsh_add_network(
            vds_resource=conf.VDS_0_HOST, network=br
        ):
            return False

    return refresh_capabilities(host=host_name)


def add_vlans_to_host(host_obj, vlan_id, vlan_name, nic):
    """
    Add VLAN to host

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param nic: Interface index (from host_obj.nics) or str (for bond nic)
    :type nic: int or str
    :param vlan_id: VLAN id
    :type vlan_id: list
    :param vlan_name: VLAN name
    :type vlan_name: list
    :return: True/False
    :rtype: bool
    """
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    logger.info(
        "Adding VLAN ID: %s. Name: %s. to %s", vlan_id, vlan_name, host_name
    )
    for vid, vname in zip(vlan_id, vlan_name):
        if not host_add_vlan(
            host_obj=host_obj, vlan_id=vid, nic=nic, vlan_name=vname
        ):
            return False
    return True


def remove_vlan_and_refresh_capabilities(host_obj, vlan_name):
    """
    Add vlan to host and refresh host capabilities

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param vlan_name: VLAN name
    :type vlan_name: list
    :return: True/False
    :rtype: bool
    """
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    for vlan in vlan_name:
        logger.info("Removing %s from %s", vlan, host_name)
        if not host_delete_vlan(host_obj=host_obj, vlan_name=vlan):
            return False
    return refresh_capabilities(host=host_name)


def refresh_capabilities(host):
    """
    Refresh host capabilities

    :param host: Host name (from engine)
    :type host: str
    :return: True/False
    :rtype: bool
    """
    last_event = events.get_max_event_id(query="")
    return ll_hosts.refresh_host_capabilities(
        host=host, start_event_id=last_event
    )


def is_interface_on_host(host_obj, interface):
    """
    Check if interface exists on host

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param interface: Interface name
    :type interface: str
    :return: True/False
    :rtype: bool
    """
    cmd = ["ip", "a", "s", interface]
    return not host_obj.run_command(cmd)[0]
