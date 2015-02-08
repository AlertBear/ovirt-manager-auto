#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by port_mirroring_test
"""
import logging
from art.rhevm_api.tests_lib.high_level.networks import TrafficMonitor
from art.rhevm_api.utils.test_utils import sendICMP, setPersistentNetwork
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level import vms as hl_vm
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.vms import (
    updateNic, migrateVm, getVmHost, waitForIP, stopVm
)
logger = logging.getLogger("Port_Mirroring_Helper")


def send_and_capture_traffic(
        srcVM, srcIP, dstIP, listenVM=config.VM_NAME[0], nic=config.VM_NICS[1],
        expectTraffic=True, dupCheck=True
):
    """
    A function that sends ICMP traffic from 'srcIP' to 'dstIP' while capturing
    traffic on 'listeningVM' to check if mirroring is happening.
    :param srcVM: mgmt network IP of the VM to send ping from
    :type srcVM: str
    :param srcIP: IP to send ping form
    :type srcIP: str
    :param dstIP: IP to send ping to
    :type dstIP: str
    :param listenVM: name of the VM that will listen to the traffic
    :type listenVM: str
    :param nic: NIC to listen to traffic on
    :type nic: str
    :param expectTraffic: boolean to indicate if we expect to see the ping
           traffic on the listening machine or not.
    :type expectTraffic: bool
    :param dupCheck: Check if packets are duplicated
    :type dupCheck: bool
    :return: If expectTraffic is True: True if the ping traffic was sent and
                captured on the listening machine, False otherwise.
                If expectTraffic is False: True if the ping traffic wasn't
                captured, False otherwise.
    :rtype: bool or Exception
    """
    logger_info = (
        "Send and capture traffic from {0} to {1}. Listen VM is {2}. "
        "Expected traffic is {3}".format(srcIP, dstIP, listenVM, expectTraffic)
    )

    expected_text = (
        "Failed to send/capture traffic" if expectTraffic else "Found traffic"
    )

    NetworkException_text = (
        "{0} from {1} to {2}. Listen VM is {3}.".format(
            expected_text, srcIP, dstIP, listenVM)
    )

    logger.info(logger_info)
    listen_vm_index = config.VM_NAME.index(listenVM)
    with TrafficMonitor(expectedRes=expectTraffic,
                        machine=config.MGMT_IPS[listen_vm_index],
                        user=config.VMS_LINUX_USER,
                        password=config.VMS_LINUX_PW,
                        nic=nic, src=srcIP, dst=dstIP, dupCheck=dupCheck,
                        protocol="icmp", numPackets=3, ) as monitor:
            monitor.addTask(sendICMP, host=srcVM, user=config.VMS_LINUX_USER,
                            password=config.VMS_LINUX_PW, ip=dstIP)
    if not monitor.getResult():
        raise NetworkException(NetworkException_text)


def set_port_mirroring(vm, nic, network, disableMirroring=False):
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
    :param disableMirroring: boolean to indicate if we want to enable or
           disable port mirroring (leave False to enable)
    :type disableMirroring: bool
    """
    vnic_profile = network + ("" if disableMirroring else "_PM")
    port_mirror_text = "Disabling" if disableMirroring else "Enabling"
    logger_info = (
        "%s port mirroring on: VM: %s, NIC: %s,  vNIC profile: %s",
        port_mirror_text, vm, nic, vnic_profile
    )
    logger.info(logger_info)
    if not updateNic(True, vm, nic, plugged=False):
        logger.error("Failed to unplug %s on %s", nic, vm)

    if not updateNic(
            True, vm, nic, network=network, vnic_profile=vnic_profile
    ):
        logger.error("Failed to update %s to %s profile.", nic, vnic_profile)

    if not updateNic(True, vm, nic, plugged=True):
        logger.error("Failed to plug %s on %s", nic, vm)


def return_vms_to_original_host():
    """
    Returns all the VMs to original host they were on
    """
    for vm in config.VM_NAME[:config.NUM_VMS]:
        if getVmHost(vm)[1]["vmHoster"] == config.HOSTS[1]:
            if not migrateVm(True, vm, config.HOSTS[0]):
                logger.error("Failed to migrate vm %s", vm)


def ge_seal_vm(vm):
    """
    Start VM, seal the VM and restart the VM
    :param vm: VM IP
    :type vm: str
    :return: None
    """
    logger.info("Sealing VM: %s", vm)
    if not hl_vm.start_vm_on_specific_host(vm=vm, host=config.HOSTS[0]):
        raise NetworkException("Failed to start %s." % config.VM_NAME[0])

    logger.info("Waiting for IP from %s", vm)
    rc, out = waitForIP(vm=vm, timeout=180, sleep=10)
    if not rc:
        raise NetworkException("Failed to get VM IP on mgmt network")

    ip = out["ip"]
    logger.info("Running setPersistentNetwork on %s", vm)
    if not setPersistentNetwork(ip, config.VMS_LINUX_PW):
        raise NetworkException("Failed to seal %s" % vm)

    logger.info("Stopping %s", vm)
    if not stopVm(positive=True, vm=vm):
        raise NetworkException("Failed to stop %s" % vm)

    logger.info("Starting %s", vm)
    if not hl_vm.start_vm_on_specific_host(vm=vm, host=config.HOSTS[0]):
        raise NetworkException("Failed to start %s." % config.VM_NAME[0])

    logger.info("Waiting for IP from %s", vm)
    rc, out = waitForIP(vm=vm, timeout=360, sleep=10)
    if not rc:
        raise NetworkException("Failed to get IP after %s is UP" % vm)
