#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Tests for the Network Linking feature

The following elements will be created for the testing:
1 DC, 1 Cluster, 1 Hosts, 8 vNICs, 3 vNIC profiles, 7 networks and 2 VMs
"""

import config as linking_conf

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_network,
    vms as hl_vms,
    networks as hl_networks
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from rhevmtests.fixtures import start_vm
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import (
    NetworkFixtures,
    add_vnic_profiles,
    remove_vnic_profiles,
    add_vnics_to_vms,
    remove_vnics_from_vms
)


@pytest.fixture(scope="module", autouse=True)
def linking_prepare_setup(request):
    """
    Prepare shared environment for cases
    """
    linking = NetworkFixtures()
    setup_net_dict = {
        "add": {
            "1": {
                "network": linking_conf.CASE_01_NET_1,
                "nic": linking.host_0_nics[1]
            },
            "2": {
                "network": linking_conf.CASE_02_NET_1,
                "nic": linking.host_0_nics[1]
            },
            "3": {
                "network": linking_conf.CASE_02_NET_2,
                "nic": linking.host_0_nics[1]
            },
            "4": {
                "network": linking_conf.CASE_04_NET_1,
                "nic": linking.host_0_nics[1]
            },
            "5": {
                "network": linking_conf.CASE_05_NET_1,
                "nic": linking.host_0_nics[1]
            },
            "6": {
                "network": linking_conf.CASE_05_NET_2,
                "nic": linking.host_0_nics[1]
            }
        }
    }

    def fin():
        """
        Remove networks from setup
        """
        assert hl_networks.remove_net_from_setup(
            host=[linking.host_0_name], all_net=True,
            data_center=linking.dc_0
        )
    request.addfinalizer(fin)

    assert hl_networks.create_and_attach_networks(
        networks=linking_conf.NET_DICT, data_center=linking.dc_0,
        clusters=[linking.cluster_0]
    )

    assert hl_host_network.setup_networks(
        host_name=linking.host_0_name, **setup_net_dict
    )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__
)
class TestLinkedCase01(NetworkTest):
    """
    Check if plugged/linked properties are enabled by default
    """

    vm = conf.VM_1
    vnic = linking_conf.CASE_01_VNIC_1
    net_1 = linking_conf.CASE_01_NET_1

    add_vnics_vms_params = {
        "1":
            {
                "vm": vm,
                "name": vnic,
                "network": net_1
            }
    }

    remove_vnics_vms_params = add_vnics_vms_params

    @tier2
    @polarion("RHEVM3-3817")
    def test_check_default_values(self):
        """
        Check the default plugged/linked states on vNIC
        """
        testflow.step("Check the default plugged/linked states on vNIC")
        assert ll_vms.get_vm_nic_linked(vm=self.vm, nic=self.vnic)
        assert ll_vms.get_vm_nic_plugged(vm=self.vm, nic=self.vnic)


@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__
)
class TestLinkedCase02(NetworkTest):
    """
    Create permutation for a plugged/linked vNIC, use e1000 and rtl8139
    drivers
    """

    add_vnics_vms_params = {
        "1":
            {
                "vm": conf.VM_1,
                "name": linking_conf.CASE_02_VNIC_1,
                "network": linking_conf.CASE_02_NET_1,
                "interface": conf.NIC_TYPE_RTL8139,
                "plugged": True,
                "linked": True
            },
        "2":
            {
                "vm": conf.VM_1,
                "name": linking_conf.CASE_02_VNIC_2,
                "network": linking_conf.CASE_02_NET_2,
                "interface": conf.NIC_TYPE_E1000,
                "plugged": True,
                "linked": False

            }
    }

    remove_vnics_vms_params = add_vnics_vms_params

    @tier2
    @polarion("RHEVM3-3834")
    def test_check_combination_plugged_linked_values(self):
        """
        1.  Check linked state of both vNICs
        2.  Update and check vNICs with opposite link states and check
            the change
        3.  Update and check vNICs with empty network
        4.  Update and check vNICs with original names and unplug them
        5.  Check the network on vNICs and their unplug state
        """
        for vnic_props in self.add_vnics_vms_params.values():
            vm = vnic_props.get("vm")
            vnic = vnic_props.get("name")
            linked = vnic_props.get("linked")
            net = vnic_props.get("network")

            testflow.step(
                "Checking link state of vNIC: %s on VM: %s", vnic, vm
            )
            assert ll_vms.get_vm_nic_linked(vm=vm, nic=vnic, positive=linked)

            testflow.step(
                "Updating link state of vNIC: %s to: %s (opposite value)",
                vnic, not linked
            )
            assert ll_vms.updateNic(
                positive=True, vm=vm, nic=vnic, linked=not linked
            )

            testflow.step("Checking updated link state of vNIC: %s ", vnic)
            assert ll_vms.get_vm_nic_linked(
                vm=vm, nic=vnic, positive=not linked
            )

            testflow.step(
                "Updating and checking vNIC: %s with empty network", vnic
            )
            assert ll_vms.updateNic(
                positive=True, vm=vm, nic=vnic, network=None
            )

            testflow.step("Restoring vNIC: %s settings", vnic)
            assert ll_vms.updateNic(
                positive=True, vm=vm, nic=vnic, network=net,
                vnic_profile=net, plugged=False
            )
            testflow.step(
                "Negative: checking if vNIC: %s is in plugged state", vnic
            )
            assert ll_vms.get_vm_nic_plugged(vm=vm, nic=vnic, positive=False)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__
)
class TestLinkedCase03(NetworkTest):
    """
    Try to run a VM with network attached to cluster and not host, the test
    should fail as VM can't run when there is no network on at least one host
    of the cluster
    """

    vm = conf.VM_1

    add_vnics_vms_params = {
        "1":
            {
                "vm": conf.VM_1,
                "name": linking_conf.CASE_03_VNIC_1,
                "network": linking_conf.CASE_03_NET_1
            }
    }

    remove_vnics_vms_params = add_vnics_vms_params

    @tier2
    @polarion("RHEVM3-3833")
    def test_check_start_vm(self):
        """
        Negative: try to start a VM when there is no network on the host
        """
        testflow.step(
            "Negative: try to start VM when there is no network on the host"
        )
        assert ll_vms.startVm(positive=False, vm=self.vm)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_vnic_profiles.__name__,
    remove_vnics_from_vms.__name__,
    add_vnic_profiles.__name__,
    add_vnics_to_vms.__name__,
    start_vm.__name__
)
class TestLinkedCase04(NetworkTest):
    """
    1.  Create vNICs with linked/unlinked states on running VM
    2.  Change network parameters for both VNICs:
    3.  Change nic names, link/plugged states
    """

    vm_name = conf.VM_0
    vnic_1 = linking_conf.CASE_04_VNIC_1
    vnic_2 = linking_conf.CASE_04_VNIC_2
    vnic_3 = linking_conf.CASE_04_VNIC_3
    nic_list = [vnic_1, vnic_2]
    net_1 = linking_conf.CASE_04_NET_1
    plug_states = [True, False]
    nic_names = [
        linking_conf.CASE_04_VNIC_1_REN, linking_conf.CASE_04_VNIC_2_REN
    ]
    start_vms_dict = {
        vm_name: {}
    }

    add_vnics_vms_params = {
        "1":
            {
                "vm": vm_name,
                "name": vnic_1,
                "network": net_1,
                "plugged": True
            },
        "2":
            {
                "vm": vm_name,
                "name": vnic_2,
                "network": net_1,
                "plugged": False
            },
        "3":
            {
                "vm": vm_name,
                "name": vnic_3,
                "network": net_1,
                "vnic_profile": linking_conf.CASE_04_VNIC_PROFILE_1
            }
    }

    remove_vnics_vms_params = add_vnics_vms_params

    add_vnic_profile_params = {
        linking_conf.CASE_04_VNIC_PROFILE_1: {
            "name": linking_conf.CASE_04_VNIC_PROFILE_1,
            "network": net_1,
            "port_mirroring": True
        }
    }

    remove_vnic_profile_params = add_vnic_profile_params

    @tier2
    @polarion("RHEVM3-3825")
    def test_change_net_param_values(self):
        """
        1.  Check network parameters changes for vNICs
        2.  Change NIC names, update linked/plugged states
        3.  Remove and return network from the VNIC
        """
        testflow.step("Check network parameters changes for vNICs")
        for nic, plug_state in zip(self.nic_list, self.plug_states):
            assert ll_vms.get_vm_nic_plugged(
                vm=self.vm_name, nic=nic, positive=plug_state
            )

        testflow.step(
            "Update and check vNIC properties and linked/plugged states"
        )
        plug_states = [False, True]
        for nic, name, plug_state in zip(
            self.nic_list, self.nic_names, plug_states
        ):
            assert ll_vms.updateNic(
                positive=True, vm=self.vm_name, nic=nic, name=name,
                network=self.net_1, vnic_profile=self.net_1, plugged=plug_state
            )

        for nic, plug_state in zip(self.nic_names, plug_states):
            prefix = "Negative: " if plug_state else ""
            testflow.step("%sCheck vNIC: %s plugged state", prefix, nic)
            assert ll_vms.get_vm_nic_plugged(
                vm=self.vm_name, nic=nic, positive=plug_state
            )

        for nic_name in self.nic_names:
            testflow.step("Update vNIC: %s to be unplugged", nic_name)
            assert ll_vms.updateNic(
                positive=True, vm=self.vm_name, nic=nic_name,
                network=self.net_1, vnic_profile=self.net_1, plugged=False
            )

        for nic_name in self.nic_names:
            testflow.step(
                "Negative: check if VM: %s vNIC: %s is plugged", self.vm_name,
                nic_name
            )
            assert ll_vms.get_vm_nic_plugged(
                vm=self.vm_name, nic=nic_name, positive=False
            )

        testflow.step("Remove and return network from the vNIC")
        for nic_name, orig_nic in zip(self.nic_names, self.nic_list):
            assert ll_vms.updateNic(
                positive=True, vm=self.vm_name, nic=nic_name, name=orig_nic
            )

    @tier2
    @polarion("RHEVM3-3823")
    def test_check_port_mirroring_network(self):
        """
        Check scenarios for port mirroring network
        """
        testflow.step(
            "Negative: unlink vNIC: %s on VM: %s", self.vnic_3, self.vm_name
        )
        assert ll_vms.updateNic(
            positive=False, vm=self.vm_name, nic=self.vnic_3, linked=False
        )

        for plugged in (False, True):
            testflow.step(
                "Set plugged=%s on vNIC: %s on VM: %s", plugged, self.vnic_3,
                self.vm_name
            )
            assert ll_vms.updateNic(
                positive=True, vm=self.vm_name, nic=self.vnic_3,
                plugged=plugged
            )


@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_vnics_from_vms.__name__,
    remove_vnic_profiles.__name__,
    add_vnics_to_vms.__name__,
    add_vnic_profiles.__name__,
    start_vm.__name__
)
class TestLinkedCase05(NetworkTest):
    """
    Check vNIC update scenarios on VM (both on and off) with plugged and
    linked vNIC states
    """

    vm = conf.VM_1
    vms_to_stop = [vm]
    vnic = linking_conf.CASE_05_VNIC_1
    net_1 = linking_conf.CASE_05_NET_1
    net_2 = linking_conf.CASE_05_NET_2
    name = linking_conf.CASE_05_VNIC_PROFILE_2
    rtl_int = conf.NIC_TYPE_RTL8139
    mac_addr = "12:22:33:44:55:66"

    add_vnics_vms_params = {
        "1":
            {
                "vm": vm,
                "name": vnic,
                "network": net_1,
            }
    }

    remove_vnics_vms_params = add_vnics_vms_params

    add_vnic_profile_params = {
        linking_conf.CASE_05_VNIC_PROFILE_1: {
            "name": linking_conf.CASE_05_VNIC_PROFILE_1,
            "network": net_2
        }
    }
    remove_vnic_profile_params = add_vnic_profile_params

    @tier2
    @polarion("RHEVM3-3826")
    def test_change_net_param_values(self):
        """
        Change plugged, network and name at once on vNIC of VM (powered-on
        and powered-off)
        """
        testflow.step("Unplug vNIC: %s on VM: %s", self.vnic, self.vm)
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, name=self.name,
            network=self.net_2, vnic_profile=self.net_2, plugged=False
        )

        testflow.step("Negative: check if vNIC: %s is plugged", self.name)
        assert ll_vms.get_vm_nic_plugged(
            vm=self.vm, nic=self.name, positive=False
        )

        testflow.step("Unlink vNIC: %s on VM: %s", self.vnic, self.vm)
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.name, name=self.vnic,
            network=self.net_1, vnic_profile=self.net_1, linked=False
        )

        testflow.step("Negative: check if vNIC: %s is linked", self.vnic)
        assert ll_vms.get_vm_nic_linked(
            vm=self.vm, nic=self.vnic, positive=False
        )

        testflow.step(
            "Run once VM: %s on host: %s", self.vm, conf.HOST_0_NAME
        )
        assert hl_vms.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )

        testflow.step(
            "Update vNIC: %s with plugged=True, linked=True", self.vnic
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, linked=True,
            plugged=True, network=self.net_2,
            vnic_profile=linking_conf.CASE_05_VNIC_PROFILE_1
        )

        testflow.step("Negative: try to update interface type and mac address")
        assert ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vnic,
            interface=self.rtl_int, mac_address=self.mac_addr
        )

        testflow.step(
            "Update vNIC: %s with plugged=False, linked=False", self.vnic
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_2,
            vnic_profile=self.net_2, linked=False, plugged=False
        )

        testflow.step("Update interface type and MAC address")
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic,
            interface=self.rtl_int, mac_address=self.mac_addr
        )
