#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing NetworkFilter feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""
import shlex

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as nf_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import (
    network_filter_prepare_setup, case_03_fixture, case_04_fixture,
    case_05_fixture, case_06_fixture
)


@attr(tier=2)
@pytest.mark.usefixtures(network_filter_prepare_setup.__name__)
class TestNetworkFilterCase01(NetworkTest):
    """
    Check that network filter (vdsm-no-mac-spoofing) is enabled by default for
    new network
    """
    __test__ = True
    net = nf_conf.NETS[1][0]

    @polarion("RHEVM-15078")
    def test_check_default_network_filter_new_net(self):
        """
        Check that network filter (vdsm-no-mac-spoofing) is enabled by default
        for new network
        """
        testflow.step(
            "Check that network filter (vdsm-no-mac-spoofing) is enabled by "
            "default for new network"
        )
        nf_attr_dict = ll_networks.get_vnic_profile_attr(
            name=self.net, network=self.net,
            attr_list=[nf_conf.NETWORK_FILTER_STR]
        )
        nf_res = nf_attr_dict[nf_conf.NETWORK_FILTER_STR]
        assert nf_res == conf.VDSM_NO_MAC_SPOOFING


@attr(tier=2)
@pytest.mark.usefixtures(network_filter_prepare_setup.__name__)
class TestNetworkFilterCase02(NetworkTest):
    """
    Check the vdsm-no-mac-spoofing in on virsh nwfilter-list
    """
    __test__ = True
    vdsm_spoofing_file = "/etc/libvirt/nwfilter/vdsm-no-mac-spoofing.xml"

    @polarion("RHEVM-15096")
    def test_check_network_filter_on_host(self):
        """
        Check the vdsm-no-mac-spoofing in on virsh nwfilter-list
        """
        testflow.step(
            "Check the vdsm-no-mac-spoofing in on virsh nwfilter-list"
        )
        nwfilter_list_cmd = "virsh -r nwfilter-list"
        assert conf.VDSM_NO_MAC_SPOOFING in conf.VDS_0_HOST.run_command(
            shlex.split(nwfilter_list_cmd)
        )[1]

        testflow.step(
            "Verify that file %s exist on VDSM host", self.vdsm_spoofing_file
        )
        assert conf.VDS_0_HOST.fs.listdir(self.vdsm_spoofing_file)

        testflow.step(
            "Verify content of %s", self.vdsm_spoofing_file
        )
        vdsm_spoofing_file_content = conf.VDS_0_HOST.run_command(
            ["cat", self.vdsm_spoofing_file]
        )[1]
        assert (
            "no-mac-spoofing" in vdsm_spoofing_file_content or
            "no-arp-mac-spoofing" in vdsm_spoofing_file_content
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_03_fixture.__name__)
class TestNetworkFilterCase03(NetworkTest):
    """
    Check that Network Filter is enabled for via dumpxml
    """
    __test__ = True
    vm = conf.VM_0
    nic0 = conf.VM_NIC_0
    nic1 = conf.VM_NIC_1
    net = nf_conf.NETS[3][0]

    @polarion("RHEVM-15098")
    def test_01_check_vm_xml_with_network_filter(self):
        """
        Check that Network Filter is enabled for via dumpxml
        """
        testflow.step(
            "Check that Network Filter is enabled for via dumpxml"
        )
        assert ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm, nics="1"
        )

    @polarion("RHEVM-15104")
    def test_02_check_network_filter_via_ebtables(self):
        """
        Check that VM NIC has network filter via ebtables
        """
        vm_macs = hl_vms.get_vm_macs(vm=self.vm, nics=[self.nic0])
        testflow.step("Check ebtables rules for running VM")
        assert ll_hosts.check_network_filtering_ebtables(
            host_obj=conf.VDS_0_HOST, vm_macs=vm_macs
        )

    @polarion("RHEVM-15099")
    def test_03_hot_plug_nic_check_xml(self):
        """
        Hot plug NIC to VM and check that NIC have filter enabled via dump XML
        """
        testflow.step(
            "Check network that filter is enabled vi dump XML for hot-plugged "
            "NIC"
        )
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=self.nic1, network=self.net
        )
        assert ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm, nics="2"
        )

    @polarion("RHEVM-15106")
    def test_04_check_network_filter_via_ebtables_hotplug_nic(self):
        """
        Check that VM NIC has network filter via ebtables for hot-plugged NIC
        """
        vm_macs = hl_vms.get_vm_macs(vm=self.vm, nics=[self.nic1])
        testflow.step("Check ebtables rules for running VM")
        assert ll_hosts.check_network_filtering_ebtables(
            host_obj=conf.VDS_0_HOST, vm_macs=vm_macs
        )

    @polarion("RHEVM-15103")
    def test_05_disable_filter_running_vm(self):
        """
        Disable network filter while VM is running, should apply after VM
        reboot
        """
        testflow.step(
            "Disable network filter while VM is running, and check that "
            "network filter is disabled after VM restart"
        )
        assert ll_networks.update_vnic_profile(
            name=self.net, network=self.net, network_filter="None"
        )
        assert ll_vms.restartVm(vm=self.vm)
        assert not ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm, nics="2"
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_04_fixture.__name__)
class TestNetworkFilterCase04(NetworkTest):
    """
    Remove network filter from vNIC profile while profile attach to stopped VM
    """
    __test__ = True
    nic1 = conf.VM_NIC_1
    vm = conf.VM_0
    net = nf_conf.NETS[4][0]

    @polarion("RHEVM-15102")
    def test_remove_filter_from_profile_vm_down(self):
        """
        Remove network filter from vNIC profile while profile attach to
        not running VM
        """
        testflow.step(
            "Remove network filter from vNIC profile while profile attach to "
            "not running VM"
        )
        assert ll_networks.update_vnic_profile(
            name=self.net, network=self.net, network_filter="None"
        )


