#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by port_mirroring_test
"""

import logging
from rhevmtests import helpers
from art.rhevm_api.utils import test_utils
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Port_Mirroring_Helper")


def send_and_capture_traffic(
    src_vm, src_ip, dst_ip, listen_vm=conf.VM_NAME[0], nic=conf.VM_NICS[1],
    expect_traffic=True, dup_check=True
):
    """
    A function that sends ICMP traffic from 'src_ip' to 'dst_ip' while
    capturing
    traffic on 'listeningVM' to check if mirroring is happening.
    :param src_vm: mgmt network IP of the VM to send ping from
    :type src_vm: str
    :param src_ip: IP to send ping form
    :type src_ip: str
    :param dst_ip: IP to send ping to
    :type dst_ip: str
    :param listen_vm: name of the VM that will listen to the traffic
    :type listen_vm: str
    :param nic: NIC to listen to traffic on
    :type nic: str
    :param expect_traffic: boolean to indicate if we expect to see the ping
           traffic on the listening machine or not.
    :type expect_traffic: bool
    :param dup_check: Check if packets are duplicated
    :type dup_check: bool
    :raise: conf.NET_EXCEPTION
    """
    logger_info = (
        "Send and capture traffic from {0} to {1}. Listen VM is {2}. "
        "Expected traffic is {3}".format(
            src_ip, dst_ip, listen_vm, expect_traffic
        )
    )
    expected_text = (
        "Failed to send/capture traffic" if expect_traffic else "Found traffic"
    )

    network_exception_text = (
        "{0} from {1} to {2}. Listen VM is {3}.".format(
            expected_text, src_ip, dst_ip, listen_vm)
    )
    logger.info(logger_info)
    listen_vm_index = conf.VM_NAME.index(listen_vm)
    with hl_networks.TrafficMonitor(
        expectedRes=expect_traffic,
        machine=conf.MGMT_IPS[listen_vm_index],
        user=conf.VMS_LINUX_USER,
        password=conf.VMS_LINUX_PW,
        nic=nic, src=src_ip, dst=dst_ip, dupCheck=dup_check,
        protocol="icmp", numPackets=3
    ) as monitor:
            monitor.addTask(
                test_utils.sendICMP, host=src_vm, user=conf.VMS_LINUX_USER,
                password=conf.VMS_LINUX_PW, ip=dst_ip
            )
    if not monitor.getResult():
        raise conf.NET_EXCEPTION(network_exception_text)


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
    vnic_profile = network + ("" if disable_mirroring else "_PM")
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
    for vm in conf.VM_NAME[:conf.NUM_VMS]:
        if ll_vms.getVmHost(vm)[1]["vmHoster"] == conf.HOSTS[1]:
            if not ll_vms.migrateVm(True, vm, conf.HOSTS[0]):
                logger.error("Failed to migrate vm %s", vm)


def ge_seal_vm(vm):
    """
    Start VM, seal the VM and restart the VM
    :param vm: VM IP
    :type vm: str
    :raise: conf.NET_EXCEPTION
    """
    logger.info("Sealing VM: %s", vm)
    if not net_help.run_vm_once_specific_host(vm=vm, host=conf.HOSTS[0]):
        raise conf.NET_EXCEPTION(
            "Failed to start %s." % conf.VM_NAME[0]
        )
    logger.info("Waiting for IP from %s", vm)
    rc, out = ll_vms.waitForIP(vm=vm, timeout=180, sleep=10)
    if not rc:
        raise conf.NET_EXCEPTION(
            "Failed to get VM IP on mgmt network"
        )
    ip = out["ip"]
    logger.info("Running setPersistentNetwork on %s", vm)
    if not test_utils.setPersistentNetwork(ip, conf.VMS_LINUX_PW):
        raise conf.NET_EXCEPTION("Failed to seal %s" % vm)

    logger.info("Stopping %s", vm)
    if not ll_vms.stopVm(positive=True, vm=vm):
        raise conf.NET_EXCEPTION("Failed to stop %s" % vm)


def check_traffic_during_icmp(
    src_ip, dst_ip, src_vm, listen_vm, nic
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
    :type nic: str
    :return: True if traffic was received while sending ICMP
    :rtype: bool
    """
    listen_vm_obj = net_help.get_vm_resource(listen_vm)
    tcpdump_kwargs = {
        "host_obj": listen_vm_obj,
        "nic": nic,
        "src": src_ip,
        "dst": dst_ip,
        "numPackets": 5,
        "timeout": str(conf.TIMEOUT)
    }

    icmp_kwargs = {
        "host": src_vm,
        "user": conf.VMS_LINUX_USER,
        "password": conf.VMS_LINUX_PW,
        "ip": dst_ip,
        "count": 10,
        "func_path": "art.rhevm_api.utils.test_utils"
    }

    return net_help.check_traffic_during_func_operation(
        func_name="sendICMP", func_kwargs=icmp_kwargs,
        tcpdump_kwargs=tcpdump_kwargs
    )


