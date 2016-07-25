#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by port_mirroring_test
"""

import logging

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import rhevmtests.networking.helper as net_help
from rhevmtests import helpers

logger = logging.getLogger("Port_Mirroring_Helper")

VLAN_0 = "1000" if conf.PPC_ARCH else conf.VLAN_ID[0]
VLAN_1 = "1500" if conf.PPC_ARCH else conf.VLAN_ID[1]


def set_port_mirroring(
    vm, nic, network, disable_mirroring=False, teardown=False
):
    """
    Set port mirroring on a machine by shutting it down and bringing it back up
    to avoid unplugging NIC's and changing their order in the machine (eth1,
    eth2, etc)
    :param vm: name of the VM
    :type vm: str
    :param nic: nic to enable/disable port mirroring on
    :type nic: str
    :param network: the name of the network the nic is connected to
    :type network: str
    :param disable_mirroring: boolean to indicate if we want to enable or
           disable port mirroring (leave False to enable)
    :type disable_mirroring: bool
    :param teardown: True if calling from teardown
    :type teardown: bool
    :raise: conf.NET_EXCEPTION
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
    if not ll_vms.updateNic(True, vm, nic, plugged=False):
        if teardown:
            logger.error(unplug_error, nic, vm)
        else:
            raise conf.NET_EXCEPTION(unplug_error % (nic, vm))

    if not ll_vms.updateNic(
            True, vm, nic, network=network, vnic_profile=vnic_profile
    ):
        if teardown:
            logger.error(update_error, nic, vnic_profile)
        else:
            raise conf.NET_EXCEPTION(
                update_error % (nic, vnic_profile)
            )
    if not ll_vms.updateNic(True, vm, nic, plugged=True):
        if teardown:
            logger.error(plug_error, nic, vm)
        else:
            raise conf.NET_EXCEPTION(plug_error % (nic, vm))


def return_vms_to_original_host():
    """
    Returns all the VMs to original host they were on
    """
    vms = filter(
        lambda x: ll_vms.getVmHost(x)[1]["vmHoster"] == conf.HOSTS[1],
        conf.VM_NAME[:conf.NUM_VMS]
    )
    hl_vms.migrate_vms(
        vms_list=vms, src_host=conf.HOSTS[1],
        vm_os_type="rhel", vm_user=conf.VMS_LINUX_USER,
        vm_password=conf.VMS_LINUX_PW, dst_host=conf.HOSTS[0]
    )


def check_traffic_during_icmp(
    src_ip, dst_ip, src_vm, listen_vm=conf.VM_0, nic=conf.NIC_NAME[1],
    positive=True
):
    """
    Check traffic while running icmp

    :param src_ip: Source IP for ICMP traffic
    :type src_ip: str
    :param dst_ip: Destination IP for ICMP traffic
    :type dst_ip: str
    :param src_vm: MGMT of VM from where the ICMP starts
    :type src_vm: str
    :param listen_vm: VM that performs port mirroring
    :type listen_vm: str
    :param nic: NIC on VM to perform port mirroring
    :type nic: int
    :param positive: True if traffic is expected, False otherwise
    :type positive: bool
    :return: True if traffic was received while sending ICMP
    :rtype: bool
    """
    listen_inter = conf.VMS_NETWORKS_PARAMS[listen_vm][nic][0]
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
        raise conf.NET_EXCEPTION(exp_info)


