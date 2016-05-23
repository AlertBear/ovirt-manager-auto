#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing VNIC profile feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_utils
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import NetworkTest
from art.unittest_lib import attr
from rhevmtests import networking

logger = logging.getLogger("VNIC_Profile_Cases")


def setup_module():
    """
    Initialize params
    Network cleanup
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    networking.network_cleanup()


class VnicProfilePrepareSetup(object):
    """
    Prepare setup
    """
    def prepare_networks(self):
        """
        Prepare networks on setup
        """
        network_helper.prepare_networks_on_setup(
            networks_dict=conf.NETS_DICT, dc=conf.DC_0, cluster=conf.CL_0
        )

    def run_vm(self):
        """
        Run VM
        """
        if not network_helper.run_vm_once_specific_host(
            vm=conf.VM_0, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    def stop_vm(self):
        """
        Stop VM
        """
        ll_vms.stopVm(positive=True, vm=conf.VM_0)

    def remove_networks(self):
        """
        Remove networks from setup
        """
        network_helper.remove_networks_from_setup()
        networking.remove_unneeded_vnic_profiles()


@pytest.fixture(scope="module")
def vnic_profile_prepare_setup(request):
    """
    Prepare setup for vNIC profile tests

    Prepare networks -> Remove networks
    Run VM -> Stop VM
    """
    ps = VnicProfilePrepareSetup()

    def fin2():
        """
        Finalizer for remove networks
        """
        ps.remove_networks()
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for stop VM
        """
        ps.stop_vm()
    request.addfinalizer(fin1)

    ps.prepare_networks()
    ps.run_vm()


