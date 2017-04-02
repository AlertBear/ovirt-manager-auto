#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for ArbitraryVlanDeviceName job
"""
import logging
import shlex

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level import events

logger = logging.getLogger("ArbitraryVlanDeviceName_Helper")


def add_vlans_to_host(host_obj, vlan_id, vlan_names, nic):
    """
    Add VLAN to host

    Args:
        host_obj (VDS): resources.VDS object
        vlan_id (str): VLAN ID
        vlan_names (list): VLAN names list
        nic (int or str): Interface index (from host_obj.nics) or str
            (for bond nic)

    Returns:
        bool: True if add VLAN succeeded. False otherwise
    """
    interface = host_obj.nics[nic] if isinstance(nic, int) else nic
    cmd = (
        "ip link add dev {vlan_name_1} link {interface} name {vlan_name_2} "
        "type vlan id {vlan_id}"
    )
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    logger.info(
        "Adding VLAN ID: %s. Name: %s. to %s", vlan_id, vlan_names, host_name
    )
    for vid, vname in zip(vlan_id, vlan_names):
        if host_obj.run_command(
            shlex.split(
                cmd.format(
                    vlan_name_1=vname, interface=interface, vlan_name_2=vname,
                    vlan_id=vid
                )
            )
        )[0]:
            return False
    return True


def remove_vlans_and_refresh_capabilities(host_obj, vlans_names):
    """
    Remove VLANs from host and refresh host capabilities

    Args:
        host_obj (vds): resources.VDS object
        vlans_names (list): VLAN names list

    Returns:
        bool: True if remove VLANs succeeded, False otherwise
    """
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    for vlan in vlans_names:
        cmd = shlex.split("ip link delete dev {vlan}".format(vlan=vlan))
        logger.info("Removing %s from %s", vlan, host_name)
        if host_obj.run_command(cmd)[0]:
            return False
    return refresh_host_capabilities(host=host_name)


def refresh_host_capabilities(host):
    """
    Refresh host capabilities

    Args:
        host (str): Host name (from engine)

    Returns:
        bool: True if refresh capabilities succeeded, False otherwise
    """
    last_event = events.get_max_event_id()
    return ll_hosts.refresh_host_capabilities(
        host=host, start_event_id=last_event
    )
