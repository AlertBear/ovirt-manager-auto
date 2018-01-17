#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Tests for the vNIC profile feature

The following elements will be used for the tests:
1 DC, 1 Cluster, 1 Hosts and 1 VM
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_networks
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    templates as ll_templates,
    vms as ll_vms
)
import config as vnic_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
from art.core_api import apis_utils
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import (
    remove_vnic_profiles,
    remove_nic_from_template,
    clean_host_interfaces,
    remove_nic_from_vm
)
from rhevmtests.fixtures import start_vm, create_datacenters
from rhevmtests.networking.fixtures import (  # noqa: F401
    create_and_attach_networks,
    remove_all_networks
)


@pytest.mark.incremental
@pytest.mark.usefixtures(create_datacenters.__name__)
class TestVNICProfileCase01(NetworkTest):
    """
    Verify that when creating a specially crafted DC (with specific version and
    management bridge) the new vNIC profile is created with management network
    name
    """
    # create_datacenters params
    dc_name2 = "vnic_profile_DC_35_case01"
    datacenters_dict = {
        dc_name2: {
            "name": dc_name2,
            "version": conf.COMP_VERSION,
        }
    }

    mgmt_br = conf.MGMT_BRIDGE

    @tier2
    @polarion("RHEVM3-3991")
    def test01_check_management_profile(self):
        """
        Check if management vNIC profile is created when creating a new DC
        """
        testflow.step(
            'Check if management vNIC profile is created when creating '
            'a new DC'
        )
        assert ll_networks.get_vnic_profile_obj(
            name=self.mgmt_br, network=self.mgmt_br, data_center=self.dc_name2
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    start_vm.__name__
)
class TestVNICProfileCase02(NetworkTest):
    """
    1.  Verify uniqueness of a vNIC profile
    2.  Update VM network to non-VM
    3.  Remove network
    """
    # General params
    dc = conf.DC_0
    cluster = conf.CL_0
    vm_name = conf.VM_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": vnic_conf.CASE_2_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # start_vm params
    start_vms_dict = {
        vm_name: {}
    }
    # Test-01
    net_1 = vnic_conf.NETS[2][0]
    net_2 = vnic_conf.NETS[2][1]

    # Test-02
    net_3 = vnic_conf.NETS[2][2]

    # Test-03
    net_4 = vnic_conf.NETS[2][3]
    vnic_profile_4 = vnic_conf.VNIC_PROFILES[2][2]

    # Test-04
    net_5 = vnic_conf.NETS[2][4]
    vnic_profile_5 = vnic_conf.VNIC_PROFILES[2][3]

    # Test-05
    net_6 = vnic_conf.NETS[2][5]
    net_7 = vnic_conf.NETS[2][6]
    net_8 = vnic_conf.NETS[2][7]

    # Test-06
    net_9 = vnic_conf.NETS[2][8]

    # Test-07
    net_10 = vnic_conf.NETS[2][9]
    net_11 = vnic_conf.NETS[2][10]
    vnic_profile_10 = vnic_conf.VNIC_PROFILES[2][6]
    vnic_profile_10_2 = vnic_conf.VNIC_PROFILES[2][7]

    # Test-08
    net_12 = vnic_conf.NETS[2][11]
    net_13 = vnic_conf.NETS[2][12]
    vnic_2 = vnic_conf.VNICS[2][2]
    vnic_3 = vnic_conf.VNICS[2][3]

    # Test-09
    net_14 = vnic_conf.NETS[2][13]

    # Test-09, Test-10, Test-11
    net_15 = vnic_conf.NETS[2][14]

    # Test-11
    net_17 = vnic_conf.NETS[2][16]
    net_18 = vnic_conf.NETS[2][17]
    vnic_profile_17 = vnic_conf.VNIC_PROFILES[2][10]
    vnic_profile_17_2 = vnic_conf.VNIC_PROFILES[2][11]

    # Test-06, Test-07, Test-10, Test-11, Test-12
    vnic = vnic_conf.VNICS[2][0]

    @tier2
    @polarion("RHEVM3-3973")
    def test_01_create_new_profiles(self):
        """
        1.  Create a profile for sw2 with the same name as sw1
        2.  Create profile with the same name for the same network (negative)
        """
        testflow.step('Create a profile for sw2 with the same name as sw1')
        assert ll_networks.add_vnic_profile(
            positive=True, name=self.net_1, data_center=self.dc,
            network=self.net_2
        )
        testflow.step(
            'Create profile with the same name for the same network (negative)'
        )
        assert ll_networks.add_vnic_profile(
            positive=False, name=self.net_1, data_center=self.dc,
            network=self.net_2
        )

    @tier2
    @polarion("RHEVM3-3989")
    def test_02_update_to_non_vm(self):
        """
        1.  Update VM network to non-VM network
        2.  Check that both vNIC profiles of the network were removed as a
            result of changing the state of the network to non-VM
        """
        assert ll_networks.update_network(
            positive=True, network=self.net_3, usages=""
        )
        testflow.step(
            'Check that both vNIC profiles of the network were removed as a '
            'result of changing the state of the network to non-VM (negative)'
        )
        assert not ll_networks.get_network_vnic_profiles(
            network=self.net_3, data_center=self.dc
        )

    @tier2
    @polarion("RHEVM3-3990")
    def test_03_remove_network(self):
        """
        1.  Add a new vNIC profile
        2.  Verify that it was created successfully
        3.  Remove the network attached to the vNIC profile
        4.  Check that both vNIC profiles of the network were removed as a
            result of network removal
        """

        testflow.step('Add a new vNIC profile')
        assert ll_networks.add_vnic_profile(
            positive=True, name=self.vnic_profile_4, data_center=self.dc,
            network=self.net_4
        )
        testflow.step('Verify that is was created successfully')
        for profile in [self.net_4, self.vnic_profile_4]:
            assert ll_networks.is_vnic_profile_exist(
                vnic_profile_name=profile
            )
        testflow.step('Remove the network attached to the vNIC profile')
        assert ll_networks.remove_network(
            positive=True, network=self.net_4, data_center=self.dc
        )
        testflow.step(
            'Check that both vNIC profiles of the network were removed as a '
            'result of network removal'
        )
        for profile in [self.net_4, self.vnic_profile_4]:
            assert not ll_networks.is_vnic_profile_exist(
                vnic_profile_name=profile
            )

    @tier2
    @polarion("RHEVM3-3972")
    def test_04_check_non_vm(self):
        """
        1.  Check no vNIC profile exists for non-VM network
        2.  Check you can't create vNIC profile for non-VM network
        """
        testflow.step(
            'Check no vNIC profile exists for non-VM network (negative)'
        )
        assert not ll_networks.get_network_vnic_profiles(
            network=self.net_5, data_center=self.dc
        )
        testflow.step(
            'Check you can''t create vNIC profile for non-VM network '
            '(negative)'
        )
        assert ll_networks.add_vnic_profile(
            positive=False, name=self.vnic_profile_5, data_center=self.dc,
            network=self.net_5
        )

    @tier2
    @polarion("RHEVM3-3978")
    def test_05_check_profile(self):
        """"
        1.  Check that vNIC profile exists for VM network
        2.  Check that vNIC profile doesn't exist for non-VM network
        3.  Check that vNIC profile doesn't exist for network with the flag
            profile_required set to false
        """
        testflow.step('Check that vNIC profile exists for VM network')
        assert ll_networks.get_network_vnic_profiles(
            network=self.net_6, data_center=self.dc
        )
        testflow.step(
            'Check that vNIC profile doesn''t exist for non-VM network'
        )
        assert not ll_networks.get_network_vnic_profiles(
            network=self.net_7, data_center=self.dc
        )
        testflow.step(
            'Check that vNIC profile doesn''t exist for network with the flag '
            'profile_required set to false'
        )
        assert not ll_networks.get_network_vnic_profiles(
            network=self.net_8, data_center=self.dc
        )

    @tier2
    @polarion("RHEVM3-3995")
    def test_06_check_profile(self):
        """"
        1.  Check that vNIC profile exists for VM network
        2.  Check that you can't add vNIC profile to VM if its network is not
            attached to the host
        """
        testflow.step('Check that vNIC profile exists for VM network')
        assert ll_networks.get_network_vnic_profiles(
            network=self.net_9, data_center=self.dc
        )
        testflow.step(
            'Check that you can''t add vNIC profile to VM if its network is '
            'not attached to the host'
        )
        assert ll_vms.addNic(
            positive=False, vm=self.vm_name, name=self.vnic,
            network=self.net_9, vnic_profile=self.net_9
        )

    @tier2
    @polarion("RHEVM3-3981")
    def test_07_update_network_unplugged_nic(self):
        """
        1.  Update vNIC profile on nic2 with profile from different network
        2.  Update vNIC profile on nic2 with profile from the same network
        3.  Update vNIC profile on nic2 with profile from the same network,
            but with port mirroring enabled
        4.  Update vNIC profile on nic2 with profile having port mirroring
            enabled to different network with port mirroring disabled
        5.  Remove vNIC from VM
        6.  Clean host interfaces
        """
        vnic_conf.HOST_NAME = ll_vms.get_vm_host(vm_name=self.vm_name)
        assert vnic_conf.HOST_NAME
        vnic_conf.HOST_NICS = global_helper.get_host_resource_by_name(
            host_name=vnic_conf.HOST_NAME
        ).nics
        assert vnic_conf.HOST_NICS

        network_setup = {
            "add": {
                "1": {
                    "network": self.net_10,
                    "nic": vnic_conf.HOST_NICS[1]
                },
                "2": {
                    "network": self.net_11,
                    "nic": vnic_conf.HOST_NICS[1]
                }
            }
        }
        assert hl_host_networks.setup_networks(
            host_name=vnic_conf.HOST_NAME, **network_setup
        )
        for vpro in [self.vnic_profile_10, self.vnic_profile_10_2]:
            port_mirroring = True if vpro == self.vnic_profile_10_2 else False
            assert ll_networks.add_vnic_profile(
                positive=True, name=vpro, data_center=self.dc,
                network=self.net_11, port_mirroring=port_mirroring
            )
        assert ll_vms.addNic(
            positive=True, vm=self.vm_name, name=self.vnic,
            network=self.net_10, plugged="false"
        )

        testflow.step(
            'Update vNIC profile on nic2 with profile from different network'
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_11,
            vnic_profile=self.vnic_profile_10
        )
        testflow.step(
            'Update vNIC profile on nic2 with profile from the same network'
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_11,
            vnic_profile=self.net_11
        )
        testflow.step(
            'Update vNIC profile on nic2 with profile from the same network, '
            'but with port mirroring enabled'
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_11,
            vnic_profile=self.vnic_profile_10_2
        )
        testflow.step(
            'Update vNIC profile on nic2 with profile having port mirroring '
            'enabled to different network with port mirroring disabled'
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_10,
            vnic_profile=self.net_10
        )
        testflow.step('Remove vNIC from VM')
        assert ll_vms.removeNic(positive=True, vm=self.vm_name, nic=self.vnic)
        assert hl_host_networks.clean_host_interfaces(
            host_name=vnic_conf.HOST_NAME
        )

    @tier2
    @polarion("RHEVM3-3976")
    def test_08_update_vnic_profile(self):
        """
        1.  Update vNIC profile on nic2 to have port mirroring enabled
        2.  Update vNIC profile on nic3 to have port mirroring disabled
        3.  Remove vNICs from VM
        4.  Clean host interfaces
        """
        network_setup = {
            "add": {
                "1": {
                    "network": self.net_12,
                    "nic": vnic_conf.HOST_NICS[1]
                },
                "2": {
                    "network": self.net_13,
                    "nic": vnic_conf.HOST_NICS[1]
                }
            }
        }
        assert hl_host_networks.setup_networks(
            host_name=vnic_conf.HOST_NAME, **network_setup
        )
        testflow.step(
            'Update vNIC profile on nic2 to have port mirroring enabled'
        )
        assert ll_networks.update_vnic_profile(
            name=self.net_13, network=self.net_13, port_mirroring=True
        )
        for nic, net in zip(
            [self.vnic_2, self.vnic_3], [self.net_12, self.net_13]
        ):
            assert ll_vms.addNic(
                positive=True, vm=self.vm_name, name=nic, network=net
            )
        testflow.step(
            'Update vNIC profile on nic3 to have port mirroring disabled'
        )
        for net, state in zip([self.net_12, self.net_13], [True, False]):
            assert not ll_networks.update_vnic_profile(
                name=net, network=self.net_12, port_mirroring=state
            )
        testflow.step('Remove vNICs from VM')
        for nic in [self.vnic_2, self.vnic_3]:
            assert ll_vms.updateNic(
                positive=True, vm=self.vm_name, nic=nic, plugged="false"
            )
            assert ll_vms.removeNic(positive=True, vm=self.vm_name, nic=nic)

        assert hl_host_networks.clean_host_interfaces(
            host_name=vnic_conf.HOST_NAME
        )

    @tier2
    @polarion("RHEVM3-3975")
    def test_09_update_profiles(self):
        """
        Try to update network for existing profile (negative)
        """
        testflow.step('Try to update network for existing profile (negative)')
        assert not ll_networks.update_vnic_profile(
            name=self.net_14, network=self.net_14, cluster=self.cluster,
            new_network=self.net_15
        )

    @tier2
    @polarion("RHEVM3-3987")
    def test_10_hotplug_link_unlink(self):
        """
        1.  Hotplug vNIC profile to the VMs nic2
        2.  Unlink nic2
        3.  Link nic2
        """
        network_setup = {
            "add": {
                "1": {
                    "network": self.net_15,
                    "nic": vnic_conf.HOST_NICS[1]
                }
            }
        }
        assert hl_host_networks.setup_networks(
            host_name=vnic_conf.HOST_NAME, **network_setup
        )
        testflow.step('Hotplug vNIC profile to the VMs nic2')
        assert ll_vms.addNic(
            positive=True, vm=self.vm_name, name=self.vnic,
            network=self.net_15, plugged="true"
        )
        testflow.step('Unlink nic2')
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=ll_vms.updateNic,
            positive=True, vm=self.vm_name, nic=self.vnic, linked="false"
        )
        assert sample.waitForFuncStatus(result=True)
        testflow.step('Link nic2')
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, linked="true"
        )

    @tier2
    @polarion("RHEVM3-3985")
    @pytest.mark.usefixtures(clean_host_interfaces.__name__)
    def test_11_remove_used_profile(self):
        """
        1.  Try to remove vNIC profile while VM is using it (negative)
        2.  Unplug vNIC from the VM
        3.  Remove vNIC from the VM
        """
        testflow.step(
            'Try to remove vNIC profile while VM is using it (negative)'
        )
        assert ll_networks.remove_vnic_profile(
            positive=False, vnic_profile_name=self.net_15, network=self.net_15
        )
        testflow.step('2. Unplug vNIC from the VM')
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, plugged="false"
        )
        testflow.step('3. Remove vNIC from the VM')
        assert ll_vms.removeNic(positive=True, vm=self.vm_name, nic=self.vnic)

    @tier2
    @polarion("RHEVM3-3986")
    @pytest.mark.usefixtures(
        remove_nic_from_vm.__name__,
        clean_host_interfaces.__name__
    )
    def test_12_update_network_plugged_nic(self):
        """
        1.  Update vNIC profile on nic2 with profile from different network
        2.  Update vNIC profile on nic2 with profile from the same network
        3.  Try to update vNIC profile on nic2 with profile from the same
            network but with port mirroring enabled (negative case)
        4.  Update vNIC profile on nic2 with empty profile
        5.  Update vNIC profile on nic2 with profile having port mirroring
            enabled (first unplug and after the action plug nic2)
        6.  Try to update vNIC profile on nic2 with profile from the same
            network but with port mirroring disabled (negative case)
        """
        network_setup = {
            "add": {
                "1": {
                    "network": self.net_17,
                    "nic": vnic_conf.HOST_NICS[1]
                },
                "2": {
                    "network": self.net_18,
                    "nic": vnic_conf.HOST_NICS[1]
                }
            }
        }
        assert hl_host_networks.setup_networks(
            host_name=vnic_conf.HOST_NAME, **network_setup
        )
        for vpro in [self.vnic_profile_17, self.vnic_profile_17_2]:
            port_mirroring = True if vpro == self.vnic_profile_17_2 else False
            assert ll_networks.add_vnic_profile(
                positive=True, name=vpro, data_center=self.dc,
                network=self.net_18, port_mirroring=port_mirroring
            )
        assert ll_vms.addNic(
            positive=True, vm=self.vm_name, name=self.vnic,
            network=self.net_17, plugged="true"
        )
        testflow.step(
            'Update vNIC profile on nic2 with profile from different network'
        )
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=ll_vms.updateNic,
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_18,
            vnic_profile=self.vnic_profile_17
        )
        assert sample.waitForFuncStatus(result=True)
        testflow.step(
            'Update vNIC profile on nic2 with profile from the same network'
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_18,
            vnic_profile=self.net_18
        )
        testflow.step(
            'Try to update vNIC profile on nic2 with profile from the same '
            'network but with port mirroring enabled (negative case)'
        )
        assert ll_vms.updateNic(
            positive=False, vm=self.vm_name, nic=self.vnic,
            network=self.net_18, vnic_profile=self.vnic_profile_17_2
        )
        testflow.step('Update vNIC profile on nic2 with empty profile')
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=None
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, plugged="false"
        )
        testflow.step(
            'Update vNIC profile on nic2 with profile having port mirroring '
            'enabled (first unplug and after the action plug nic2)'
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, network=self.net_18,
            vnic_profile=self.vnic_profile_17_2
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, plugged="true"
        )
        testflow.step(
            'Try to update vNIC profile on nic2 with profile from the same '
            'network but with port mirroring disabled (negative case)'
        )
        assert ll_vms.updateNic(
            positive=False, vm=self.vm_name, nic=self.vnic,
            network=self.net_18, vnic_profile=self.vnic_profile_17
        )
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vnic, plugged="false"
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    remove_vnic_profiles.__name__,
    remove_nic_from_template.__name__
)
class TestVNICProfileCase03(NetworkTest):
    """
    vNIC Profile on template
    """
    # General params
    dc = conf.DC_NAME[0]
    mgmt = conf.MGMT_BRIDGE
    vm_name2 = "new_VM_case03"
    cluster = conf.CLUSTER_NAME[0]

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": vnic_conf.CASE_3_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # Test-01, Test-02
    net_1 = vnic_conf.NETS[3][0]
    vnic_1 = vnic_conf.VNIC_PROFILES[3][1]
    template = conf.TEMPLATE_NAME[0]

    # Test-01
    vnic_2 = vnic_conf.VNIC_PROFILES[3][2]

    @tier2
    @polarion("RHEVM3-3993")
    def test01_create_new_profiles_template(self):
        """
        1.  Check that you can create non-empty vNIC profile on Template
        2.  Check that you can create empty vNIC profile on Template
        3.  Create VM from the template with empty and non-empty profiles
        4.  Make sure this VM has empty and non-empty profiles on it's NIC's
        """
        testflow.step(
            'Check that you can create non-empty vNIC profile on Template'
        )
        assert ll_templates.addTemplateNic(
            positive=True, template=self.template, name=self.vnic_1,
            data_center=self.dc, network=self.net_1
        )
        testflow.step(
            'Check that you can create empty vNIC profile on Template'
        )
        assert ll_templates.addTemplateNic(
            positive=True, template=self.template, name=self.vnic_2,
            data_center=self.dc, network=None
        )
        testflow.step(
            'Create VM from the template with empty and non-empty profiles'
        )
        assert ll_vms.createVm(
            positive=True, vmName=self.vm_name2, vmDescription="",
            cluster=self.cluster, template=self.template, network=self.mgmt
        )
        testflow.step(
            'Make sure this VM has empty and non-empty profiles on it''s '
            'NIC''s'
        )
        for vpro, nic in zip([self.net_1, None], [self.vnic_1, self.vnic_2]):
            assert ll_vms.check_vm_nic_profile(
                vm=self.vm_name2, vnic_profile_name=vpro, nic=nic
            )

    @tier2
    @polarion("RHEVM3-3977")
    def test02_remove_new_profiles_template(self):
        """
        1.  Remove VM created from the previous test
        2.  Try to remove network when template is using its vNIC profile.
            This test is the negative one
        3.  Remove vNIC profile from the template
        4.  Remove vNIC profile from the setup
        """
        testflow.step('Remove VM created from the previous test')
        assert ll_vms.removeVm(positive=True, vm=self.vm_name2)
        testflow.step(
            'Try to remove network when template is using its vNIC profile. '
            'This test is the negative one'
        )
        assert ll_networks.remove_network(
            positive=False, network=self.net_1, data_center=self.dc
        )
        testflow.step('Remove vNIC profile from the template')
        assert ll_templates.removeTemplateNic(
            positive=True, template=self.template, nic=self.vnic_1
        )
        testflow.step('Remove vNIC profile from the setup')
        assert ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=self.net_1, network=self.net_1
        )
