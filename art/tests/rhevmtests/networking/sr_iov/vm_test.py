# #! /usr/bin/python
# # -*- coding: utf-8 -*-
#
"""
SR_IOV feature tests for VFs on VM
"""

import pytest

import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sriov_conf
import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_utils
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    reset_host_sriov_params, update_vnic_profiles, add_vnics_to_vm,
    init_fixture, prepare_setup_vm, set_num_of_vfs, create_qos, update_qos,
    add_labels, add_vnic_profile, set_all_networks_allowed,
    set_ip_on_vm_interface
)
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import setup_networks_fixture
from rhevmtests.networking.fixtures import clean_host_interfaces  # noqa: F401


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    reset_host_sriov_params.__name__,
    init_fixture.__name__,
    prepare_setup_vm.__name__,
    update_vnic_profiles.__name__,
    add_vnics_to_vm.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovVm01(NetworkTest):
    """
    Cases for VFs on VM
    """
    __test__ = True

    # General
    vm = conf.VM_0
    extra_vm = conf.VM_1
    vm_nic = sriov_conf.VM_TEST_VNICS[1][0]
    extra_vm_nic = sriov_conf.VM_TEST_VNICS[1][1]
    net_1 = sriov_conf.VM_NETS[1][0]
    net_2 = sriov_conf.VM_NETS[1][1]

    # stop VM
    vms_to_stop = [vm]

    # update_vnic_profiles
    vnics_profiles = {
        net_1: {
            "pass_through": True
        },
        net_2: {
            "pass_through": True
        },
    }

    # add_vnics_to_vm
    pass_through_vnic = [True]
    profiles = [net_1]
    nets = profiles
    nics = [vm_nic, extra_vm_nic]

    @polarion("RHEVM3-6614")
    def test_01_run_vm_zero_vfs(self):
        """
        Try to run VM when there are zero VFs
        """
        testflow.step("Try to run VM when there are zero VFs")
        assert not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )

    @polarion("RHEVM3-10628")
    def test_02_change_vf_num_for_occupied_vf_on_vm(self):
        """
        Create one VF and run VM (using that VF)
        Try to change the number of VFs and fail when the only VF is occupied
        """
        assert sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(1)
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )
        testflow.step(
            "Negative: Try to change the number of VFs when one of the VFs is "
            "occupied by VM NIC"
        )
        assert not sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(2)

    @polarion("RHEVM3-10653")
    def test_03_check_mac_of_vf_on_vm(self):
        """
        Check the same MAC address exists on VF attached to VM in engine and
        in vm appropriate file
        """
        mac_addr = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=self.vm_nic)
        vm_resource = global_helper.get_vm_resource(vm=self.vm)
        vm_interfaces = vm_resource.network.all_interfaces()
        testflow.step(
            "Check the same MAC address exists on VF attached to VM "
            "in the engine and in vm's appropriate file"
        )
        assert mac_addr in [
            vm_resource.run_command(
                ["cat", sriov_conf.MAC_ADDR_FILE % i]
            )[1].strip() for i in vm_interfaces
            ]

    @polarion("RHEVM3-10663")
    def test_04_run_vm_occupied_vfs(self):
        """
        Add vNIC to the second VM
        Try to run second VM when there is only one VF that is already
        occupied by the first VM
        Remove vNIC from VM
        """
        assert ll_vms.addNic(
            positive=True, vm=self.extra_vm, name=self.vm_nic,
            network=self.net_2, interface=conf.PASSTHROUGH_INTERFACE
        )
        testflow.step(
            "Try to run a second VM when there is only one VF that is already"
            "occupied by the first VM"
        )
        assert not network_helper.run_vm_once_specific_host(
            vm=self.extra_vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )
        assert ll_vms.removeNic(
            positive=True, vm=self.extra_vm, nic=self.vm_nic
        )

    @polarion("RHEVM3-14596")
    def test_05_check_no_vf_on_host_while_run_vm(self):
        """
        Check that the VF disappeared when VM is using it
        """
        testflow.step(
            "Check that the number of VFs was decreased by 1 under %s PF when "
            "VM was running",
            sriov_conf.HOST_0_PF_OBJECT.nic_name
        )
        assert not sriov_conf.HOST_0_PF_OBJECT.get_all_vf_names()

    @polarion("RHEVM3-14638")
    def test_06_check_vf_exists_when_vm_is_down(self):
        """
        Stop VM
        Check that the VF is back to the host after stopping VM that use the VF
        """
        testflow.step("Stop VM and check that there is 1 VF")
        assert ll_vms.stopVm(positive=True, vm=self.vm)
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=lambda: len(
                sriov_conf.HOST_0_PF_OBJECT.get_all_vf_names()
            ) == 1
        )
        assert sample.waitForFuncStatus(result=True)

    @polarion("RHEVM3-14638")
    def test_07_change_vf_num_non_occupied_vfs(self):
        """
        Change the number of VFs and succeed
        """
        testflow.step("Change the number of VFs and succeed")
        assert sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(3)

    @polarion("RHEVM3-14595")
    def test_08_check_vf_while_passthrough_attached_to_non_running_vm(self):
        """
        Check that set number of VF is working while pass-through network
        reside on non running VM
        """
        testflow.step(
            "Check that set number of VF is working while pass-through "
            "network reside on non running VM"
        )
        assert sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(4)

    @polarion("RHEVM3-6316")
    def test_09_hotplug_hotunplug(self):
        """
        Start VM
        Hotunplug vNIC with passthrough profile
        Hotplug new vNIC profile with passthrough property
        Try to edit vNIC profile with passthrough property to be virtIO
        """
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )
        last_event = ll_events.get_last_event(
            code=sriov_conf.REFRESH_CAPS_CODE
        )
        testflow.step("Hotunplug vNIC with passthrough profile")
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vm_nic, plugged="false"
        )
        assert helper.wait_for_refresh_caps(last_event=last_event)
        testflow.step(
            "Hotplug new vNIC profile with passthrough property"
        )
        last_event = ll_events.get_last_event(
            code=sriov_conf.REFRESH_CAPS_CODE
        )
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=self.extra_vm_nic,
            network=self.net_2, vnic_profile=self.net_2,
            interface=conf.PASSTHROUGH_INTERFACE
        )
        assert helper.wait_for_refresh_caps(last_event=last_event)
        testflow.step(
            "Try to edit vNIC profile with passthrough property to be virtIO"
        )
        assert ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.extra_vm_nic,
            interface=conf.INTERFACE_VIRTIO
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    reset_host_sriov_params.__name__,
    init_fixture.__name__,
    prepare_setup_vm.__name__,
    set_num_of_vfs.__name__,
    update_vnic_profiles.__name__,
    add_vnics_to_vm.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovVm02(NetworkTest):
    """
    Test run VM with VLAN
    """
    __test__ = True

    # General
    vm = conf.VM_0
    vm_nic = sriov_conf.VM_TEST_VNICS[2][0]
    net_1 = sriov_conf.VM_NETS[2][0]
    vlan_id = sriov_conf.VLAN_IDS[2]
    dc = conf.DC_0

    # remove_vnics_from_vm
    nics = [vm_nic]

    # set_num_of_vfs
    num_of_vfs = 1

    # update_vnic_profiles
    vnics_profiles = {
        net_1: {
            "pass_through": True
        },
    }

    # add_vnics_to_vm
    pass_through_vnic = [True]
    profiles = [net_1]
    nets = profiles

    # start_vm
    start_vms_dict = {
        vm: {}
    }

    @polarion("RHEVM3-6314")
    def test_01_vm_with_vlan(self):
        """
        Check that VLAN tag passed to virsh XML
        """
        vlan_from_xml = helper.get_vlan_id_from_vm_xml(vm=self.vm)
        testflow.step("Check that VLAN tag passed to virsh XML")
        err_log = "VLAN tag on XML is %s but should be %s" % (
            vlan_from_xml, self.vlan_id
        )
        assert vlan_from_xml == self.vlan_id, err_log