def create_vnic_profiles_with_pm():
    """
    Creates vNIC profiles with port mirroring for MGMT and sw162

    :raise: conf.NET_EXCEPTION
    """
    for vnic_profile, network in zip(
        conf.PM_VNIC_PROFILE[:2], [conf.MGMT_BRIDGE, conf.PM_NETWORK[0]]
    ):
        if not ll_networks.add_vnic_profile(
            positive=True, name=vnic_profile, cluster=conf.CL_0,
            network=network, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()


def configure_ip_all_vms():
    """
    Configure static IP on VM interfaces

    :raise: conf.NET_EXCEPTION
    """
    logger.info("Configure IPs for each VM")
    for vm in conf.VM_NAME[:conf.NUM_VMS]:
        logger.info("Getting management network IP for %s.", vm)
        local_mgmt_ip = hl_vms.get_vm_ip(vm_name=vm, start_vm=False)
        logger.info("%s: %s", vm, local_mgmt_ip)
        conf.MGMT_IPS.append(local_mgmt_ip)
        vm_resource = helpers.get_vm_resource(vm=vm)
        interfaces = net_help.get_vm_interfaces_list(
            vm_resource, exclude_nics=[conf.VM_NICS[0]]
        )
        if not interfaces:
            raise conf.NET_EXCEPTION("Failed to get interfaces from %s" % vm)

        for inter in interfaces:
            mac_cmd = ["cat", "/sys/class/net/%s/address" % inter]
            inter_mac = vm_resource.run_command(command=mac_cmd)[1].strip()
            logger.info("Configure IPs on %s for %s", vm, inter)
            params = {
                "IPADDR": conf.VMS_MACS_AND_IPS[vm][inter_mac][1],
                "BOOTPROTO": "static",
                "NETMASK": "255.255.0.0"
            }
            vm_resource.network.create_ifcfg_file(
                nic=inter, params=params, ifcfg_path=net_help.IFCFG_PATH
            )

            if vm_resource.run_command(command=["ifup", inter])[0]:
                raise conf.NET_EXCEPTION()


def add_nics_to_vms():
    """
    Add 2 additional vNICs to VMs (besides NIC with MGMT)

    :raise: conf.NET_EXCEPTION
    """
    vms_list = conf.VM_NAME[:conf.NUM_VMS]
    for vm_name in vms_list:
        conf.VMS_MACS_AND_IPS[vm_name] = dict()
        for nic, net in zip(conf.NIC_NAME[1:3], conf.PM_NETWORK[:2]):
            # Add vNIC with PM to first VM on second NIC
            if vm_name == conf.VM_0 and nic == conf.NIC_NAME[1]:
                vnic_profile = conf.PM_VNIC_PROFILE[1]
            else:
                #  Add vNIC without PM
                vnic_profile = net

            if not ll_vms.addNic(
                positive=True, vm=vm_name, name=nic,
                interface=conf.NIC_TYPE_VIRTIO, network=net,
                vnic_profile=vnic_profile
            ):
                raise conf.NET_EXCEPTION()


def prepare_ips_for_vms():
    """
    Prepare IPs for VMs
    """
    vms_list = conf.VM_NAME[:conf.NUM_VMS]
    for vm_name in vms_list:
        conf.VMS_MACS_AND_IPS[vm_name] = dict()
        for nic in conf.NIC_NAME[:3]:
            vnic_mac = ll_vms.get_vm_nic_mac_address(
                vm=vm_name, nic=nic
            )
            if nic == conf.NIC_NAME[0]:
                nic_ip = hl_vms.get_vm_ip(vm_name=vm_name, start_vm=False)
            else:
                nic_ip = (
                    conf.NET1_IPS[vms_list.index(vm_name)] if
                    nic == conf.NIC_NAME[1]else
                    conf.NET2_IPS[vms_list.index(vm_name)]
                )
            nic_and_ip = (nic, nic_ip)
            conf.VMS_MACS_AND_IPS[vm_name][vnic_mac] = nic_and_ip


def create_networks_pm():
    """
    Creates networks on DC/Cluster/Host for pm feature

    :raise: conf.NET_EXCEPTION
    """
    logger.info(
        "Create %s, %s on %s/%s and attach them to %s",
        conf.PM_NETWORK[0],
        ".".join([conf.BOND[0], conf.PM_NETWORK[1]]),
        conf.DC_0, conf.CL_0, conf.HOSTS[:2]
    )
    network_params = {
        None: {
            "nic": conf.BOND[0],
            "mode": 1,
            "slaves": [2, 3]
        },
        conf.PM_NETWORK[0]: {
            "vlan_id": VLAN_0,
            "nic": 1,
            "required": "false"
        },
        conf.PM_NETWORK[1]: {
            "vlan_id": VLAN_1,
            "nic": conf.BOND[0],
            "required": "false"
        }
    }
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_0, cluster=conf.CL_0,
        host=conf.VDS_HOSTS[:2], network_dict=network_params,
        auto_nics=[0, 1]
    ):
        raise conf.NET_EXCEPTION("Cannot create and attach networks")


def vms_network_params():
    """
    Get all VMs network params
    """
    for vm in conf.VM_NAME[:conf.NUM_VMS]:
        conf.VMS_NETWORKS_PARAMS[vm] = dict()
        vm_resource = helpers.get_vm_resource(vm=vm)
        vm_nics = ll_vms.get_vm_nics_obj(vm_name=vm)
        for nic in vm_nics:
            mac = nic.mac.address
            ip = conf.VMS_MACS_AND_IPS[vm][mac][1]
            nic_name = conf.VMS_MACS_AND_IPS[vm][mac][0]
            inter = vm_resource.network.find_int_by_ip(ip=ip)
            conf.VMS_NETWORKS_PARAMS[vm][nic_name] = (inter, ip)