@attr(tier=2)
class TestVNICProfileCase01(NetworkTest):
    """
    Verify that when creating the new DC the new VNIC profile is created
    with management network name
    """
    __test__ = True
    dc_name2 = "vnic_profile_DC_35_case01"
    mgmt_br = conf.MGMT_BRIDGE
    dc_ver = conf.COMP_VERSION
    storage_type = conf.STORAGE_TYPE

    @classmethod
    def setup_class(cls):
        """
        Create new DC
        """
        if not ll_datacenters.addDataCenter(
            positive=True, name=cls.dc_name2, version=cls.dc_ver,
            storage_type=cls.storage_type
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3991")
    def test_check_management_profile(self):
        """
        Check management VNIC profile is created when creating the new DC
        """
        ll_networks.get_vnic_profile_obj(
            name=self.mgmt_br, network=self.mgmt_br, data_center=self.dc_name2
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove DC from the setup.
        """
        ll_datacenters.remove_datacenter(
            positive=True, datacenter=cls.dc_name2
        )


@attr(tier=2)
@pytest.mark.usefixtures("vnic_profile_prepare_setup")
class TestVNICProfileCase02(NetworkTest):
    """
    Verify uniqueness of VNIC profile
    Update VM network to non-VM
    Remove network
    """
    __test__ = True
    net_1 = conf.NETS[2][0]
    net_2 = conf.NETS[2][1]
    net_3 = conf.NETS[2][2]
    net_4 = conf.NETS[2][3]
    net_5 = conf.NETS[2][4]
    net_6 = conf.NETS[2][5]
    net_7 = conf.NETS[2][6]
    net_8 = conf.NETS[2][7]
    net_9 = conf.NETS[2][8]
    net_10 = conf.NETS[2][9]
    net_11 = conf.NETS[2][10]
    net_12 = conf.NETS[2][11]
    net_13 = conf.NETS[2][12]
    net_14 = conf.NETS[2][13]
    net_15 = conf.NETS[2][14]
    net_16 = conf.NETS[2][15]
    net_17 = conf.NETS[2][16]
    net_18 = conf.NETS[2][17]
    vnic_profile_4 = conf.VNIC_PROFILES[2][3]
    vnic_profile_5 = conf.VNIC_PROFILES[2][4]
    vnic_profile_10 = conf.VNIC_PROFILES[2][10]
    vnic_profile_10_2 = conf.VNIC_PROFILES[2][11]
    vnic_profile_17 = conf.VNIC_PROFILES[2][16]
    vnic_profile_17_2 = conf.VNIC_PROFILES[2][17]
    dc = conf.DC_0
    vm = conf.VM_0
    cluster = conf.CLUSTER_NAME[0]
    vnic = conf.NIC_NAME[1]
    vnic_2 = conf.NIC_NAME[2]
    vnic_3 = conf.NIC_NAME[3]

    @polarion("RHEVM3-3973")
    def test_01_create_new_profiles(self):
        """
        Check you can create a profile for sw2 with the same name as sw1
        Check you can't create profile with the same name for the same network
        """
        if not ll_networks.add_vnic_profile(
            positive=True, name=self.net_1, data_center=self.dc,
            network=self.net_2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=False, name=self.net_1, data_center=self.dc,
            network=self.net_2
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3989")
    def test_02_update_to_non_vm(self):
        """
        Update VM network to non-VM network
        Check that both VNIC profiles of the network were removed as a
        result of changing the state of the network to non-VM
        """
        if not ll_networks.updateNetwork(
            positive=True, network=self.net_3, usages=""
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.get_network_vnic_profiles(
            network=self.net_3, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION(
                "VNIC profiles exists for non-VM network %s" % self.net_3
            )

    @polarion("RHEVM3-3990")
    def test_03_remove_network(self):
        """
        Remove VM network
        Check that both VNIC profiles of the network were removed as a
        result of network removal
        """
        if not ll_networks.add_vnic_profile(
            positive=True, name=self.vnic_profile_4, data_center=self.dc,
            network=self.net_4
        ):
            raise conf.NET_EXCEPTION()

        for profile in [self.net_4, self.vnic_profile_4]:
            if not ll_networks.is_vnic_profile_exist(
                vnic_profile_name=profile
            ):
                raise conf.NET_EXCEPTION()

        if not ll_networks.removeNetwork(
            positive=True, network=self.net_4, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

        for profile in [self.net_4, self.vnic_profile_4]:
            if ll_networks.is_vnic_profile_exist(vnic_profile_name=profile):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3972")
    def test_04_check_non_vm(self):
        """
        Check no VNIC profile exists for non-VM network
        Check you can't create VNIC profile for non-VM network
        """
        if ll_networks.get_network_vnic_profiles(
            network=self.net_5, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION(
                "VNIC profiles exist for non-VM network %s" % self.net_5
            )

        if not ll_networks.add_vnic_profile(
            positive=False, name=self.vnic_profile_5, data_center=self.dc,
            network=self.net_5
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3978")
    def test_05_check_profile(self):
        """"
        Check that VNIC profile exists for VM network
        Check that VNIC profile doesn't exist for non-VM network'
        Check that VNIC profile doesn't exist for network with the flag
            profile_required set to false
        """
        if not ll_networks.get_network_vnic_profiles(
            network=self.net_6, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.get_network_vnic_profiles(
            network=self.net_7, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.get_network_vnic_profiles(
            network=self.net_8, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION(
                "VNIC profiles exists for non-VM network %s" % self.net_8
            )

    @polarion("RHEVM3-3995")
    def test_06_check_profile(self):
        """"
        Check that VNIC profile exists for VM network
        Check that you can't add VNIC profile to VM if its network is not
            attached to the host
        """
        if not ll_networks.get_network_vnic_profiles(
            network=self.net_9, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=False, vm=self.vm, name=self.vnic, network=self.net_9,
            vnic_profile=self.net_9
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3981")
    def test_07_update_network_unplugged_nic(self):
        """
        Update VNIC profile on nic2 with profile from different network
        Update VNIC profile on nic2 with profile from the same network
        Update VNIC profile on nic2 with profile from the same network
            but with port mirroring enabled
        Update VNIC profile on nic2 with profile having port mirroring
            enabled to different network with port mirroring disabled
        Remove vNIC from VM
        Clean host interfaces
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net_10,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": self.net_11,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_networks.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        ):
            raise conf.NET_EXCEPTION()

        for vpro in [self.vnic_profile_10, self.vnic_profile_10_2]:
            port_mirroring = False
            if vpro == self.vnic_profile_10_2:
                port_mirroring = True

            if not ll_networks.add_vnic_profile(
                positive=True, name=vpro, data_center=self.dc,
                network=self.net_11, port_mirroring=port_mirroring
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vnic, network=self.net_10,
            plugged="false"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_11,
            vnic_profile=self.vnic_profile_10
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_11,
            vnic_profile=self.net_11
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_11,
            vnic_profile=self.vnic_profile_10_2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_10,
            vnic_profile=self.net_10
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=self.vm, nic=self.vnic):
            raise conf.NET_EXCEPTION()

        if not hl_host_networks.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3976")
    def test_08_update_vnic_profile(self):
        """
        Try to update VNIC profile on nic2 to have port mirroring enabled
        Try to update VNIC profile on nic3 to have port mirroring disabled
        Remove vNICs from VM
        Clean host interfaces
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net_12,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": self.net_13,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_networks.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_vnic_profile(
            name=self.net_13, network=self.net_13, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

        for nic, net in zip(
            [self.vnic_2, self.vnic_3], [self.net_12, self.net_13]
        ):
            if not ll_vms.addNic(
                positive=True, vm=self.vm, name=nic, network=net
            ):
                raise conf.NET_EXCEPTION()

        for net, state in zip([self.net_12, self.net_13], [True, False]):
            if ll_networks.update_vnic_profile(
                name=net, network=self.net_12, port_mirroring=state
            ):
                raise conf.NET_EXCEPTION()

        for nic in [self.vnic_2, self.vnic_3]:
            if not ll_vms.updateNic(
                positive=True, vm=self.vm, nic=nic, plugged="false"
            ):
                raise conf.NET_EXCEPTION()

            if not ll_vms.removeNic(positive=True, vm=self.vm, nic=nic):
                raise conf.NET_EXCEPTION()

        if not hl_host_networks.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3975")
    def test_09_update_profiles(self):
        """
        Try to update network for existing profile
        """
        if ll_networks.update_vnic_profile(
            name=self.net_14, network=self.net_14, cluster=self.cluster,
            new_network=self.net_15
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3987")
    @bz({"1342054": {}})
    def test_10_hotplug_link_unlink(self):
        """
        Hotplug VNIC profile to the VMs nic2
        Unlink nic2
        Link nic2
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net_15,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_networks.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vnic, network=self.net_15,
            plugged="true"
        ):
            raise conf.NET_EXCEPTION()

        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=ll_vms.updateNic,
            positive=True, vm=self.vm,  nic=self.vnic,
            linked="false"
        )
        if not sample.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, linked="true"
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3985")
    @bz({"1342054": {}})
    def test_11_remove_used_profile(self):
        """
        Try to remove VNIC profile while VM is using it (negative case)
        Unplug vNIC from the VM
        Remove vNIC from the VM
        """
        if not ll_networks.remove_vnic_profile(
            positive=False, vnic_profile_name=self.net_15, network=self.net_15
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, plugged="false"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=self.vm, nic=self.vnic):
            raise conf.NET_EXCEPTION()

        if not hl_host_networks.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3986")
    @bz({"1342054": {}})
    def test_12_update_network_plugged_nic(self):
        """
        Update VNIC profile on nic2 with profile from different network
        Update VNIC profile on nic2 with profile from the same network
        Try to update VNIC profile on nic2 with profile from the same
            network but with port mirroring enabled (negative case)
        Update VNIC profile on nic2 with empty profile
        Update VNIC profile on nic2 with profile having port mirroring
            enabled (first unplug and after the action plug nic2)
        Try to update VNIC profile on nic2 with profile from the same
            network but with port mirroring disabled (negative case)
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net_17,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": self.net_18,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_networks.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        ):
            raise conf.NET_EXCEPTION()

        for vpro in [self.vnic_profile_17, self.vnic_profile_17_2]:
            port_mirroring = False
            if vpro == self.vnic_profile_17_2:
                port_mirroring = True

            if not ll_networks.add_vnic_profile(
                positive=True, name=vpro, data_center=self.dc,
                network=self.net_18, port_mirroring=port_mirroring
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vnic, network=self.net_17,
            plugged="true"
        ):
            raise conf.NET_EXCEPTION()

        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=ll_vms.updateNic,
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_18,
            vnic_profile=self.vnic_profile_17
        )
        if not sample.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_18,
            vnic_profile=self.net_18
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vnic, network=self.net_18,
            vnic_profile=self.vnic_profile_17_2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=None
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, plugged="false"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, network=self.net_18,
            vnic_profile=self.vnic_profile_17_2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, plugged="true"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vnic, network=self.net_18,
            vnic_profile=self.vnic_profile_17
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=self.vm, nic=self.vnic, plugged="false"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=self.vm, nic=self.vnic):
            raise conf.NET_EXCEPTION()

        if not hl_host_networks.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        ):
            raise conf.NET_EXCEPTION()


@attr(tier=2)
@pytest.mark.usefixtures("vnic_profile_prepare_setup")
class TestVNICProfileCase03(NetworkTest):
    """
    VNIC Profile on template
    """
    __test__ = True
    net_1 = conf.NETS[3][0]
    vnic_1 = conf.NIC_NAME[1]
    vnic_2 = conf.NIC_NAME[2]
    template = conf.TEMPLATE_NAME[0]
    cluster = conf.CLUSTER_NAME[0]
    dc = conf.DC_NAME[0]
    mgmt = conf.MGMT_BRIDGE
    vm_name2 = "new_VM_case03"

    @polarion("RHEVM3-3993")
    def test_create_new_profiles_template(self):
        """
        Check that you can create non-empty VNIC profile on Template
        Check that you can create empty VNIC profile on Template
        Create VM from the template with empty and non-empty profiles
        Make sure this VM has empty and non-empty profiles on it's NICs
        """
        if not ll_templates.addTemplateNic(
            positive=True, template=self.template, name=self.vnic_1,
            data_center=self.dc, network=self.net_1
        ):
            raise conf.NET_EXCEPTION()

        if not ll_templates.addTemplateNic(
            positive=True, template=self.template, name=self.vnic_2,
            data_center=self.dc, network=None
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.createVm(
            positive=True, vmName=self.vm_name2, vmDescription="",
            cluster=self.cluster, template=self.template, network=self.mgmt
        ):
            raise conf.NET_EXCEPTION()

        for vpro, nic in zip([self.net_1, None], [self.vnic_1, self.vnic_2]):
            if not ll_vms.check_vm_nic_profile(
                vm=self.vm_name2, vnic_profile_name=vpro, nic=nic
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3977")
    def test_remove_new_profiles_template(self):
        """
        Remove VM created from the previous test
        Try to remove network when template is using its VNIC profile.
            This test is the negative one
        Remove VNIC profile from the template
        Remove VNIC profile from the setup
        """
        if not ll_vms.removeVm(positive=True, vm=self.vm_name2):
            raise conf.NET_EXCEPTION()

        if not ll_networks.removeNetwork(
            positive=False, network=self.net_1, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

        if not ll_templates.removeTemplateNic(
            positive=True, template=self.template, nic=self.vnic_1
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=self.net_1, network=self.net_1
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove network from template
        """
        if not ll_templates.removeTemplateNic(
            positive=True, template=cls.template, nic=cls.vnic_2
        ):
            raise conf.NET_EXCEPTION()
