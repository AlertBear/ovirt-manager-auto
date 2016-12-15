#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by SR_IOV feature
"""

import logging
import shlex
import socket
from xml.etree import ElementTree

from utilities import jobs

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sriov_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

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


def create_bond_on_vm(vm_name, vm_resource, vnic):
    """
    Create BOND on VM

    Args:
        vm_name (str): VM name
        vm_resource (Host): VM resource
        vnic (str): Primary vNIC of the VM

    Returns:
        bool: True if creation of the BOND fails, False otherwise
    """
    vm_interfaces = vm_resource.network.all_interfaces()
    sriov_vnic_mac = ll_vms.get_vm_nic_mac_address(
        vm=vm_name, nic=vnic
    )
    sriov_int = None
    for inter in vm_interfaces:
        inter_mac = vm_resource.network.find_mac_by_int(interfaces=[inter])
        if inter_mac and inter_mac[0] == sriov_vnic_mac:
            sriov_int = inter
            break

    assert sriov_int
    reg_int = filter(lambda x: x != sriov_int, vm_interfaces)
    assert reg_int
    reg_int = reg_int[0]
    nm_control_cmd = "sed -i /NM_CONTROLLED=no/d {ifcfg_file}".format(
        ifcfg_file="{ifcfg_path}/ifcfg-{inter}".format(
            ifcfg_path=network_helper.IFCFG_PATH, inter=reg_int
        )
    )
    assert not vm_resource.run_command(shlex.split(nm_control_cmd))[0]
    nmcli_reload_cmd = "nmcli connection reload {inter}".format(inter=reg_int)
    assert not vm_resource.run_command(
        command=shlex.split(nmcli_reload_cmd)
    )[0]
    nmcli_cmd = [
        "nmcli connection add type ethernet con-name {sriov_int_1} ifname"
        " {sriov_int_2}".format(sriov_int_1=sriov_int, sriov_int_2=sriov_int),
        "nmcli connection add type bond con-name bond1 ifname bond1 mode "
        "active-backup primary {sriov_int}".format(sriov_int=sriov_int),
        "nmcli connection modify id bond1 ipv4.method auto ipv6.method ignore",
        "nmcli connection modify id {sriov_int} ipv4.method disabled"
        " ipv6.method ignore".format(sriov_int=sriov_int),
        "nmcli connection modify id {reg_int} ipv4.method disabled ipv6.method"
        " ignore".format(reg_int=reg_int),
        "nmcli connection modify id {sriov_int} connection.slave-type bond "
        "connection.master bond1 connection.autoconnect yes".format(
            sriov_int=sriov_int
        ),
        "nmcli connection modify id {reg_int} connection.slave-type bond "
        "connection.master bond1 connection.autoconnect yes".format(
            reg_int=reg_int
        )
    ]
    assert not all(
        [vm_resource.run_command(
            command=shlex.split(cmd))[0] for cmd in nmcli_cmd]
    )
    nmcli_up_cmd = (
        "nmcli connection down id {sriov_int_1}; "
        "nmcli connection up id {sriov_int_2}; "
        "nmcli connection down id {reg_int_1}; "
        "nmcli connection up id {reg_int_2}; "
        "nmcli connection up bond1".format(
            sriov_int_1=sriov_int, sriov_int_2=sriov_int, reg_int_1=reg_int,
            reg_int_2=reg_int
        )
    )
    try:
        vm_resource.run_command(
            command=shlex.split(nmcli_up_cmd), tcp_timeout=10, io_timeout=10

        )
    except socket.timeout:
        return True


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