@attr(tier=2)
@pytest.mark.usefixtures(
    reset_host_sriov_params.__name__,
    init_fixture.__name__,
    set_num_of_vfs.__name__,
    prepare_setup_vm.__name__,
    create_qos.__name__,
    update_qos.__name__,
    update_vnic_profiles.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vm.__name__,
    start_vm.__name__
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovVm03(NetworkTest):
    """
    Try to edit vNIC to be passthrough interface when it has regular profile
    Try to add passthrough vNIC to virtIO interface
    Run VM with passthrough, port mirroring and network QoS profiles
    """
    __test__ = True

    # update_vnic_profile_and_qos
    net_2 = sriov_conf.VM_NETS[3][1]
    net_3 = sriov_conf.VM_NETS[3][2]
    net_qos = sriov_conf.NETWORK_QOS
    dc = conf.DC_0

    # General
    vm = conf.VM_0
    vm_nic_1 = sriov_conf.VM_TEST_VNICS[3][0]
    vm_nic_2 = sriov_conf.VM_TEST_VNICS[3][1]
    vm_nic_3 = sriov_conf.VM_TEST_VNICS[3][2]
    vm_nic_4 = sriov_conf.VM_TEST_VNICS[3][3]
    net_1 = sriov_conf.VM_NETS[3][0]
    net_4 = sriov_conf.VM_NETS[3][3]
    net_list = [net_1, net_2, net_3]

    # stop VM
    vms_to_stop = [vm]

    # set_num_of_vfs
    num_of_vfs = 1

    # add_vnics_to_vm
    pass_through_vnic = [True, False, False]
    profiles = net_list
    vms = [conf.VM_0, conf.VM_0, conf.VM_0]
    nics = [vm_nic_1, vm_nic_2, vm_nic_3]

    # create_qos
    nets = net_list

    # update_vnic_profiles
    vnics_profiles = {
        net_1: {
            "pass_through": True
        },
        net_2: {
            "port_mirroring": True
        },
        net_4: {
            "pass_through": True
        }
    }

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            net_2: {
                "nic": 1,
                "network": net_2,
            },
            net_3: {
                "nic": 1,
                "network": net_3,
            }
        }
    }

    @polarion("RHEVM3-10632")
    def test_01_edit_interface_passthrough(self):
        """
        Try to edit vNIC with regular profile to become passthrough interface
        """
        testflow.step(
            "Try to edit vNIC with regular profile to become passthrough "
            "interface"
        )
        assert ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vm_nic_2,
            interface=conf.PASSTHROUGH_INTERFACE
        )

    @polarion("RHEVM3-6552")
    def test_02_add_passthroug_vnic_incomp_interface(self):
        """
        Try to add passthrough vNIC to the interface with virtIO type
        """
        testflow.step(
            "Try to add passthrough vNIC to the interface with virtIO type"
        )
        assert ll_vms.addNic(
            positive=False, vm=self.vm, name=self.vm_nic_4,
            network=self.net_4, vnic_profile=self.net_4
        )

    @polarion("RHEVM3-10631")
    def test_03_run_multiple_vnics(self):
        """
        Run VM with different types of vNIC profile
        """
        testflow.step("Run VM with different types of vNIC profile")
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    reset_host_sriov_params.__name__,
    init_fixture.__name__,
    set_all_networks_allowed.__name__,
    add_vnics_to_vm.__name__,
    set_num_of_vfs.__name__,
    prepare_setup_vm.__name__,
    update_vnic_profiles.__name__,
    add_labels.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovVm04(NetworkTest):
    """
    Allowed networks and labels
    """
    __test__ = True

    # General
    vm = conf.VM_0
    net_1 = sriov_conf.VM_NETS[4][0]
    net_2 = sriov_conf.VM_NETS[4][1]
    net_3 = sriov_conf.VM_NETS[4][2]
    net_4 = sriov_conf.VM_NETS[4][3]
    label_1 = sriov_conf.LABELS[4][0]
    label_2 = sriov_conf.LABELS[4][1]

    # remove_vnics_from_vm
    nics = sriov_conf.VM_TEST_VNICS[4][:1]
    add_vm_nic = False

    # set_num_of_vfs
    num_of_vfs = 1

    # add_labels
    net_list = [net_1, net_3, net_2, net_4]
    label_list = [label_1, label_2]

    # update_vnic_profiles
    vnics_profiles = {
        net_1: {
            "pass_through": True
        },
        net_2: {
            "pass_through": True
        },
        net_3: {
            "pass_through": True
        },
        net_4: {
            "pass_through": True
        },
    }

    # stop VM
    vms_to_stop = [vm]

    @polarion("RHEVM3-14640")
    def test_01_all_networks_allowed_specific_net_negative(self):
        """
        Add vNIC to VM
        Try to run VM with network not specified in all_networks_allowed
        """
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=self.nics[0],
            network=self.net_1, interface=conf.PASSTHROUGH_INTERFACE
        )
        testflow.step(
            "Try to run a VM with network not specified in "
            "all_networks_allowed"
        )
        assert not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )

    @polarion("RHEVM3-14639")
    def test_02_all_networks_allowed_specific_label_negative(self):
        """
        Update vNIC to VM
        Try to run VM with label not specified in all_networks_allowed
        """
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nics[0], network=self.net_2,
            interface=conf.PASSTHROUGH_INTERFACE
        )
        testflow.step(
            "Try to run VM with label not specified in all_networks_allowed"
        )
        assert not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )

    @polarion("RHEVM3-9373")
    def test_03_all_networks_allowed_specific_net(self):
        """
        Update vNIC to VM
        Add network to all_networks_allowed
        Run VM
        """
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nics[0], network=self.net_3,
            interface=conf.PASSTHROUGH_INTERFACE
        )
        sriov_conf.HOST_0_PF_OBJECT.add_network_to_allowed_networks(
            network=self.net_3
        )
        testflow.step(
            "Add network to all_networks_allowed and run VM"
        )
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )
        testflow.step("Stop VM %s", self.vm)
        assert ll_vms.stop_vms_safely(vms_list=[self.vm])

    @polarion("RHEVM3-10627")
    def test_04_all_networks_allowed_specific_label(self):
        """
        Update vNIC to VM
        Set all_networks_allowed to specific label
        Run VM
        """
        assert ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.nics[0], network=self.net_4,
            interface=conf.PASSTHROUGH_INTERFACE
        )
        assert sriov_conf.HOST_0_PF_OBJECT.add_label_to_allowed_labels(
            label=self.label_2
        )
        testflow.step(
            "Set all_networks_allowed to specific label and run VM"
        )
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    reset_host_sriov_params.__name__,
    set_num_of_vfs.__name__,
    add_vnic_profile.__name__,
    add_vnics_to_vm.__name__,
    start_vm.__name__,
    set_ip_on_vm_interface.__name__
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovVm05(NetworkTest):
    """
    Check connectivity between VMs using VF and bridge vNICs
    """
    __test__ = True

    # General
    vm_1 = conf.VM_0
    vm_2 = conf.VM_1

    # set_num_of_vfs
    num_of_vfs = 1

    # add_vnic_profile
    net_1 = conf.MGMT_BRIDGE
    port_mirroring = [False, False]

    # add_vnics_to_vm
    nics = [sriov_conf.VM_TEST_VNICS[5][0], sriov_conf.VM_TEST_VNICS[5][0]]
    nets = [conf.MGMT_BRIDGE, conf.MGMT_BRIDGE]
    vms = [vm_1, vm_2]
    profiles = ["mgmt_passthrough", "mgmt_vitio"]
    pass_through_vnic = [True, False]

    # start_vm
    start_vms_dict = {
        vm_1: {
            "host": 0
        },
        vm_2: {
            "host": 1
        }
    }

    # set_ip_on_vm_interface
    ips = sriov_conf.IPS[:2]

    @polarion("RHEVM3-6728")
    def test_check_connectivity(self):
        """
        Ping between VMs using VF and bridge vNICs
        """
        vm_resource = global_helper.get_vm_resource(vm=self.vm_1)
        assert vm_resource.network.send_icmp(dst=sriov_conf.IPS[1])
