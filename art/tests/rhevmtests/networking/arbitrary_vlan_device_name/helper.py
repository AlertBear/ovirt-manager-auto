#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for ArbitraryVlanDeviceName job
"""
import logging
from random import randint

import libvirt

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.low_level import events

logger = logging.getLogger("ArbitraryVlanDeviceName_Helper")


def job_tear_down():
    """
    tear_down for ArbitraryVlanDeviceName job
    """
    host_obj = conf.VDS_HOSTS[0]
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    vlans_to_remove = [
        v for v in conf.VLAN_NAMES if is_interface_on_host(
            host_obj=host_obj, interface=v
        )
    ]
    remove_vlan_and_refresh_capabilities(
        host_obj=host_obj, vlan_name=vlans_to_remove
    )
    virsh_delete_bridges(host_obj=host_obj, bridges=conf.BRIDGE_NAMES)

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

    logger.info("Cleaning host interfaces")
    if not hl_host_network.clean_host_interfaces(host_name=conf.HOSTS[0]):
        logger.error("Clean host interfaces failed")


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
    host_exec = host_obj.executor()
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to create %s. err: %s. out: %s", vlan_name, err, out
        )
        return False
    return True


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
    host_exec = host_obj.executor()
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to delete %s. err: %s. out: %s", vlan_name, err, out
        )
        return False
    return True


def virsh_add_bridge(host_obj, bridge):
    """
    Add bridge to virsh via xml file

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param bridge: Bridge name
    :type bridge: str
    :return: True/False
    :rtype: bool
    """
    host_ip = host_obj.ip
    libvirt_conn = get_libvirt_connection(host_ip)

    rand_uuid = randint(1000, 9999)
    vdsm_bridge_name = "vdsm-{0}".format(bridge)
    vdsm_bridge_line = "<name>{0}</name>".format(vdsm_bridge_name)
    bridge_name_line = "<bridge name='{0}'/>".format(bridge)
    uuid_line = "<uuid>a2de77bc-{0}-4ec5-a37a-f8f2dbdf91c9</uuid>".format(
        str(rand_uuid)
    )
    xml_str = ("<network>{0}{1}<forward mode='bridge'/>{2}</network>".format(
        vdsm_bridge_line, uuid_line, bridge_name_line))
    try:
        libvirt_conn.networkCreateXML(xml_str)
    except libvirt.libvirtError as e:
        logger.error("Failed to add network to libvirt from XML. ERR: %s", e)
        return False

    if not get_bridge_from_virsh(host_obj, bridge):
        logger.error("%s not found among libvirt networks", vdsm_bridge_name)
        return False

    return True


def virsh_delete_bridges(host_obj, bridges, undefine=False):
    """
    Delete bridge to virsh via xml file

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param bridges: Bridge name
    :type bridges: list
    :param undefine: Flag if undefine bridge is needed
    :type undefine: bool
    """
    bridges = filter(
        None, [get_bridge_from_virsh(host_obj, b) for b in bridges]
    )
    for br in bridges:
        logger.info("Deleting %s from virsh", br.name())
        br.destroy()
        if undefine:
            br.undefine()


def get_libvirt_connection(host):
    """
    Create libvirt connection to host
    :param host: Host IP or FQDN
    :type host: str
    :return: libvirt connection object
    :rtype: object
    """
    remote_uri = "qemu+ssh://root@{0}/system".format(host)
    return libvirt.open(remote_uri)


def detach_nic_from_bridge(host_obj, bridge, nic):
    """
    Detach NIC from bridge

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param bridge: Bridge name
    :type bridge: str
    :param nic: NIC name
    :type nic: str
    :return: True/False
    :rtype: bool
    """
    cmd = ["brctl", "delif", bridge, nic]
    host_exec = host_obj.executor()
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to detach %s from %s. err: %s. out: %s", nic,  bridge,
            err, out
        )
        return False
    return True


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
    if nic not in [i.name for i in host_nics]:
        return False
    return True


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
        if not virsh_add_bridge(host_obj=host_obj, bridge=br):
            return False

    refresh_capabilities(host=host_name)
    return True


def delete_bridge_on_host_and_virsh(host_obj, bridge):
    """
    Delete bridge on host and delete the bridge on virsh as well

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param bridge: Bridge name
    :type bridge: str
    :return: raise NetworkException on error
    """
    host_name = ll_hosts.get_host_name_from_engine(host_obj)
    logger.info("Delete %s on %s", bridge, host_name)
    virsh_delete_bridges(host_obj=host_obj, bridges=[bridge])
    logger.info("Delete %s on %s", bridge, host_name)
    if not host_obj.network.delete_bridge(bridge=bridge):
        raise conf.NET_EXCEPTION(
            "Failed to delete %s on %s" % (bridge, host_name)
        )


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
    if not refresh_capabilities(host=host_name):
        return False
    return True


def refresh_capabilities(host):
    """
    Refresh host capabilities

    :param host: Host name (from engine)
    :type host: str
    :return: True/False
    :rtype: bool
    """
    logger.info("Getting MAX event ID")
    last_event = events.get_max_event_id(query="")
    logger.info("Refresh capabilities for %s", host)
    if not ll_hosts.refresh_host_capabilities(
        host=host, start_event_id=last_event
    ):
        logger.error("Failed to refresh capabilities for: %s" % host)
        return False
    return True


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
    host_exec = host_obj.executor()
    cmd = ["ip", "a", "s", interface]
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        return False
    return True


def get_bridge_from_virsh(host_obj, bridge):
    """
    Check if bridge exist in virsh

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param bridge: Bridge name
    :type bridge: str
    :return: Network if found else None
    :rtype: object
    """
    host_ip = host_obj.ip
    vdsm_bridge_name = "vdsm-{0}".format(bridge)
    libvirt_connection = get_libvirt_connection(host_ip)
    all_bridges = libvirt_connection.listAllNetworks(0)
    try:
        return [i for i in all_bridges if vdsm_bridge_name == i.name()][0]
    except IndexError:
        logger.warning("%s not found in virsh", bridge)
        return None
