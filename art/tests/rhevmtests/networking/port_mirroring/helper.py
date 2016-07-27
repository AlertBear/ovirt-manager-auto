#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by port_mirroring_test
"""

import logging

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as pm_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_help
from rhevmtests import helpers

logger = logging.getLogger("Port_Mirroring_Helper")


def set_port_mirroring(
    vm, nic, network, disable_mirroring=False, teardown=False
):
    """
    Set port mirroring on a machine by shutting it down and bringing it back up
    to avoid unplugging NIC's and changing their order in the machine (eth1,
    eth2, etc)

    Args:
        vm (str): Name of the VM.
        nic (str): Nic to enable/disable port mirroring on.
        network (str): The name of the network the nic is connected to.
        disable_mirroring (bool): Indicate if we want to enable or disable port
            mirroring (leave False to enable).
        teardown (boo): True if calling from teardown.

    Returns:
        bool: True if set port mirroring on a machine was Succeeded,
            False otherwise.
    """
    unplug_error = "Failed to unplug %s on %s"
    update_error = "Failed to update %s to %s profile."
    plug_error = "Failed to plug %s on %s"
    vnic_profile = network + (
        "" if disable_mirroring else "_vNIC_PORT_MIRRORING"
    )
    port_mirror_text = "Disabling" if disable_mirroring else "Enabling"
    logger_info = (
        "%s port mirroring on: VM: %s, NIC: %s,  vNIC profile: %s" %
        (port_mirror_text, vm, nic, vnic_profile)
    )
    logger.info(logger_info)
    if not ll_vms.updateNic(positive=True, vm=vm, nic=nic, plugged=False):
        if teardown:
            logger.error(unplug_error, nic, vm)
        else:
            logger.error(unplug_error, nic, vm)
            return False

    if not ll_vms.updateNic(
        positive=True, vm=vm, nic=nic, network=network,
        vnic_profile=vnic_profile
    ):
        if teardown:
            logger.error(update_error, nic, vnic_profile)
        else:
            logger.error(update_error, nic, vnic_profile)
            return False

    if not ll_vms.updateNic(positive=True, vm=vm, nic=nic, plugged=True):
        if teardown:
            logger.error(plug_error, nic, vm)
        else:
            logger.error(plug_error, nic, vm)
            return False

    return True


def return_vms_to_original_host():
    """
    Returns all the VMs to original host they were on
    """
    logger.info(
        "Return (migrate) all vms to %s", conf.HOST_0_NAME
    )
    vms = filter(
        lambda x: ll_vms.getVmHost(x)[1]["vmHoster"] == conf.HOST_1_NAME,
        conf.VM_NAME[:pm_conf.NUM_VMS]
    )
    hl_vms.migrate_vms(
        vms_list=vms, src_host=conf.HOST_1_NAME,
        vm_os_type="rhel", vm_user=conf.VMS_LINUX_USER,
        vm_password=conf.VMS_LINUX_PW, dst_host=conf.HOST_0_NAME
    )


def check_traffic_during_icmp(
    src_ip, dst_ip, src_vm, listen_vm=conf.VM_0, nic=pm_conf.PM_NIC_NAME[1][1],
    positive=True
):
    """
    Check traffic while running icmp

    Args:
        src_ip (str): Source IP for ICMP traffic.
        dst_ip (str): Destination IP for ICMP traffic.
        src_vm (str): MGMT of VM from where the ICMP starts.
        listen_vm (str): VM that performs port mirroring.
        nic (str): NIC on VM to perform port mirroring.
        positive (bool): True if traffic is expected, False otherwise.

    Returns:
        bool: True if traffic was received while sending ICMP, False if traffic
            wasn't received.
    """
    listen_inter = pm_conf.VMS_NETWORKS_PARAMS[listen_vm][nic][0]
    exp_info = "Traffic is not received" if positive else "Traffic is received"
    logger.info(
        "Check the ICMP traffic on mirroring VM %s NIC %s", listen_vm, nic
    )

    listen_vm_obj = helpers.get_vm_resource(vm=listen_vm)
    src_vm_obj = helpers.get_host_resource(
        ip=src_vm, password=conf.VMS_LINUX_PW
    )
    tcpdump_kwargs = {
        "host_obj": listen_vm_obj,
        "nic": listen_inter,
        "src": src_ip,
        "dst": dst_ip,
        "numPackets": 5,
        "timeout": str(conf.TIMEOUT)
    }

    icmp_kwargs = {
        "dst": dst_ip,
        "count": "10",
    }

    res = net_help.check_traffic_during_func_operation(
        func=src_vm_obj.network.send_icmp, func_kwargs=icmp_kwargs,
        tcpdump_kwargs=tcpdump_kwargs
    )

    if not positive == res:
        logger.error(exp_info)

    return True


def create_vnic_profiles_with_pm():
    """
    Creates vNIC profiles with port mirroring for MGMT and net_1

    Raises:
        AssertionError: If failed to create vNIC profiles with port mirroring
    """
    for vnic_profile, network in zip(
        pm_conf.PM_VNIC_PROFILE[:2], [conf.MGMT_BRIDGE, pm_conf.PM_NETWORK[0]]
    ):
        assert ll_networks.add_vnic_profile(
            positive=True, name=vnic_profile, cluster=conf.CL_0,
            network=network, port_mirroring=True
        )


def configure_ip_all_vms():
    """
    Configure static IP on VM interfaces

     Raises:
        AssertionError: If failed to configure IPs for each VM.
    """
    logger.info("Configure IPs for each VM")
    for vm in conf.VM_NAME[:pm_conf.NUM_VMS]:
        logger.info("Getting management network IP for %s.", vm)
        local_mgmt_ip = hl_vms.get_vm_ip(vm_name=vm, start_vm=False)
        logger.info("%s: %s", vm, local_mgmt_ip)
        pm_conf.MGMT_IPS.append(local_mgmt_ip)
        vm_resource = helpers.get_vm_resource(vm=vm)
        interfaces = net_help.get_vm_interfaces_list(
            vm_resource=vm_resource, exclude_nics=[conf.VM_NICS[0]]
        )
        assert interfaces, "Failed to get interfaces from %s" % vm

        for inter in interfaces:
            mac_cmd = ["cat", "/sys/class/net/%s/address" % inter]
            inter_mac = vm_resource.run_command(command=mac_cmd)[1].strip()
            logger.info("Configure IPs on %s for %s", vm, inter)
            params = {
                "IPADDR": pm_conf.VMS_MACS_AND_IPS[vm][inter_mac][1],
                "BOOTPROTO": "static",
                "NETMASK": "255.255.0.0"
            }
            vm_resource.network.create_ifcfg_file(
                nic=inter, params=params, ifcfg_path=net_help.IFCFG_PATH
            )
            assert not vm_resource.run_command(command=["ifup", inter])[0]


def add_nics_to_vms():
    """
    Add 2 additional vNICs to VMs (besides NIC with MGMT)

    Raises:
        AssertionError: If NICs weren't added successfully.
    """
    vms_list = conf.VM_NAME[:pm_conf.NUM_VMS]
    for vm_name in vms_list:
        pm_conf.VMS_MACS_AND_IPS[vm_name] = dict()
        for nic, net in zip(
            pm_conf.PM_NIC_NAME[1][1:3], pm_conf.PM_NETWORK[:2]
        ):
            # Add vNIC with PM to first VM on second NIC
            if vm_name == conf.VM_0 and nic == pm_conf.PM_NIC_NAME[1][1]:
                vnic_profile = pm_conf.PM_VNIC_PROFILE[1]
            else:
                #  Add vNIC without PM
                vnic_profile = net

            assert ll_vms.addNic(
                positive=True, vm=vm_name, name=nic, network=net,
                nterface=conf.NIC_TYPE_VIRTIO, vnic_profile=vnic_profile
            )


def prepare_ips_for_vms():
    """
    Prepare IPs for VMs
    """
    vms_list = conf.VM_NAME[:pm_conf.NUM_VMS]
    for vm_name in vms_list:
        pm_conf.VMS_MACS_AND_IPS[vm_name] = dict()
        for nic in conf.NIC_NAME[:1] + pm_conf.PM_NIC_NAME[1][1:3]:
            vnic_mac = ll_vms.get_vm_nic_mac_address(
                vm=vm_name, nic=nic
            )
            if nic == conf.NIC_NAME[0]:
                nic_ip = hl_vms.get_vm_ip(vm_name=vm_name, start_vm=False)
            else:
                nic_ip = (
                    pm_conf.NET1_IPS[vms_list.index(vm_name)] if
                    nic == pm_conf.PM_NIC_NAME[1][1]else
                    pm_conf.NET2_IPS[vms_list.index(vm_name)]
                )
            nic_and_ip = (nic, nic_ip)
            pm_conf.VMS_MACS_AND_IPS[vm_name][vnic_mac] = nic_and_ip


def vms_network_params():
    """
    Get all VMs network params
    """
    for vm in conf.VM_NAME[:pm_conf.NUM_VMS]:
        pm_conf.VMS_NETWORKS_PARAMS[vm] = dict()
        vm_resource = helpers.get_vm_resource(vm=vm)
        vm_nics = ll_vms.get_vm_nics_obj(vm_name=vm)
        for nic in vm_nics:
            mac = nic.mac.address
            ip = pm_conf.VMS_MACS_AND_IPS[vm][mac][1]
            nic_name = pm_conf.VMS_MACS_AND_IPS[vm][mac][0]
            inter = vm_resource.network.find_int_by_ip(ip=ip)
            pm_conf.VMS_NETWORKS_PARAMS[vm][nic_name] = (inter, ip)
