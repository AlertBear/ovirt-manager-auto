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
import config as conf
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Linking_Cases")


@attr(tier=2)
class TestLinkedCasesBase(NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    nic_list = list()
    vm = None

    @classmethod
    def teardown_class(cls):
        """
        Remove all vNICs (besides nic1) from VM
        """
        for nic in cls.nic_list:
            if cls.vm == conf.VM_NAME[0]:
                ll_vms.updateNic(
                    positive=True, vm=cls.vm, nic=nic, plugged=False
                )

            ll_vms.removeNic(positive=True, vm=cls.vm, nic=nic)


class TestLinkedCase01(TestLinkedCasesBase):
    """
    Add a new network to VM with default plugged and linked states
    Check that plugged and linked are True by default
    """
    __test__ = True
    vm = conf.VM_NAME[1]
    nic1 = conf.NIC_NAME[1]
    nic_list = [nic1]
    net = conf.NETS[1][0]

    @classmethod
    def setup_class(cls):
        """
        Create 1 vNIC on stopped VM with default plugged/linked states
        """
        if not ll_vms.addNic(
            positive=True, vm=cls.vm, name=cls.nic1, network=cls.net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3817")
    def test_check_default_values(self):
        """
        Check the default values for the Plugged/Linked options on VNIC
        """
        if not ll_vms.get_vm_nic_linked(vm=self.vm, nic=self.nic1):
            raise conf.NET_EXCEPTION()

        if not ll_vms.get_vm_nic_plugged(vm=self.vm, nic=self.nic1):
            raise conf.NET_EXCEPTION()


@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestLinkedCase02(TestLinkedCasesBase):
    """
    Create permutation for the Plugged/Linked vNIC
    Use e1000 and rtl8139 drivers
    """
    __test__ = True
    vm = conf.VM_NAME[1]
    plug_values = [True, True]
    link_values = [True, False]
    net_list = conf.NETS[1]
    nic_list = conf.NIC_NAME[1:3]
    int_type_list = [conf.NIC_TYPE_RTL8139, conf.NIC_TYPE_E1000]

    @classmethod
    def setup_class(cls):
        """
        Create 2 VNICs on stopped VM with different NIC type for plugged/linked
        """
        for int_type, nic, net, plug_value, link_value in zip(
            cls.int_type_list, cls.nic_list, cls.net_list, cls.plug_values,
            cls.link_values
        ):
            if not ll_vms.addNic(
                positive=True, vm=cls.vm, name=nic, network=net,
                interface=int_type, plugged=plug_value, linked=link_value
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3834")
    def test_check_combination_plugged_linked_values(self):
        """
        Check linked state of both vNICs
        Update vNICs with opposite link states and check the change
        Update vNICs with empty network
        Update vNICs with original names and unplug them
        Check the network on vNICs and their unplug state
        """
        for nic, state in zip(self.nic_list, self.link_values):
            if not ll_vms.get_vm_nic_linked(
                vm=self.vm, nic=nic, positive=state
            ):
                raise conf.NET_EXCEPTION()
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic, linked=not state
            ):
                raise conf.NET_EXCEPTION()
            if not ll_vms.get_vm_nic_linked(
                vm=self.vm, nic=nic, positive=not state
            ):
                raise conf.NET_EXCEPTION()

        for nic_name in self.nic_list:
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic_name, network=None
            ):
                raise conf.NET_EXCEPTION()

        for nic, net in zip(self.nic_list, self.net_list):
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic, network=net,
                vnic_profile=net, plugged=False
            ):
                raise conf.NET_EXCEPTION()

        for nic in self.nic_list:
            if not ll_vms.getVmNicNetwork(vm=self.vm, nic=nic):
                raise conf.NET_EXCEPTION()
            if not ll_vms.get_vm_nic_plugged(
                vm=self.vm, nic=nic, positive=False
            ):
                raise conf.NET_EXCEPTION()


class TestLinkedCase03(TestLinkedCasesBase):
    """
    Try to run VM with network attached to Cluster but not to the host
    The test should fail as VM can't run when there is no network on
    at least one host of the Cluster
    """
    __test__ = True
    vm = conf.VM_NAME[1]
    nic1 = conf.NIC_NAME[1]
    nic_list = [nic1]
    net = conf.NETWORKS[0]

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster and add it to VM
        """
        local_dict = {
            cls.net: {
                "required": "false"
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CL_0, network_dict=local_dict
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=cls.vm, name=cls.nic1, network=cls.net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3833")
    def test_check_start_vm(self):
        """
        Try to start VM when there is no network on the host
        """
        if not ll_vms.startVm(positive=False, vm=self.vm):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VM and network from the setup.
        """
        super(TestLinkedCase03, cls).teardown_class()
        ll_networks.removeNetwork(
            positive=True, network=cls.net, data_center=conf.DC_0
        )


