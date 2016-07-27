#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Port Mirroring
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as pm_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as networking_helper
from rhevmtests import helpers, networking
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def port_mirroring_prepare_setup(request):
    """
    Setup and teardown for Port Mirroring
    """
    port_mirroring = NetworkFixtures()
    bond_1 = "bond01"
    vm_list = conf.VM_NAME[:pm_conf.NUM_VMS]

    @networking.ignore_exception
    def fin5():
        """
        Remove networks
        """
        hl_networks.remove_net_from_setup(
            host=port_mirroring.hosts_list, data_center=port_mirroring.dc_0,
            all_net=True
        )
    request.addfinalizer(fin5)

    @networking.ignore_exception
    def fin4():
        """
        Remove all vNIC profiles from setup
        """
        networking.remove_unneeded_vnic_profiles()
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
        Stop all VMs
        """
        ll_vms.stop_vms_safely(vms_list=conf.VM_NAME)
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Remove ifcfg files from VMs
        """
        networking_helper.remove_ifcfg_files(
            vms=conf.VM_NAME[:pm_conf.NUM_VMS]
        )
    request.addfinalizer(fin1)

    networking_helper.prepare_networks_on_setup(
        networks_dict=pm_conf.NETS_DICT, dc=port_mirroring.dc_0,
        cluster=port_mirroring.cluster_0
    )
    local_dict = {
        "add": {
            "1": {
                "network": pm_conf.PM_NETWORK[1],
                "slaves": port_mirroring.host_0_nics[2:4],
                "nic": bond_1,
            },
            "2": {
                "network": pm_conf.PM_NETWORK[0],
                "nic": port_mirroring.host_0_nics[1],
            },

        }
    }
    for host_name in port_mirroring.hosts_list:
        assert hl_host_network.setup_networks(
            host_name=host_name, **local_dict
        )

    helper.create_vnic_profiles_with_pm()

    assert helper.set_port_mirroring(
        vm=port_mirroring.vm_0, nic=conf.NIC_NAME[0],
        network=port_mirroring.mgmt_bridge
    )
    hl_vms.start_vms_on_specific_host(
        vm_list=vm_list, max_workers=len(vm_list),
        host=port_mirroring.host_0_name, wait_for_ip=False,
        wait_for_status=conf.ENUMS['vm_state_up']
    )
    helper.add_nics_to_vms()
    helper.prepare_ips_for_vms()
    helper.configure_ip_all_vms()

    for vm in conf.VM_NAME[:2]:
        vm_resource = helpers.get_vm_resource(vm=vm)
        interfaces = networking_helper.get_vm_interfaces_list(
            vm_resource=vm_resource
        )
        assert interfaces
        pm_conf.VM_NICS_DICT[vm] = interfaces

    helper.vms_network_params()

    for host in port_mirroring.vds_list:
        assert host.service(conf.FIREWALL_SRV).stop(), (
            "Cannot stop Firewall service"
        )


@pytest.fixture(scope="class")
def return_vms_to_original_host(request):
    """
    Return VMs to original host.
    """
    NetworkFixtures()

    def fin():
        """
        Migrate all VMs back to original host
        """
        helper.return_vms_to_original_host()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def disable_port_mirroring(request):
    """
    Disable port mirroring.
    """
    NetworkFixtures()

    def fin():
        """
        Disable PM for non first VM
        """
        for vm_name in conf.VM_NAME[2:4]:
            assert helper.set_port_mirroring(
                vm=vm_name, nic=pm_conf.PM_NIC_NAME[1][1], teardown=True,
                network=pm_conf.PM_NETWORK[0], disable_mirroring=True
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def set_port_mirroring(request):
    """
    Set port mirroring.
    """
    port_mirroring = NetworkFixtures()

    assert helper.set_port_mirroring(
        vm=port_mirroring.vm_1, nic=pm_conf.PM_NIC_NAME[1][1],
        network=pm_conf.PM_NETWORK[0]
    )
