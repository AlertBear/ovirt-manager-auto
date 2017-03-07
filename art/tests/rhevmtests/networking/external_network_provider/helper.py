#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for External Network Provider
"""

import logging
import re
import shlex

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as ovn_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as net_helper
from art.unittest_lib import testflow
from utilities import jobs

logger = logging.getLogger("external_network_provider_helper")


def run_vm_on_host(vm, host):
    """
    Run a VM on host and save its Host resource

    Args:
        vm (str): VM name
        host (str): Host name

    Returns:
        bool: True if VM started successfully, False otherwise

    """
    if net_helper.run_vm_once_specific_host(
        vm=vm, host=host, wait_for_up_status=True
    ):
        ovn_conf.OVN_VMS_RESOURCES[vm] = global_helper.get_vm_resource(
            vm=vm, start_vm=False
        )
        return True
    return False


def set_ip_non_mgmt_nic(vm, address_type="static", ip_network=None):
    """
    Set IP network on the non-mgmt NIC of a VM that has two NIC's installed

    Args:
        vm (str): VM name
        address_type (str): IP address type, can be "static" for static, or
            "dhcp" for DHCP
        ip_network (str): IP network to be set (in CIDR convention, e.g.
            192.168.100.0/24) to be used in conjunction with static address
            type

    Returns:
        str: IP address of the VM, or empty string if error has occurred

    """
    interface = net_helper.get_non_mgmt_nic_name(vm=vm)
    if not interface:
        return ""
    interface = interface[0]

    vm_resource = ovn_conf.OVN_VMS_RESOURCES[vm]

    if address_type == "static" and ip_network:
        ret = vm_resource.run_command(
            command=shlex.split(
                ovn_conf.OVN_CMD_SET_IP.format(net=ip_network, eth=interface)
            )
        )
        return ip_network if ret[0] == 0 else ""

    if address_type == "dhcp":
        network = vm_resource.get_network()

        logger.info(
            "Requesting IP address from DHCP on VM: %s interface: %s",
            vm, interface
        )
        if vm_resource.run_command(
            command=shlex.split(
                ovn_conf.OVN_CMD_DHCLIENT.format(eth=interface)
            )
        )[0] != 0:
            return ""

        ip = network.find_ip_by_int(interface)
        logger.info("VM: %s acquired IP address: %s", vm, ip)
        return ip

    return ""


def create_ifcfg_on_vm(vm, action="create"):
    """
    Create interface configuration file which prevents OVN DHCP from changing
    the routing table of a VM

    Args:
        vm (str): VM name
        action (str): "create" to create file, or "delete" to delete file

    Returns:
        bool: True if file created or deleted successfully, False otherwise

    """
    ifcfg_prevent_default_route = {
        "DEFROUTE": "no"
    }

    interface = net_helper.get_non_mgmt_nic_name(vm=vm)
    if not interface:
        return False
    interface = interface[0]

    vm_resource = ovn_conf.OVN_VMS_RESOURCES[vm]
    network = vm_resource.get_network()
    filename = ovn_conf.OVN_CMD_NET_SCRIPT.format(eth=interface)

    logger.info(
        "Creating configuration file: %s to prevent default route"
        " changes on VM: %s", filename, vm
    )
    network.create_ifcfg_file(interface, ifcfg_prevent_default_route)

    return vm_resource.fs.exists(filename)


def check_for_ovn_objects():
    """
    Check for existing OVN objects on the provider database, in case found
    write error log

    Returns:
        bool: True if OVN objects exists on provider, False otherwise

    """
    ret_net = ovn_conf.OVN_PROVIDER.get_networks_list_from_provider_server()
    if ret_net:
        logger.error(
            "There are exiting networks objects in the provider: %s", ret_net
        )

    ret_sub = ovn_conf.OVN_PROVIDER.get_subnets_list()
    if ret_sub:
        logger.error(
            "There are exiting subnets objects in the provider: %s", ret_sub
        )

    return True if ret_net or ret_sub else False


def check_ping(vm, dst_ip, max_loss=0, count=ovn_conf.OVN_PING_COUNT):
    """
    Send ICMP ping between VM and destination IP address, packets will be sent
    from the non-mgmt interface

    Args:
        vm (str): VM name as source to send the ping
        dst_ip (str): Destination IP address
        max_loss (int): Maximum number of packets loss to tolerate in a
            successful ping
        count (int): Number of packets to send

    Returns:
        bool: True if ping was successful, False otherwise

    """
    interface = net_helper.get_non_mgmt_nic_name(vm=vm)
    if not interface:
        return False
    interface = interface[0]

    ret = ovn_conf.OVN_VMS_RESOURCES[vm].run_command(
        command=shlex.split(
            ovn_conf.OVN_CMD_PING.format(
                ip=dst_ip, count=count, size=ovn_conf.OVN_PING_SIZE,
                eth=interface
            )
        )
    )

    match = re.findall(ovn_conf.OVN_PING_PACKETS_RECEIVED_REGEX, ret[1])

    if max_loss > 0 and match:
        logger.info(
            "Ping migration test: packets sent: %s received: %s [max defined "
            "packet loss: %s]",
            count, int(match[0]), max_loss
        )
        return int(match[0]) >= max_loss

    return ret[0] == 0


def check_dns_resolver(vm, ip_address):
    """
    Check if IP address is configured as a DNS resolver in a VM

    Args:
        vm (str): VM name
        ip_address (str): DNS IP address

    Returns:
        bool: True if given IP address is configured as resolver on VM,
            False if not, or error has occurred

    """
    resolv_content = ""

    logger.info("Looking for nameserver: %s in %s", ip_address, vm)
    fs = ovn_conf.OVN_VMS_RESOURCES[vm].fs
    if fs.exists(ovn_conf.OVN_CMD_RESOLV_CONFIG):
        resolv_content = fs.read_file(ovn_conf.OVN_CMD_RESOLV_CONFIG)
    else:
        logger.error("Unable to locate: %s", ovn_conf.OVN_CMD_RESOLV_CONFIG)

    return ip_address in resolv_content


def check_hot_unplug_and_plug(vm, vnic, network=None, vnic_profile=None):
    """
    Check hot-plug and hot-unplug vNIC on VM, and change network and/or vNIC
    profile values

    Args:
        vm (str): VM name
        vnic (str): vNIC name (as represented in the OS)
        network (str): Network name
        vnic_profile (str): vNIC profile

    Returns:
        bool: True if test was successful, False otherwise

    """
    for state, action in zip(
        ("False", "True"), ("Hot-unplugging", "Hot-plugging")
    ):
        update_nic_args = {
            "positive": True,
            "vm": vm,
            "nic": vnic,
            "plugged": state,
        }

        testflow.step("%s vNIC: %s on VM: %s", action, ovn_conf.OVN_VNIC, vm)

        if network and state == "True":
            testflow.step("Changing vNIC: %s network to: %s", vnic, network)
            update_nic_args["network"] = network

        if vnic_profile and state == "True":
            testflow.step(
                "Changing vNIC: %s vNIC profile to: %s", vnic, vnic_profile
            )
            update_nic_args["vnic_profile"] = vnic_profile

        if not ll_vms.updateNic(**update_nic_args):
            return False

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
    ping_job = jobs.Job(target=check_ping, args=(), kwargs=ping_kwargs)
    migrate_job = jobs.Job(
        target=hl_vms.migrate_vms, args=(), kwargs=migration_kwargs
    )
    job_set = jobs.JobsSet()
    job_set.addJobs(jobs=[ping_job, migrate_job])
    job_set.start()
    job_set.join(timeout=ovn_conf.OVN_MIGRATION_TIMEOUT)

    logger.info(
        "Migration job result: %s ping job result: %s", migrate_job.result,
        ping_job.result
    )

    return migrate_job.result and ping_job.result


def wait_for_up_state_and_reactivate(host):
    """
    Wait for host up state and reactivate host

    Args:
        host (str): Host name

    Returns:
        bool: True if result was successful, False otherwise

    """
    wait = ll_hosts.wait_for_hosts_states(positive=True, names=host)
    deactivate = hl_hosts.deactivate_host_if_up(host=host)
    activate = hl_hosts.activate_host_if_not_up(host=host)
    return wait and deactivate and activate


def service_handler(host, service, action="stop"):
    """
    System service handler

    Args:
        host (Host): Host object
        service (str): Service name
        action (str): Action to take on service, can be "stop", "start" or
            "state" to get service state

    Returns:

    """
    if action == "start":
        return host.service(name=service).start()
    if action == "stop":
        try:
            return host.service(name=service).stop()
        except Exception:
            return True
    if action == "state":
        return host.run_command(
            shlex.split(ovn_conf.OVN_CMD_SERVICE_STATUS.format(name=service))
        )[0] == 0


def rpm_install(host, rpm_name):
    """
    Installs RPM package

    Args:
        host (Host): Host object
        rpm_name (str): RPM package name

    Returns:
        True if install was successful, False otherwise

    """
    if host.package_manager.exist(rpm_name):
        return host.package_manager.update(packages=[rpm_name])

    host.package_manager.install(rpm_name)
    return host.package_manager.exist(rpm_name)
