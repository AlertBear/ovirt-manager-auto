#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Port Mirroring
"""
import logging

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as conf
import helper
import rhevmtests.networking.helper as net_help
from rhevmtests import helpers, networking

logger = logging.getLogger("Port_Mirroring_Fixture")


class PrepareSetup(object):
    """
    Prepare setup for Port Mirroring
    """
    def __init__(self):
        self.vm_list = conf.VM_NAME[:conf.NUM_VMS]

    def create_pm_networks(self):
        """
        Create network with PM
        """
        return helper.create_networks_pm()

    def create_vnic_profiles_with_pm(self):
        """
        Create vNIC profiles with PM
        """
        return helper.create_vnic_profiles_with_pm()

    def set_pm_on_vm_mgmt_net(self):
        """
        Set PM on vNIC with mgmt network on first VM
        """
        return helper.set_port_mirroring(
            vm=conf.VM_0, nic=conf.NIC_NAME[0], network=conf.MGMT_BRIDGE
        )

    def start_vms_on_host(self):
        """
        Start VMs on specific host
        """
        hl_vms.start_vms_on_specific_host(
            vm_list=self.vm_list, max_workers=len(self.vm_list),
            host=conf.HOSTS[0], wait_for_ip=False,
            wait_for_status=conf.ENUMS['vm_state_up']
        )

    def add_nics_to_vms(self):
        """
        Add vNICs to VMs
        """
        return helper.add_nics_to_vms()

    def set_ip_on_vms_vnics(self):
        """
        Set IP on VMs vNICs
        """
        return helper.configure_ip_all_vms()

    def get_vms_interfaces(self):
        """
        Get two first VMs interfaces
        """
        for vm in conf.VM_NAME[:2]:
            vm_resource = helpers.get_vm_resource(vm=vm)
            interfaces = net_help.get_vm_interfaces_list(
                vm_resource=vm_resource
            )
            if not interfaces:
                raise conf.NET_EXCEPTION(
                    "Failed to get interfaces from %s" % vm
                )
            conf.VM_NICS_DICT[vm] = interfaces

    def prepare_ips_for_vms(self):
        """
        Prepare IPs for VMs
        """
        helper.prepare_ips_for_vms()

    def get_vms_networks_params(self):
        """
        Get all VMs network params
        """
        helper.vms_network_params()

    def stop_firewall_service(self):
        """
        Stop firewall service on two first hosts
        """
        for host in conf.VDS_HOSTS[:2]:
            if not host.service(conf.FIREWALL_SRV).stop():
                raise conf.NET_EXCEPTION("Cannot stop Firewall service")

    def remove_ifcfg_files_from_vms(self):
        """
        Remove ifcfg files from VMs
        """
        net_help.remove_ifcfg_files(vms=conf.VM_NAME[:conf.NUM_VMS])

    def stop_vms(self):
        """
        Stop all VMs
        """
        ll_vms.stop_vms_safely(vms_list=conf.VM_NAME)

    def remove_vnics_from_vms(self):
        """
        Remove all vNICs from VMs
        """
        for vm in conf.VM_NAME:
            vm_nics = ll_vms.get_vm_nics_obj(vm_name=vm)
            for nic in vm_nics:
                if nic.name == conf.NIC_NAME[0]:
                    ll_vms.updateNic(
                        positive=True, vm=vm, nic=conf.NIC_NAME[0],
                        network=conf.MGMT_BRIDGE, vnic_profile=conf.MGMT_BRIDGE
                    )
                else:
                    ll_vms.removeNic(positive=True, vm=vm, nic=nic.name)

    def remove_vnic_profiles_from_setup(self):
        """
        Remove all vNIC profiles from setup
        """
        networking.remove_unneeded_vnic_profiles()

    def remove_all_networks_from_setup(self):
        """
        Remove all networks from setup
        """
        hl_networks.remove_net_from_setup(
            host=conf.HOSTS[:2], data_center=conf.DC_0, all_net=True
        )


@pytest.fixture(scope="module")
def port_mirroring_prepare_setup(request):
    """
    Setup and teardown for Port Mirroring
    """
    ps = PrepareSetup()

    @networking.ignore_exception
    def fin5():
        """
        Finalizer for remove networks
        """
        ps.remove_all_networks_from_setup()
    request.addfinalizer(fin5)

    @networking.ignore_exception
    def fin4():
        """
        Finalizer for remove vNIC profiles
        """
        ps.remove_vnic_profiles_from_setup()
    request.addfinalizer(fin4)

    @networking.ignore_exception
    def fin3():
        """
        Finalizer for remove vNICs from VMs
        """
        networking.remove_unneeded_vms_nics()
    request.addfinalizer(fin3)

    @networking.ignore_exception
    def fin2():
        """
        Finalizer for stop VMs
        """
        ps.stop_vms()
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Finalizer for remove ifcfg files from VMs
        """
        ps.remove_ifcfg_files_from_vms()
    request.addfinalizer(fin1)

    networking.network_cleanup()
    ps.create_pm_networks()
    ps.create_vnic_profiles_with_pm()
    ps.set_pm_on_vm_mgmt_net()
    ps.start_vms_on_host()
    ps.add_nics_to_vms()
    ps.prepare_ips_for_vms()
    ps.set_ip_on_vms_vnics()
    ps.get_vms_interfaces()
    ps.get_vms_networks_params()
    ps.stop_firewall_service()


@pytest.fixture(scope="class")
def case01_fixture(request, port_mirroring_prepare_setup):
    """
    Fixture for case01
    """
    def fin():
        """
        Migrate all VMs back to original host
        """
        logger.info("Return (migrate) all vms to %s", conf.HOSTS[0])
        helper.return_vms_to_original_host()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case02_fixture(request, port_mirroring_prepare_setup):
    """
    Fixture for case02
    """
    def fin():
        """
        Disable PM for non first VM
        """
        for vm_name in conf.VM_NAME[2:4]:
            helper.set_port_mirroring(
                vm=vm_name, nic=conf.NIC_NAME[1],
                network=conf.VLAN_NETWORKS[0], disable_mirroring=True,
                teardown=True
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case04_fixture(request, port_mirroring_prepare_setup):
    """
    Fixture for case04
    """
    helper.set_port_mirroring(
        vm=conf.VM_NAME[1], nic=conf.NIC_NAME[1], network=conf.VLAN_NETWORKS[0]
    )

    def fin():
        """
        Disable port mirroring on VM NIC
        """
        vm_nic_vnic_profile = ll_vms.get_vm_nic_vnic_profile(
            vm=conf.VM_NAME[1], nic=conf.NIC_NAME[1]
        )
        vnic_profile_name = ll_general.get_object_name_by_id(
            ll_networks.VNIC_PROFILE_API, vm_nic_vnic_profile.id
        )
        if filter(
            lambda x: x.name == vnic_profile_name and x.port_mirroring,
            ll_networks.get_vnic_profile_objects()
        ):
            helper.set_port_mirroring(
                vm=conf.VM_NAME[1], nic=conf.NIC_NAME[1],
                network=conf.VLAN_NETWORKS[0], disable_mirroring=True,
                teardown=True
            )
    request.addfinalizer(fin)
