#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Linking/Plugging feature.
1 DC, 1 Cluster, 1 Hosts and 2 VMs will are used for testing.
Linking/Plugging will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for different states of VNIC on stopped/running VM.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as linking_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_help
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    fixture_case_01, fixture_case_02, fixture_case_03, fixture_case_04,
    fixture_case_05, fixture_case_06
)

logger = logging.getLogger("Linking_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_01.__name__)
class TestLinkedCase01(NetworkTest):
    """
    Add a new network to VM with default plugged and linked states
    Check that plugged and linked are True by default
    """
    __test__ = True
    vm = conf.VM_1
    nic1 = conf.NIC_NAME[1]
    nic_list = [nic1]
    net = linking_conf.NETS[1][0]

    @polarion("RHEVM3-3817")
    def test_check_default_values(self):
        """
        Check the default values for the Plugged/Linked options on VNIC
        """
        testflow.step(
            "Check the default values for the Plugged/Linked options on VNIC"
        )
        self.assertTrue(
            ll_vms.get_vm_nic_linked(vm=self.vm, nic=self.nic1)
        )

        self.assertTrue(
            ll_vms.get_vm_nic_plugged(vm=self.vm, nic=self.nic1)
        )


@attr(tier=2)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(fixture_case_02.__name__)
class TestLinkedCase02(NetworkTest):
    """
    Create permutation for the Plugged/Linked vNIC
    Use e1000 and rtl8139 drivers
    """
    __test__ = True
    vm = conf.VM_1
    plug_values = [True, True]
    link_values = [True, False]
    net_list = linking_conf.NETS[1]
    nic_list = conf.NIC_NAME[1:3]
    int_type_list = [conf.NIC_TYPE_RTL8139, conf.NIC_TYPE_E1000]

    @polarion("RHEVM3-3834")
    def test_check_combination_plugged_linked_values(self):
        """
        Check linked state of both vNICs
        Update vNICs with opposite link states and check the change
        Update vNICs with empty network
        Update vNICs with original names and unplug them
        Check the network on vNICs and their unplug state
        """
        testflow.step("Check linked state of both vNICs")
        for nic, state in zip(self.nic_list, self.link_values):
            self.assertTrue(
                ll_vms.get_vm_nic_linked(vm=self.vm, nic=nic, positive=state)
            )
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=nic, linked=not state
                )
            )
            self.assertTrue(
                ll_vms.get_vm_nic_linked(
                    vm=self.vm, nic=nic, positive=not state
                )
            )
        testflow.step(
            "Update vNICs with opposite link states and check the change "
            "Update vNICs with empty network Update vNICs with original "
            "names and unplug them"
        )
        for nic_name in self.nic_list:
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=nic_name, network=None
                )
            )

        for nic, net in zip(self.nic_list, self.net_list):
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=nic, network=net,
                    vnic_profile=net, plugged=False
                )
            )

        for nic in self.nic_list:
            self.assertTrue(ll_vms.getVmNicNetwork(vm=self.vm, nic=nic))
            self.assertTrue(
                ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic, positive=False)
            )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_03.__name__)
