#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Port Mirroring
"""

import pytest

from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_network,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms
)
import config as pm_conf
import helper
import rhevmtests.helpers as global_helper
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)
from art.unittest_lib import testflow


@pytest.fixture(scope="module")
def port_mirroring_prepare_setup(request):
    """
    Setup and teardown for Port Mirroring
    """
    bond_1 = "bond01"
    vm_list = conf.VM_NAME[:pm_conf.NUM_VMS]
    result = list()

    def fin7():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)
    request.addfinalizer(fin7)

    def fin6():
        """
        Remove networks
        """
        result.append(
            (
                hl_networks.remove_net_from_setup(
                    host=conf.HOSTS[:2], data_center=conf.DC_0, all_net=True
                ), "fin6:  hl_networks.remove_net_from_setup"
            )
        )
    request.addfinalizer(fin6)

    def fin5():
        """
        Remove all vNIC profile from setup
        """
        result.append(
            (
                ll_networks.remove_vnic_profile(
                    positive=True,
                    vnic_profile_name=pm_conf.PM_VNIC_PROFILE[0],
                    network=conf.MGMT_BRIDGE, data_center=conf.DC_0
                ), "fin5: ll_networks.remove_vnic_profile"
            )
        )

    request.addfinalizer(fin5)

    def fin4():
        """
        Finalizer for remove vNICs from VMs
        """
        for vm_name in vm_list:
            for nic, net in zip(
                pm_conf.PM_NIC_NAME, pm_conf.PM_NETWORK[:2]
            ):
                result.append(
                    (
                        ll_vms.removeNic(positive=True, vm=vm_name, nic=nic),
                        "fin4: ll_vms.removeNic"
                    )
                )
    request.addfinalizer(fin4)

    def fin3():
        """
        Finalizer for updating vNIC to original VM NIC
        """
        result.append(
            (
                ll_vms.updateNic(
                    positive=True, vm=conf.VM_0, nic=conf.NIC_NAME[0],
                    network=conf.MGMT_BRIDGE, vnic_profile=conf.MGMT_BRIDGE,
                ), "fin3: ll_vms.updateNic"
            )
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Stop all VMs
        """
        testflow.teardown("Stop all VMs")
        result.append(
            (
                ll_vms.stop_vms_safely(vms_list=conf.VM_NAME),
                "fin: ll_vms.stop_vms_safely"
            )
        )
    request.addfinalizer(fin2)

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
        result.append(
            (
                network_helper.remove_ifcfg_files(vms_resources=vms_resources),
                "fin1: network_helper.remove_ifcfg_files"
            )
        )
    request.addfinalizer(fin1)

    assert hl_networks.create_and_attach_networks(
        networks=pm_conf.NETS_DICT, data_center=conf.DC_0, clusters=[conf.CL_0]
    )
    sn_dict = {
        "add": {
            "1": {
                "network": pm_conf.PM_NETWORK[1],
                "slaves": None,
                "nic": bond_1,
            },
            "2": {
                "network": pm_conf.PM_NETWORK[0],
                "nic": None
            },

        }
    }
    hosts_and_nics = (
        (conf.HOST_0_NAME, conf.HOST_0_NICS),
        (conf.HOST_1_NAME, conf.HOST_1_NICS)
    )
    for host, nics in hosts_and_nics:
        sn_dict["add"]["1"]["slaves"] = nics[2:4]
        sn_dict["add"]["2"]["nic"] = nics[1]
        assert hl_host_network.setup_networks(host_name=host, **sn_dict)

    testflow.setup("Create vnic profiles with port mirroring")
    helper.create_vnic_profiles_with_pm()

    testflow.setup("Set port mirroring on VM %s", conf.VM_0)
    assert ll_vms.updateNic(
        positive=True, vm=conf.VM_0, nic=conf.NIC_NAME[0],
        network=conf.MGMT_BRIDGE, vnic_profile=pm_conf.PM_VNIC_PROFILE[0]
    )
    for vm in vm_list:
        testflow.setup(
            "Start VM %s on specific host %s", vm, conf.HOST_0_NAME
        )
        assert ll_vms.runVmOnce(
            positive=True, vm=vm, host=conf.HOST_0_NAME,
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
    result = list()

    def fin2():
        """
        Check if the finalizer failed.
        """
        global_helper.raise_if_false_in_list(results=result)
    request.addfinalizer(fin2)

    def fin1():
        """
        Disable PM for non first VM
        """
        for vm_name in conf.VM_NAME[2:4]:
            result.append(
                (
                    helper.set_port_mirroring(
                        vm=vm_name, nic=pm_conf.PM_NIC_NAME[0],
                        network=pm_conf.PM_NETWORK[0], disable_mirroring=True
                    ), "fin1: helper.set_port_mirroring"
                )
            )
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def set_port_mirroring(request):
    """
    Set port mirroring.
    """

    testflow.step("Set port on VM %s", conf.VM_1)
    assert helper.set_port_mirroring(
        vm=conf.VM_1, nic=pm_conf.PM_NIC_NAME[0], network=pm_conf.PM_NETWORK[0]
    )
