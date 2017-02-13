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
    src_ip, dst_ip, src_vm, listen_vm=conf.VM_0, nic=pm_conf.PM_NIC_NAME[0],
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
    listen_inter = pm_conf.VMS_NETWORKS_PARAMS[listen_vm][nic]["interface"]
    exp_info = "Traffic is not received" if positive else "Traffic is received"
    logger.info(
        "Check the ICMP traffic on mirroring VM %s NIC %s", listen_vm, nic
    )

    listen_vm_obj = pm_conf.VMS_NETWORKS_PARAMS[listen_vm]["resource"]
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

    logger.info("Check if %s accept ICMP", dst_ip)
    if not src_vm_obj.network.send_icmp(dst=dst_ip, count="1"):
        logger.error("Failed to send ICMP to %s", dst_ip)
        return False

    res = net_help.check_traffic_during_func_operation(
        func=src_vm_obj.network.send_icmp, func_kwargs=icmp_kwargs,
        tcpdump_kwargs=tcpdump_kwargs
    )

    if not positive == res:
        logger.error(exp_info)
        return False
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


def set_ip_on_vm_interface(vm, main_ip, mac, ip):
    """
    Set IP on VM interface

    Args:
        vm (str): VM name
        main_ip (str): VM main IP
        mac (str): MAC of interface to set the IP on
        ip (str): IP to set on the interface

    Returns:
        str: Interface name that the IP was set on
    """
    vm_resource = pm_conf.VMS_NETWORKS_PARAMS[vm]["resource"]
    main_interface = vm_resource.network.find_int_by_ip(ip=main_ip)
    main_mac = vm_resource.network.find_mac_by_int(interfaces=[main_interface])
    assert main_mac
    if mac == main_mac[0]:
        return main_interface

    interfaces = net_help.get_vm_interfaces_list(vm_resource=vm_resource)
    assert interfaces, "Failed to get interfaces from %s" % vm
    for inter in interfaces:
        mac_cmd = ["cat", "/sys/class/net/%s/address" % inter]
        inter_mac = vm_resource.run_command(command=mac_cmd)
        assert inter_mac
        inter_mac = inter_mac[1].strip()
        if mac == inter_mac:
            logger.info("Configure IP %s on %s for %s", ip, vm, inter)
            params = {
                "IPADDR": ip,
                "BOOTPROTO": "static",
                "NETMASK": "255.255.0.0"
            }
            vm_resource.network.create_ifcfg_file(
                nic=inter, params=params, ifcfg_path=net_help.IFCFG_PATH
            )
            assert not vm_resource.run_command(command=["ifup", inter])[0]
            return inter


def add_nics_to_vms():
    """
    Add 2 additional vNICs to VMs (besides NIC with MGMT)

    Raises:
        AssertionError: If NICs weren't added successfully.
    """
    vms_list = conf.VM_NAME[:pm_conf.NUM_VMS]
    for vm_name in vms_list:
        for nic, net in zip(
            pm_conf.PM_NIC_NAME, pm_conf.PM_NETWORK[:2]
        ):
            # Add vNIC with PM to first VM on second NIC
            if vm_name == conf.VM_0 and nic == pm_conf.PM_NIC_NAME[0]:
                vnic_profile = pm_conf.PM_VNIC_PROFILE[1]
            else:
                # Add vNIC without PM
                vnic_profile = net

            assert ll_vms.addNic(
                positive=True, vm=vm_name, name=nic, network=net,
                interface=conf.NIC_TYPE_VIRTIO, vnic_profile=vnic_profile
            )


def set_vms_network_params():
    """
    Get VMs main IP and VMs resources
    """
    vms_list = conf.VM_NAME[:pm_conf.NUM_VMS]
    for vm in vms_list:
        pm_conf.VMS_NETWORKS_PARAMS[vm] = dict()
        logger.info("Getting management network IP for %s.", vm)
        main_ip = ll_vms.wait_for_vm_ip(vm=vm)
        assert main_ip[0]
        main_ip = main_ip[1].get("ip")
        pm_conf.MGMT_IPS.append(main_ip)
        logger.info("%s: %s", vm, main_ip)
        vm_resource = helpers.get_host_resource(
            ip=main_ip, password=conf.VMS_LINUX_PW
        )
        pm_conf.VMS_NETWORKS_PARAMS[vm]["main_ip"] = main_ip
        pm_conf.VMS_NETWORKS_PARAMS[vm]["resource"] = vm_resource
        vm_nics_objects = ll_vms.get_vm_nics_obj(vm_name=vm)
        assert vm_nics_objects
        for nic in vm_nics_objects:
            nic_name = nic.name
            pm_conf.VMS_NETWORKS_PARAMS[vm][nic_name] = dict()
            mac = ll_vms.get_vm_nic_mac_address(vm=vm, nic=nic_name)
            assert mac
            if nic_name == conf.NIC_NAME[0]:
                nic_ip = pm_conf.VMS_NETWORKS_PARAMS[vm]["main_ip"]
            else:
                nic_ip = (
                    pm_conf.NET1_IPS[vms_list.index(vm)] if
                    nic_name == pm_conf.PM_NIC_NAME[0] else
                    pm_conf.NET2_IPS[vms_list.index(vm)]
                )
            pm_conf.VMS_NETWORKS_PARAMS[vm][nic_name]["ip"] = nic_ip
            pm_conf.VMS_NETWORKS_PARAMS[vm][nic_name]["mac"] = mac
            ip = pm_conf.VMS_NETWORKS_PARAMS[vm][nic_name]["ip"]
            interface = set_ip_on_vm_interface(
                vm=vm, main_ip=main_ip, mac=mac, ip=ip
            )
            pm_conf.VMS_NETWORKS_PARAMS[vm][nic_name]["interface"] = interface