class TestLinkedCase03(NetworkTest):
    """
    Try to run VM with network attached to Cluster but not to the host
    The test should fail as VM can't run when there is no network on
    at least one host of the Cluster
    """
    __test__ = True
    vm = conf.VM_1
    nic1 = conf.NIC_NAME[1]
    nic_list = [nic1]
    net = conf.NETWORKS[0]

    @polarion("RHEVM3-3833")
    def test_check_start_vm(self):
        """
        Try to start VM when there is no network on the host
        """
        testflow.step("Try to start VM when there is no network on the host")
        self.assertTrue(ll_vms.startVm(positive=False, vm=self.vm))


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_04.__name__)
class TestLinkedCase04(NetworkTest):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True
    vm = conf.VM_NAME[0]
    nic1 = conf.NIC_NAME[1]
    nic_list = [nic1]
    net = linking_conf.NETS[1][0]
    vprofile = "pm_linking"

    @polarion("RHEVM3-3823")
    def test_check_port_mirroring_network(self):
        """
        Check scenarios for port mirroring network
        """
        testflow.step(
            "Editing plugged VNIC with port mirroring enabled on running VM"
        )
        self.assertTrue(
            ll_vms.updateNic(
                positive=False, vm=self.vm, nic=self.nic1, linked=False
            )
        )

        for plugged in (False, True):
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=self.nic1, plugged=plugged
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_05.__name__)
class TestLinkedCase05(NetworkTest):
    """
    Create VNICs with linked/unlinked states on running VM.
    Change network parameters for both VNICs:
    Change nic names, link/plugged states
    """
    __test__ = True
    vm = conf.VM_NAME[0]
    nic1 = conf.NIC_NAME[1]
    nic2 = conf.NIC_NAME[2]
    nic_list = [nic1, nic2]
    net = linking_conf.NETS[1][0]
    plug_states = [True, False]
    nic_names = ["vnic2", "vnic3"]

    @polarion("RHEVM3-3825")
    def test_change_net_param_values(self):
        """
        Check network parameters changes for vNICs
        Change NIC names, update linked/plugged states
        Remove and return network from the VNIC
        """
        testflow.step("Check network parameters changes for vNICs")
        for nic, plug_state in zip(self.nic_list, self.plug_states):
            self.assertTrue(
                ll_vms.get_vm_nic_plugged(
                    vm=self.vm, nic=nic, positive=plug_state
                )
            )

        plug_states = [False, True]
        testflow.step("Change NIC names, update linked/plugged states")
        for nic, name, plug_state in zip(
            self.nic_list, self.nic_names, plug_states
        ):
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=nic, name=name,
                    network=self.net, vnic_profile=self.net, plugged=plug_state
                )
            )

        for nic, plug_state in zip(self.nic_names, plug_states):
            self.assertTrue(
                ll_vms.get_vm_nic_plugged(
                    vm=self.vm, nic=nic, positive=plug_state
                )
            )

        for nic_name in self.nic_names:
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=nic_name, network=self.net,
                    vnic_profile=self.net, plugged=False
                )
            )

        for nic_name in self.nic_names:
            self.assertTrue(ll_vms.getVmNicNetwork(vm=self.vm, nic=nic_name))
            self.assertFalse(
                ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic_name)
            )

        testflow.step("Remove and return network from the VNIC")
        for nic_name, orig_nic in zip(self.nic_names, self.nic_list):
            self.assertTrue(
                ll_vms.updateNic(
                    positive=True, vm=self.vm, nic=nic_name, name=orig_nic
                )
            )


@attr(tier=2)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(fixture_case_06.__name__)
class TestLinkedCase06(NetworkTest):
    """
    Changing several network parameters at once on non-running VM
    """
    __test__ = True
    vm = conf.VM_1
    nic1 = conf.NIC_NAME[1]
    net1 = linking_conf.NETS[1][0]
    net2 = linking_conf.NETS[1][1]
    nic_list = [nic1]
    vprofile = "pm_7_linking"
    name = "vnic2"
    rtl_int = conf.NIC_TYPE_RTL8139
    mac_addr = "12:22:33:44:55:66"

    @polarion("RHEVM3-3826")
    def test_change_net_param_values(self):
        """
        Change plugged, network and name at once on VNIC of VM
        """
        testflow.step("Change plugged, network and name at once on VNIC of VM")
        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=self.vm, nic=self.nic1, name=self.name,
                network=self.net2, vnic_profile=self.net2, plugged=False
            )
        )

        self.assertFalse(ll_vms.get_vm_nic_plugged(vm=self.vm, nic=self.name))

        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=self.vm, nic=self.name, name=self.nic1,
                network=self.net1, vnic_profile=self.net1, linked=False
            )
        )

        self.assertFalse(ll_vms.get_vm_nic_linked(vm=self.vm, nic=self.nic1))

        self.assertTrue(
            net_help.run_vm_once_specific_host(
                vm=self.vm, host=conf.HOSTS[0], wait_for_up_status=True
            )
        )

        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=self.vm, nic=self.nic1, linked=True,
                plugged=True, network=self.net2, vnic_profile=self.vprofile
            )
        )

        self.assertTrue(
            ll_vms.updateNic(
                positive=False, vm=self.vm, nic=self.nic1,
                interface=self.rtl_int, mac_address=self.mac_addr
            )
        )

        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=self.vm, nic=self.nic1, network=self.net2,
                vnic_profile=self.net2, linked=False, plugged=False
            )
        )

        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=self.vm, nic=self.nic1,
                interface=self.rtl_int, mac_address=self.mac_addr
            )
        )
