#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by SR_IOV feature
"""

import logging
import shlex
import socket
from xml.etree import ElementTree

from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    vms as hl_vms
)
import config as sriov_conf
import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.low_level import (
    events as ll_events,
    hosts as ll_hosts
)
from art.rhevm_api.utils import jobs

logger = logging.getLogger("SR_IOV_Helper")


def update_host_nics():
    """
    Clear cache and update first Host NICs
    """
    logger.info("Get all NICs from host %s", conf.HOST_0_NAME)
    conf.VDS_0_HOST.cache.clear()
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics


def get_vlan_id_from_vm_xml(vm):
    """
    Get VLAN id of vm interface from running VM

    Args:
        vm (str): VM name

    Returns:
        str: VLAN ID

    Raises:
        NetworkException: If VLAN not found among VM interfaces
    """
    logger.info("Get VLAN ID from %s XML", vm)
    dump_xml_cmd = ["virsh", "-r", "dumpxml", vm]
    rc, xml_output, _ = conf.VDS_0_HOST.run_command(dump_xml_cmd)
    assert not rc

    xml_obj = ElementTree.fromstring(xml_output)
    interfaces = xml_obj.find("devices").findall("interface")
    vlan_interface = filter(
        lambda x: x is not None, [i.find("vlan") for i in interfaces]
    )
    assert vlan_interface, "VLAN not found on VM %s interfaces" % vm
    return vlan_interface[0].find("tag").get("id")


def create_bond_on_vm(vm_name, vm_resource, vnics, mode=1, proto="auto"):
    """
    Create BOND on VM

    Args:
        vm_name (str): VM name
        vm_resource (Host): VM resource
        vnics (list): Primary vNIC of the VM
        mode (int): BOND mode
        proto (str): ipv4.method for BOND (auto, disabled)

    Raises:
        AssertionError: If creation of the BOND fails.
    """
    bond = "bond1"
    remove_nm_controlled_cmd = (
        "sed -i /NM_CONTROLLED/d /etc/sysconfig/network-scripts/ifcfg-{"
        "interface}"
    )
    active_interface = vm_resource.network.get_info().get("interface")
    assert not vm_resource.run_command(
        command=shlex.split(remove_nm_controlled_cmd.format(
            interface=active_interface)
        )
    )[0]
    assert not vm_resource.run_command(
        command=shlex.split("nmcli connection reload")
    )[0]

    secondary_interface = "System\ {active_interface}".format(
        active_interface=active_interface
    )
    primary_interface = hl_networks.get_vm_interface_by_vnic(
        vm=vm_name, vm_resource=vm_resource, vnic=vnics[0]
    )

    # Create connection in NM for the new interface
    nmcli_add_con = [
        "nmcli connection add type ethernet con-name {primary_interface_1} "
        "ifname {primary_interface_2}".format(
            primary_interface_1=primary_interface,
            primary_interface_2=primary_interface
        ),
        "nmcli connection modify id {primary_interface} ipv4.method disabled"
        " ipv6.method ignore".format(primary_interface=primary_interface),
    ]
    assert not all(
        [
            vm_resource.run_command(
                command=shlex.split(cmd))[0] for cmd in
            nmcli_add_con
        ]
    )

    # Create BOND
    create_bond_cmds = [
        "nmcli connection add type bond con-name {bond} ifname "
        "bond1 mode {mode} {primary}".format(
            bond=bond, mode=mode, primary="primary {primary_interface}".format(
                primary_interface=primary_interface
            ) if mode == 1 else ""
        ),
        "nmcli connection modify id {bond} ipv4.method {proto} "
        "ipv6.method ignore".format(bond=bond, proto=proto)
    ]
    assert not all(
        [
            vm_resource.run_command(
                command=shlex.split(cmd))[0] for cmd in
            create_bond_cmds
        ]
    )

    # Add the slaves to the BOND
    for inter in primary_interface, secondary_interface:
        nmcli_add_slave = (
            "nmcli connection modify id {inter} connection.slave-type "
            "bond connection.master {bond} connection.autoconnect "
            "yes".format(bond=bond, inter=inter)
        )
        assert not vm_resource.run_command(
            command=shlex.split(nmcli_add_slave)
        )[0]

    # Deactivate all connection and activate again to get the new configuration
    nmcli_up_cmd = (
        "nmcli connection down {primary_interface_1};"
        "nmcli connection down {secondary_interface_1};"
        "nmcli connection down {bond_1};"
        "nmcli connection up {bond_2};"
        "nmcli connection up {primary_interface_2};"
        "nmcli connection up {secondary_interface_2}"
    ).format(
        primary_interface_1=primary_interface,
        secondary_interface_1=secondary_interface,
        bond_1=bond,
        bond_2=bond,
        primary_interface_2=primary_interface,
        secondary_interface_2=secondary_interface
    )
    try:
        vm_resource.run_command(
            command=shlex.split(
                nmcli_up_cmd
            ), tcp_timeout=10, io_timeout=10
        )
    except socket.timeout:
        pass


def check_ping_during_vm_migration(ping_kwargs, migration_kwargs):
    """
    Check VM migration while sending ping to the VM

    Args:
        ping_kwargs (dict): send_ping function kwargs
        migration_kwargs (dict): migrate_vms function kwargs

    Returns:
        bool: True if migration and ping tests were successful, False if one
            of them failed

    """
    target = ping_kwargs.pop("src_resource")
    ping_job = jobs.Job(
        target=target.network.send_icmp, args=(), kwargs=ping_kwargs
    )
    migrate_job = jobs.Job(
        target=hl_vms.migrate_vms, args=(), kwargs=migration_kwargs
    )
    job_set = jobs.JobsSet()
    job_set.addJobs(jobs=[ping_job, migrate_job])
    job_set.start()
    job_set.join(timeout=sriov_conf.MIGRATION_TIMEOUT)

    logger.info(
        "Migration job result: %s\nping job result: %s", migrate_job.result,
        ping_job.result
    )

    return migrate_job.result and ping_job.result


def wait_for_refresh_caps(last_event):
    """
    Wait until host refreshed the capabilities is done

    When hot plug/unplug sr-iov vNIC from VM getVdsCaps is called and we
    need to make sure that we wait till it's done before doing anything.

    Args:
        last_event (Event): Event object of last event to search from

    Returns:
        bool: True if refresh caps done, False otherwise
    """
    content = "Successfully refreshed the capabilities"
    return ll_events.find_event(
        last_event=last_event, event_code=sriov_conf.REFRESH_CAPS_CODE,
        content=content, matches=1
    )


def get_first_free_vf_host_device(hostname):
    """
    Get the first free (unallocated to a VM) VF network host device name

    Args:
        hostname (str): Host name to get the device from

    Returns:
        str: Host device name, or empty string if none found
    """
    # Look for unallocated (without VM instance) host devices with product name
    # containing "Virtual Function"
    vf_devices_on_host = [
        dev for dev in ll_hosts.get_host_devices(host_name=hostname)
        if hasattr(dev.product, "name") and
        "virtual function" in dev.product.name.lower() and
        not dev.vm
    ]
    return vf_devices_on_host[0].name if vf_devices_on_host else ""
