# #! /usr/bin/python
# # -*- coding: utf-8 -*-
#
"""
SR_IOV feature tests
Non-VM related cases
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import config as sriov_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    create_qos, set_num_of_vfs, prepare_setup_general,
    add_vnics_to_vm, init_fixture, reset_host_sriov_params, add_vnic_profile
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    setup_networks_fixture.__name__
)
@pytest.mark.skipif(
    conf.NO_SEMI_SRIOV_SUPPORT, reason=conf.NO_SEMI_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriov01(NetworkTest):
    """
    1. Create bond from 2 supported sr_iov NICs (PFs)
    2. Check that bond doesn't have sr_iov related configuration
    3. Check that bond NICs have SR_IOV related configuration
    """
    __test__ = True

    # General
    bond_1 = "bond1"
    sriov_nics = True

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [0, 1],
            }
        }
    }

    @polarion("RHEVM3-6550")
    def test_bond_sriov_config(self):
        """
        1. Check that bond doesn't have sr_iov related configuration
        2. Check that Bond NICs have sr_iov related configuration
        """
        helper.update_host_nics()
        pf_list_names = (
            sriov_conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_names()
        )
        testflow.step(
            "Check that bond name is not in sr_iov pf names list"
        )
        assert self.bond_1 not in pf_list_names
        testflow.step(
            "Check that bond NICs are still sr_iov pfs when being part of a "
            "bond by trying to create a PF object"
        )
        [
            ll_sriov.SriovNicPF(conf.HOST_0_NAME, pf) for
            pf in sriov_conf.HOST_0_PF_NAMES[:2]
        ]


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    init_fixture.__name__,
    create_qos.__name__,
    add_vnic_profile.__name__
)
@pytest.mark.skipif(
    conf.NO_SEMI_SRIOV_SUPPORT, reason=conf.NO_SEMI_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriov02(NetworkTest):
    """
    Edit vNIC profile with passthrough property
    """
    __test__ = True

    # General
    dc = conf.DC_0

    # create_qos
    net_qos = sriov_conf.NETWORK_QOS

    # add_vnic_profile
    profiles = sriov_conf.GENERAL_TEST_VNICS[2][:3]
    pass_through_vnic = [True, True, False]
    port_mirroring = [False, False, True]
    net_1 = conf.MGMT_BRIDGE

    @polarion("RHEVM3-6305")
    def test_01_port_mirroring_update(self):
        """
        Check that port mirroring can't be configured
        """
        testflow.step("Check that port mirroring can't be configured")
        assert not ll_networks.update_vnic_profile(
            name=self.profiles[0], network=self.net_1,
            data_center=self.dc, port_mirroring=True
        )

    @polarion("RHEVM3-14628")
    def test_02_network_qos_update(self):
        """
        Check that QoS can't be configured
        """
        testflow.step("Check that QoS can't be configured")
        assert not ll_networks.update_qos_on_vnic_profile(
            datacenter=self.dc, qos_name=self.net_qos,
            vnic_profile_name=self.profiles[0],
            network_name=self.net_1
        )

    @polarion("RHEVM3-14630")
    def test_03_pm_qos_update(self):
        """
        Check that port mirroring and QoS are available after
        disabling passthrough on vNIC
        """
        testflow.step(
            "Check that port mirroring and QoS are available after disabling "
            "passthrough on vNIC"
        )
        assert ll_networks.update_vnic_profile(
            name=self.profiles[0], network=self.net_1,
            pass_through=False, data_center=self.dc
        )
        assert ll_networks.update_vnic_profile(
            name=self.profiles[0], network=self.net_1,
            data_center=self.dc, port_mirroring=True
        )
        assert ll_networks.update_qos_on_vnic_profile(
            datacenter=self.dc, qos_name=self.net_qos,
            vnic_profile_name=self.profiles[0],
            network_name=self.net_1
        )

    @polarion("RHEVM3-6310")
    def test_04_passthrough_enabled_vnic(self):
        """
        Check that passthrough property is enabled on created vNIC profile
        """
        testflow.step("Check passthrough on %s", self.profiles[1])
        vnic_profile_obj = ll_networks.get_vnic_profile_obj(
            name=self.profiles[1], network=self.net_1,
            cluster=conf.CL_0,  data_center=self.dc
        )
        assert vnic_profile_obj.get_pass_through().get_mode() != "disable"

    @polarion("RHEVM3-14581")
    def test_05_port_mirroring_update_created_vnic(self):
        """
        Check that port mirroring can't be configured on vNIC profile
        with passthrough property
        """
        testflow.step(
            "Check that port mirroring can't be configured on vNIC profile "
            "with passthrough property"
        )
        assert not ll_networks.update_vnic_profile(
            name=self.profiles[1], network=self.net_1,
            data_center=self.dc, port_mirroring=True
        )

    @polarion("RHEVM3-14631")
    def test_06_network_qos_update_created_vnic(self):
        """
        Check that QoS can't be configured on vNIC profile
        with passthrough property
        """
        testflow.step(
            "Check that QoS can't be configured on vNIC profile with "
            "passthrough property"
        )
        assert not ll_networks.update_qos_on_vnic_profile(
            datacenter=self.dc, qos_name=self.net_qos,
            vnic_profile_name=self.profiles[1],
            network_name=self.net_1
        )

    @polarion("RHEVM3-14632")
    def test_07_pm_update_enable(self):
        """
        Try to update vNIC profile with passthrough property when pm is enabled
        """
        testflow.step(
            "Try to update vNIC profile with passthrough property when pm is "
            "enabled"
        )
        assert not ll_networks.update_vnic_profile(
            name=self.profiles[2], network=self.net_1,
            pass_through=True, data_center=self.dc
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    reset_host_sriov_params.__name__,
    clean_host_interfaces.__name__,
    set_num_of_vfs.__name__
)
@pytest.mark.skipif(
    conf.NO_SEMI_SRIOV_SUPPORT, reason=conf.NO_SEMI_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriov03(NetworkTest):
    """
    Create several VFs for PF and check
    a. The same number is configured on engine and on host relevant file
    b. Putting link up and down doesn't change the number of VFs
    """
    __test__ = True

    # set_num_of_vfs
    num_of_vfs = 2

    # clean_host_interfaces
    hosts_nets_nic_dict = {
        0: {}
    }

    @polarion("RHEVM3-6318")
    def test_same_vf_number_engine_host(self):
        """
        Check for the same number of VFs on engine and on host file
        """
        nic_name = sriov_conf.HOST_0_PF_OBJECT_1.nic_name
        num_vf = sriov_conf.HOST_0_PF_OBJECT_1.get_number_of_vf()
        path = sriov_conf.NUM_VF_PATH % nic_name
        rc, out, _ = conf.VDS_0_HOST.run_command(["cat", path])
        testflow.step(
            "Check for the same number of VFs on engine and on host file"
        )
        assert num_vf == int(out)

    @polarion("RHEVM3-14633")
    def test_vf_number_after_ifup_ifdown(self):
        """
        Check that putting link up and down doesn't change the number of VFs
        """
        testflow.step(
            "Check that putting link up and down doesn't change the number of "
            "VFs"
        )
        nic_name = sriov_conf.HOST_0_PF_OBJECT_1.nic_name
        num_vf = sriov_conf.HOST_0_PF_OBJECT_1.get_number_of_vf()
        assert conf.VDS_0_HOST.network.if_down(nic=nic_name)
        assert conf.VDS_0_HOST.network.if_up(nic=nic_name)
        assert num_vf == num_vf

    @polarion("RHEVM3-14594")
    def test_negative_vf_number(self):
        """
        Check that it's impossible to configure negative value for num VF
        """
        testflow.step("Try to configure negative VF value for PF")
        assert not sriov_conf.HOST_0_PF_OBJECT_1.set_number_of_vf(-2)

    @polarion("RHEVM3-14635")
    def test_over_max_vf_number(self):
        """
        Check that it's impossible to configure value bigger than the max value
        supported by PF
        """
        testflow.step("Try to configure value bigger than max supported by PF")
        max_vf = sriov_conf.HOST_0_PF_OBJECT_1.get_max_number_of_vf()
        assert not sriov_conf.HOST_0_PF_OBJECT_1.set_number_of_vf(max_vf + 1)


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    reset_host_sriov_params.__name__,
    clean_host_interfaces.__name__,
    prepare_setup_general.__name__,
    set_num_of_vfs.__name__
)
@pytest.mark.skipif(
    conf.NO_SEMI_SRIOV_SUPPORT, reason=conf.NO_SEMI_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriov04(NetworkTest):
    """
    Changing the number of VFs for a PF when PF contains non-free VFs
    """
    __test__ = True

    # General
    net1 = sriov_conf.GENERAL_NETS[4][0]

    # set_num_of_vfs
    num_of_vfs = 3

    # clean_host_interfaces
    hosts_nets_nic_dict = {
        0: {}
    }

    @polarion("RHEVM3-14637")
    def test_01_change_vf_num_for_occupied_vf_network(self):
        """
        1. Add network to VF
        2. Try to change the number of VFs and fail as one VF is occupied
        """
        testflow.step(
            "Negative: Try to change the number of VFs when one of the VFs is "
            "occupied by network %s attached to it", self.net1
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net1,
                    "nic": sriov_conf.HOST_0_PF_OBJECT_1.get_all_vf_names()[0]
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        assert not sriov_conf.HOST_0_PF_OBJECT_1.set_number_of_vf(2)

    @polarion("RHEVM-19156")
    def test_change_vf_num_for_non_occupied_vf_network(self):
        """
        1. Remove network from VF
        2. Change the number of VFs on PF and succeed
        """
        testflow.step(
            "Remove network %s and check you can change the VF number",
            self.net1
        )
        assert hl_host_network.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        )
        assert sriov_conf.HOST_0_PF_OBJECT_1.set_number_of_vf(2)


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    prepare_setup_general.__name__,
    setup_networks_fixture.__name__,
    add_vnic_profile.__name__,
    add_vnics_to_vm.__name__,
)
@pytest.mark.skipif(
    conf.NO_SEMI_SRIOV_SUPPORT, reason=conf.NO_SEMI_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriov05(NetworkTest):
    """
    Try to edit regular vNIC profile on VM to have passthrough property
    Try to edit vNIC profile with passthrough property to become regular vNIC
    """
    __test__ = True

    # General
    vnic_profile = sriov_conf.GENERAL_TEST_VNICS[5][0]
    dc = conf.DC_0

    # add_vnic_profile
    port_mirroring = [False]
    net_1 = sriov_conf.GENERAL_NETS[5][0]

    # add_vnics_to_vm
    nics = sriov_conf.GENERAL_TEST_VNICS[5][1:3]
    pass_through_vnic = [True, False]
    profiles = [vnic_profile, net_1]
    vms = [conf.VM_0, conf.VM_0]
    nets = [net_1, net_1]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
            }
        }
    }

    @polarion("RHEVM3-10630")
    def test_01_update_vnic_with_passthrough(self):
        """
        Check that it's impossible to change regular vNIC on VM to have
        passthrough property
        """
        testflow.step(
            "Check that it's impossible to change regular vNIC on VM to have "
            "passthrough property"
        )
        assert not ll_networks.update_vnic_profile(
            name=self.net_1, network=self.net_1, data_center=self.dc,
            pass_through=True
        )

    @polarion("RHEVM3-14641")
    def test_02_update_vnic_with_non_passthrough(self):
        """
        Check that it's impossible to change vNIC on VM with passthrough
        property to become regular vNIC
        """
        testflow.step(
            "Check that it's impossible to change vNIC on VM with "
            "passthrough property to become regular vNIC"
        )
        assert not ll_networks.update_vnic_profile(
            name=self.vnic_profile, network=self.net_1, data_center=self.dc,
            pass_through=False
        )