@attr(tier=2)
@bz({"1347931": {}})
@pytest.mark.usefixtures(case_05_fixture.__name__)
class TestNetworkFilterCase05(NetworkTest):
    """
    Create new vNIC profile with custom network_filter, no network
    filter and default network filter
    Update vNIC profile with custom network_filter, no network
    filter and default network filter

    """
    __test__ = True
    vnic_pro_1 = nf_conf.VNIC_PROFILES[5][0]
    vnic_pro_2 = nf_conf.VNIC_PROFILES[5][1]
    vnic_pro_3 = nf_conf.VNIC_PROFILES[5][2]

    @polarion("RHEVM-15476")
    def test_01_create_new_vnic_profile(self):
        """
        Create new vNIC profile with custom network_filter, no network
        filter and default network filter
        """
        testflow.step("Create new vNIC profile with default network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_1
        )
        testflow.step("Create new vNIC profile with no network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_2,
            network_filter="None"
        )
        testflow.step("Create new vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_3,
            network_filter=nf_conf.ARP_FILTER
        )

    @polarion("RHEVM-15477")
    def test_02_update_vnic_profile(self):
        """
        Update vNIC profile with custom network_filter, no network
        filter and default network filter
        """
        testflow.step("Update vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            network_filter=nf_conf.ARP_FILTER
        )
        testflow.step("Update vNIC profile without network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            network_filter="None"
        )
        testflow.step(
            "Update vNIC profile without send network profile. network "
            "filter should't update and stay the same"
        )
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1
        )


@attr(tier=2)
@bz({"1347931": {}})
@pytest.mark.usefixtures(case_06_fixture.__name__)
class TestNetworkFilterCase06(NetworkTest):
    """
    Create and update vNIC profile network filter on old datacenter
    Create new vNIC profile with custom network_filter, no network
    filter and default network filter
    Update vNIC profile with custom network_filter, no network
    filter and default network filter
    """
    __test__ = True
    ext_dc = "NF_DC_3_6"
    ext_cl = "NF_CL_3_6"
    vnic_pro_1 = nf_conf.VNIC_PROFILES[6][0]
    vnic_pro_2 = nf_conf.VNIC_PROFILES[6][1]
    vnic_pro_3 = nf_conf.VNIC_PROFILES[6][2]

    @polarion("RHEVM-15109")
    def test_create_update_network_filter_pre_cluster(self):
        testflow.step("Create new vNIC profile with default network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_1, datacenter=self.ext_dc
        )
        testflow.step("Create new vNIC profile with no network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_2, datacenter=self.ext_dc,
            network_filter="None"
        )
        testflow.step("Create new vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_3, datacenter=self.ext_dc,
            network_filter=nf_conf.ARP_FILTER
        )
        testflow.step("Update vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            datacenter=self.ext_dc, network_filter=nf_conf.ARP_FILTER
        )
        testflow.step("Update vNIC profile without network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            datacenter=self.ext_dc, network_filter="None"
        )
        testflow.step(
            "Update vNIC profile without send network profile. network "
            "filter should't update and stay the same"
        )
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            datacenter=self.ext_dc
        )
