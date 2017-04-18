#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Port Mirroring
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as pm_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.unittest_lib import testflow
from rhevmtests import networking
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
        testflow.teardown("Remove networks from setup")
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
        testflow.teardown("Remove unneeded vnic profiles")
        networking.remove_unneeded_vnic_profiles()
    request.addfinalizer(fin4)

    @networking.ignore_exception
    def fin3():
        """
        Finalizer for remove vNICs from VMs
        """
        testflow.teardown("Remove unneeded VMs NICs")
        networking.remove_unneeded_vms_nics()
    request.addfinalizer(fin3)

    @networking.ignore_exception
    def fin2():
        """
        Stop all VMs
        """
        testflow.teardown("Stop all VMs")
        ll_vms.stop_vms_safely(vms_list=conf.VM_NAME)
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Remove ifcfg files from VMs
        """
        vms_resources = list()
        for vm in conf.VM_NAME[:pm_conf.NUM_VMS]:
            vms_resources.append(
                pm_conf.VMS_NETWORKS_PARAMS.get(vm).get("resource")
            )
            testflow.teardown("Remove ifcfg files from VMs")
        assert network_helper.remove_ifcfg_files(vms_resources=vms_resources)
    request.addfinalizer(fin1)

    network_helper.prepare_networks_on_setup(
        networks_dict=pm_conf.NETS_DICT, dc=port_mirroring.dc_0,
        cluster=port_mirroring.cluster_0
    )
    sn_dict = {
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
        assert hl_host_network.setup_networks(host_name=host_name, **sn_dict)

    testflow.setup("Create vnic profiles with port mirroring")
    helper.create_vnic_profiles_with_pm()
    testflow.setup("Set port mirroring on VM %s", port_mirroring.vm_0)
    assert helper.set_port_mirroring(
        vm=port_mirroring.vm_0, nic=conf.NIC_NAME[0],
        network=port_mirroring.mgmt_bridge
    )
    for vm in vm_list:
        testflow.setup(
            "Start VM %s on specific host %s", vm, port_mirroring.host_0_name
        )
        assert ll_vms.runVmOnce(
            positive=True, vm=vm, host=port_mirroring.host_0_name,
            wait_for_state=conf.ENUMS["vm_state_up"]
        )

    testflow.setup("Add nics to VMs")
    helper.add_nics_to_vms()
    helper.set_vms_network_params()


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
        testflow.teardown("Return VMs to original host")
        assert helper.migrate_vms_to_origin_host()
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
            testflow.teardown("Disable port mirroring on VM %s", vm_name)
            assert helper.set_port_mirroring(
                vm=vm_name, nic=pm_conf.PM_NIC_NAME[0], teardown=True,
                network=pm_conf.PM_NETWORK[0], disable_mirroring=True
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def set_port_mirroring(request):
    """
    Set port mirroring.
    """
    port_mirroring = NetworkFixtures()

    testflow.step("Set port on VM %s", port_mirroring.vm_1)
    assert helper.set_port_mirroring(
        vm=port_mirroring.vm_1, nic=pm_conf.PM_NIC_NAME[0],
        network=pm_conf.PM_NETWORK[0]
    )