class TestLinkedCase04(TestLinkedCasesBase):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True
    vm = conf.VM_NAME[0]
    nic1 = conf.NIC_NAME[1]
    nic_list = [nic1]
    net = conf.NETS[1][0]
    vprofile = "pm_linking"

    @classmethod
    def setup_class(cls):
        """
        Create 1 plugged/linked VNIC with port mirroring enabled
        on running VM
        """
        if not ll_networks.add_vnic_profile(
            positive=True, name=cls.vprofile, cluster=conf.CL_0,
            network=cls.net, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=cls.vm, name=cls.nic1,
            vnic_profile=cls.vprofile, network=cls.net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3823")
    def test_check_port_mirroring_network(self):
        """
        Check scenarios for port mirroring network
        """
        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.nic1, linked=False
        ):
            raise conf.NET_EXCEPTION()

        for plugged in (False, True):
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=self.nic1, plugged=plugged
            ):
                raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VM and remove vNIC profile
        """
        super(TestLinkedCase04, cls).teardown_class()
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.vprofile, network=cls.net
        )


class TestLinkedCase05(TestLinkedCasesBase):
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
    net = conf.NETS[1][0]
    plug_states = [True, False]
    nic_names = ["vnic2", "vnic3"]

    @classmethod
    def setup_class(cls):
        """
        Create 2 VNICs on running VM with different linked states for VNICs
        """
        for nic, plug_state in zip(cls.nic_list, cls.plug_states):
            if not ll_vms.addNic(
                positive=True, vm=cls.vm, name=nic, network=cls.net,
                plugged=plug_state
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3825")
    def test_change_net_param_values(self):
        """
        Check network parameters changes for vNICs
        Change NIC names, update linked/plugged states
        Remove and return network from the VNIC
        """
        for nic, plug_state in zip(self.nic_list, self.plug_states):
            if not ll_vms.get_vm_nic_plugged(
                vm=self.vm, nic=nic, positive=plug_state
            ):
                raise conf.NET_EXCEPTION()

        plug_states = [False, True]
        for nic, name, plug_state in zip(
            self.nic_list, self.nic_names, plug_states
        ):
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic, name=name,
                network=self.net, vnic_profile=self.net, plugged=plug_state
            ):
                raise conf.NET_EXCEPTION()

        for nic, plug_state in zip(self.nic_names, plug_states):
            if not ll_vms.get_vm_nic_plugged(
                vm=self.vm, nic=nic, positive=plug_state
            ):
                raise conf.NET_EXCEPTION()

        for nic_name in self.nic_names:
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic_name, network=self.net,
                vnic_profile=self.net, plugged=False
            ):
                raise conf.NET_EXCEPTION()

        for nic_name in self.nic_names:
            if not ll_vms.getVmNicNetwork(vm=self.vm, nic=nic_name):
                raise conf.NET_EXCEPTION()
            if ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic_name):
                raise conf.NET_EXCEPTION()

        for nic_name, orig_nic in zip(self.nic_names, self.nic_list):
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic_name, name=orig_nic
            ):
                raise conf.NET_EXCEPTION()


@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestLinkedCase06(TestLinkedCasesBase):
    """
    Changing several network parameters at once on non-running VM
    """
    __test__ = True
    vm = conf.VM_NAME[1]
    nic1 = conf.NIC_NAME[1]
    net1 = conf.NETS[1][0]
    net2 = conf.NETS[1][1]
    nic_list = [nic1]
    vprofile = "pm_7_linking"
    name = "vnic2"
    rtl_int = conf.NIC_TYPE_RTL8139
    mac_addr = "12:22:33:44:55:66"

    @classmethod
    def setup_class(cls):
        """
        Create 1 vNIC on non-running VM
        Add vNIC profile with port mirroring to the second network
        """
        if not ll_vms.addNic(
            positive=True, vm=cls.vm, name=cls.nic1, network=cls.net1
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=cls.vprofile, cluster=conf.CL_0,
            network=cls.net2, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3826")
    def test_change_net_param_values(self):
        """
        Change plugged, network and name at once on VNIC of VM
        """
        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nic1, name=self.name,
            network=self.net2, vnic_profile=self.net2, plugged=False
        ):
            raise conf.NET_EXCEPTION()

        if ll_vms.get_vm_nic_plugged(vm=self.vm, nic=self.name):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.name, name=self.nic1,
            network=self.net1, vnic_profile=self.net1, linked=False
        ):
            raise conf.NET_EXCEPTION()

        if ll_vms.get_vm_nic_linked(vm=self.vm, nic=self.nic1):
            raise conf.NET_EXCEPTION()

        if not net_help.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOSTS[0], wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nic1, linked=True,
            plugged=True, network=self.net2, vnic_profile=self.vprofile
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.nic1,
            interface=self.rtl_int, mac_address=self.mac_addr
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nic1, network=self.net2,
            vnic_profile=self.net2, linked=False, plugged=False
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nic1,
            interface=self.rtl_int, mac_address=self.mac_addr
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VM
        Remove vNIC profile
        Stop VM
        """
        super(TestLinkedCase06, cls).teardown_class()
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.vprofile, network=cls.net2
        )
        ll_vms.stopVm(positive=True, vm=cls.vm)