def check_received_traffic(
    src_ip, dst_ip, src_vm, listen_vm=conf.VM_NAME[0], nic=conf.VM_NICS[1],
    positive=True
):
    """
    Check if ICMP traffic was received or not according to positive and raise
    exception if it's different than positive

    :param src_ip: Source IP for ICMP traffic
    :type src_ip: str
    :param dst_ip: Destination IP for ICMP traffic
    :type dst_ip: str
    :param src_vm: MGMT of VM from where the ICMP starts
    :type src_vm: str
    :param listen_vm: VM that performs port mirroring
    :type listen_vm: str
    :param nic: NIC on VM to perform port mirroring
    :type nic: str
    :param positive: True if traffic is expected, False otherwise
    :type positive: bool
    :raise: conf.NET_EXCEPTION
    """
    exp_info = "Traffic is not received" if positive else "Traffic is received"
    logger.info(
        "Check the ICMP traffic on mirroring VM %s NIC %s", listen_vm, nic
    )
    if not positive == check_traffic_during_icmp(
        src_ip=src_ip, dst_ip=dst_ip, src_vm=src_vm, listen_vm=listen_vm,
        nic=nic
    ):
        raise conf.NET_EXCEPTION(exp_info)


def create_vnic_profiles_with_pm():
    """
    Creates vNIC profiles with port mirroring for MGMT and sw162

    :raise: conf.NET_EXCEPTION
    """
    logger.info(
        "Create vNIC profiles with port mirroring for %s network and %s",
        conf.MGMT_BRIDGE, conf.VLAN_NETWORKS[0]
    )
    for i, network in enumerate((conf.MGMT_BRIDGE, conf.VLAN_NETWORKS[0])):
        if not ll_networks.addVnicProfile(
            positive=True, name=conf.PM_VNIC_PROFILE[i],
            cluster=conf.CLUSTER_NAME[0],
            network=network, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create VNIC profile %s with port mirroring." %
                conf.PM_VNIC_PROFILE[i]
            )


def configure_ip_all_vms():
    """
    Configure static IP on VM interfaces

    :raise: conf.NET_EXCEPTION
    """
    logger.info("Configure IPs for each VM")
    for i, vm in enumerate(conf.VM_NAME[:conf.NUM_VMS]):
        logger.info("Getting MGMT network IP for %s.", vm)
        rc, out = ll_vms.waitForIP(vm=vm, timeout=180, sleep=10)

        if not rc:
            raise conf.NET_EXCEPTION(
                "Failed to get VM IP on MGMT network"
            )
        local_mgmt_ip = out["ip"]
        logger.info(
            "Update the list of MGMT network IPs with %s from %s",
            local_mgmt_ip, vm
        )
        conf.MGMT_IPS.append(local_mgmt_ip)
        vm_resource = helpers.get_host_resource_with_root_user(
            ip=local_mgmt_ip, root_password=conf.VMS_LINUX_PW
        )
        logger.info("Configure IPs on %s for nic1 and nic2", vm)
        for nicIndex, ip in enumerate(
            (conf.NET1_IPS[i], conf.NET2_IPS[i]), start=1
        ):
            params = {
                "IPADDR": ip,
                "BOOTPROTO": "static",
                "NETMASK": "255.255.0.0"
            }
            ifcfg_path = "/etc/sysconfig/network-scripts/"
            vm_resource.network.create_ifcfg_file(
                nic="eth%s" % nicIndex, params=params, ifcfg_path=ifcfg_path
            )
        logger.info("Restarting network service on %s", vm)
        if not vm_resource.service("network").restart():
            raise conf.NET_EXCEPTION(
                "Failed to restart network service on %s" % vm
            )
    logger.info("Stop iptables service on hosts")
    for host in conf.VDS_HOSTS[:2]:
        if not host.service(conf.FIREWALL_SRV).stop():
            raise conf.NET_EXCEPTION("Cannot stop Firewall service")


def add_nics_to_vms():
    """
    Add 2 additional vNICs to VM (besides NIC with MGMT)

    :raise: conf.NET_EXCEPTION
    """
    for vmName in conf.VM_NAME[:conf.NUM_VMS]:
        for i in (0, 1):
            if vmName == conf.VM_NAME[0] and i == 0:
                vnic_profile = conf.PM_VNIC_PROFILE[1]
            else:
                vnic_profile = conf.VLAN_NETWORKS[i]
            logger.info("Adding %s to %s", conf.NIC_NAME[i + 1], vmName)
            if not ll_vms.addNic(
                True, vm=vmName, name=conf.NIC_NAME[i + 1],
                interface=conf.NIC_TYPE_VIRTIO,
                network=conf.VLAN_NETWORKS[i],
                vnic_profile=vnic_profile
            ):
                raise conf.NET_EXCEPTION(
                    "Failed to add nic to %s" % vmName
                )


def create_networks_pm():
    """
    Creates networks on DC/Cluster/Host for pm feature

    :raise: conf.NET_EXCEPTION
    """
    logger.info(
        "Create %s, %s on %s/%s and attach them to %s",
        conf.VLAN_NETWORKS[0],
        ".".join([conf.BOND[0], conf.VLAN_NETWORKS[1]]),
        conf.DC_NAME[0], conf.CLUSTER_NAME[0], conf.HOSTS[:2]
    )
    network_params = {
        None: {
            "nic": conf.BOND[0],
            "mode": 1,
            "slaves": [2, 3]
        },
        conf.VLAN_NETWORKS[0]: {
            "vlan_id": conf.VLAN_ID[0],
            "nic": 1,
            "required": "false"
        },
        conf.VLAN_NETWORKS[1]: {
            "vlan_id": conf.VLAN_ID[1],
            "nic": conf.BOND[0],
            "required": "false"
        }
    }
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_NAME[0], cluster=conf.CLUSTER_NAME[0],
        host=conf.VDS_HOSTS[:2], network_dict=network_params,
        auto_nics=[0, 1]
    ):
        raise conf.NET_EXCEPTION("Cannot create and attach networks")
