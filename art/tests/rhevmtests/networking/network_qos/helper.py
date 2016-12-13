#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for network QoS job
"""

import logging
import xml.etree.ElementTree

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as qos_conf
import rhevmtests.networking.config as conf

logger = logging.getLogger("Network_VNIC_QoS_Helper")


def get_vm_xml(host_obj, vm_name):
    """
    Get xml from the provided vm on specific host
    :param host_obj: resource.VDS host object
    :type host_obj: resource.VDS
    :param vm_name: vm name to check the id
    :type vm_name: str
    :return: etree xml
    :rtype: ElementTree
    """
    cmd = ["virsh", "-r", "dumpxml", vm_name]
    host_exec = host_obj.executor()
    rc, out, error = host_exec.run_cmd(cmd)
    if rc:
        logger.error("Failed to run %s. ERR: %s", cmd, error)
        return None
    return xml.etree.ElementTree.fromstring(out)


class QosCalculator(object):
    """
    Class that converts the QoS values given in Mb in rhevm to KB that is
    represented in libvirt and then compares the values for inbound and
    outbound values of both
    """
    def __init__(self, inbound_dict, outbound_dict):
        self.inbound_dict = inbound_dict.copy()
        self.outbound_dict = outbound_dict.copy()
        self.update_qos_for_libvirt()

    def _calculate_average(self):
        """
        Converts the average provided in Mbps by user to KiB
        """
        if self.inbound_dict:
            self.inbound_dict["average"] = str(
                self.inbound_dict["average"] *
                qos_conf.M_K_CONVERTER / qos_conf.BITS_BYTES
            )
        if self.outbound_dict:
            self.outbound_dict["average"] = str(
                self.outbound_dict["average"] *
                qos_conf.M_K_CONVERTER / qos_conf.BITS_BYTES
            )

    def _calculate_peak(self):
        """
        Converts the peak provided in Mbps by user to KiB
        """
        if self.inbound_dict:
            self.inbound_dict["peak"] = str(
                self.inbound_dict["peak"] *
                qos_conf.M_K_CONVERTER / qos_conf.BITS_BYTES
            )
        if self.outbound_dict:
            self.outbound_dict["peak"] = str(
                self.outbound_dict["peak"] *
                qos_conf.M_K_CONVERTER / qos_conf.BITS_BYTES
            )

    def _calculate_burst(self):
        """
        Converts the burst provided in MiB by user to KiB
        """
        if self.inbound_dict:
            self.inbound_dict["burst"] = str(
                self.inbound_dict["burst"] * qos_conf.M_K_CONVERTER
            )
        if self.outbound_dict:
            self.outbound_dict["burst"] = str(
                self.outbound_dict["burst"] * qos_conf.M_K_CONVERTER
            )

    def update_qos_for_libvirt(self):
        """
        Converts the values provided in Mb to KB as are the values on libvirt
        """
        self._calculate_average()
        self._calculate_peak()
        self._calculate_burst()

    def get_inbound_dict(self):
        """
        Gets the dictionary for inbound bandwidth
        """
        return self.inbound_dict

    def get_outbound_dict(self):
        """
        Gets the dictionary for outbound bandwidth
        """
        return self.outbound_dict

    def compare_dicts(self, libvirt_inbound_dict, libvirt_outbound_dict):
        """
        Compares dictionaries provided by user to the dictionary from libvirt
        :param libvirt_inbound_dict: dict for inbound bw on libvirt
        :type libvirt_inbound_dict: dict
        :param libvirt_outbound_dict: dict for outbound bw on libvirt
        :type libvirt_outbound_dict: dict
        :return: True/False
        :rtype: bool
        """
        if cmp(self.inbound_dict, libvirt_inbound_dict) or cmp(
                self.outbound_dict, libvirt_outbound_dict):
            return False
        return True


def build_dict(inbound_dict, outbound_dict, vm, nic):
    """
    Builds dictionary of MAC:QosCalculator values
    :param inbound_dict: dict for inbound bw
    :type inbound_dict: dict
    :param outbound_dict: dict for outbound bw
    :type outbound_dict: dict
    :param vm: vm to find VNIC on
    :type vm: str
    :param nic: nic to find MAC on
    :type nic: str
    :return: dictionary of MAC: QosCalculator values
    :rtype: dict
    """
    qos_obj = QosCalculator(inbound_dict, outbound_dict)
    rc, mac_dict = ll_vms.getVmMacAddress(True, vm=vm, nic=nic)
    if not rc:
        return {}
    mac = mac_dict["macAddress"]
    return {mac: qos_obj}


def get_libvirt_bw(interface):
    """
    Gets bandwidth from libvirt xml output
    :param interface: etree element object
    :type interface: ElementTree
    :return: True/False
    :rtype: bool
    """
    try:
        virsh_qos_in_dict = interface.find(
            "bandwidth").find("inbound").attrib
    except AttributeError:
        virsh_qos_in_dict = {}
    try:
        virsh_qos_out_dict = interface.find(
            "bandwidth").find("outbound").attrib
    except AttributeError:
        virsh_qos_out_dict = {}
    return virsh_qos_in_dict, virsh_qos_out_dict


def compare_qos(vm_name, **kwargs):
    """
    Compares QoS of provided bw and libvirt bw

    Args:
        vm_name (str): vm name to check the id

    Returns:
        bool: True if QoS is match expected Qos , False otherwise
    """
    host = ll_vms.get_vm_host(vm_name=vm_name)
    host_obj = conf.VDS_HOSTS[conf.HOSTS.index(host)]
    xml_out = get_vm_xml(host_obj, vm_name)
    interface_list = xml_out.find("devices").findall("interface")
    for interface in interface_list:
        interface_mac = interface.find("mac").get("address")
        if interface_mac in kwargs:
            qos_calc = kwargs.get(interface_mac)
            virsh_qos_in_dict, virsh_qos_out_dict = get_libvirt_bw(interface)
            if not qos_calc.compare_dicts(
                virsh_qos_in_dict, virsh_qos_out_dict
            ):
                return False
    return True


def add_qos_profile_to_nic(qos_name, vnic_profile_name, nic=conf.VM_NIC_1):
    """
    Creates VNIC profile for mgmt network
    Updates the VNIC profile with specific QoS
    Add VNIC profile to VM NIC

    Args:
        qos_name (str): name of qos to be updated on VNIC profile
        vnic_profile_name (str): vnic profile to update the NIC with
        nic (str): nic to update the vnic profile on

    Returns:
        bool: True/False
    """
    if not ll_networks.add_vnic_profile(
        positive=True, name=vnic_profile_name, data_center=conf.DC_0,
        network=conf.MGMT_BRIDGE
    ):
        return False

    if not ll_networks.update_qos_on_vnic_profile(
        datacenter=conf.DC_0, qos_name=qos_name,
        vnic_profile_name=vnic_profile_name,
        network_name=conf.MGMT_BRIDGE
    ):
        return False

    if not ll_vms.addNic(
        positive=True, vm=conf.VM_0, name=nic, network=conf.MGMT_BRIDGE,
        vnic_profile=vnic_profile_name
    ):
        return False

    return True
