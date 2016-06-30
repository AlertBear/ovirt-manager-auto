#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing MultiHost feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be used for testing.
MultiHost will be tested for untagged, tagged, MTU, VM/non-VM and bond
scenarios.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as multi_host_conf
import helper
import rhevmtests.networking.config as conf
from art.core_api import apis_utils
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    fixture_case_03, fixture_case_04, fixture_case_05, fixture_case_06,
    fixture_case_01_02, fixture_case_07
)

logger = logging.getLogger("MultiHost_Cases")


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(fixture_case_01_02.__name__)
class TestMultiHostCase01(NetworkTest):
    """
    Update untagged network with VLAN
    Update tagged network with another VLAN
    Update tagged network to be untagged
    Update network with the default MTU to the MTU of 9000
    Update network to have default MTU value
    Update VM network to be non-VM network
    Update non-VM network to be VM network
    """
    __test__ = True
    restore_mtu = False
    net = multi_host_conf.NETS[1][0]
    vlan_1 = multi_host_conf.VLAN_IDS[0]
    vlan_2 = multi_host_conf.VLAN_IDS[1]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]

    @polarion("RHEVM3-4067")
    def test_update_with_vlan(self):
        """
        1) Update network with VLAN 162
        2) Check that the Host was updated with VLAN 162
        3) Update network with VLAN 163
        4) Check that the Host was updated with VLAN 163
        5) Update network with VLAN 163 to be untagged
        6) Check that the Host was updated as well
        """
        testflow.step("Update network with VLAN %s", self.vlan_1)
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan_1
            )
        )
        testflow.step("Update network with VLAN %s", self.vlan_2)
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan_2
            )
        )

    @polarion("RHEVM3-4080")
    def test_update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        testflow.step("Update network with MTU 9000")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, mtu=self.mtu_9000
            )
        )
        testflow.step("Update network with MTU 1500")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, mtu=self.mtu_1500
            )
        )

    @polarion("RHEVM3-4072")
    def test_update_with_non_vm_nonvm(self):
        """
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        testflow.step("Update network to be non-VM network")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, bridge=False
            )
        )
        testflow.step("Update network to be VM network")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, bridge=True
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_01_02.__name__)
class TestMultiHostCase02(NetworkTest):
    """
    Update network name:
    1) Negative when host is using it
    2) Negative when VM is using it (even non-running one)
    3) Negative when template is using it
    4) Positive when only DC/Cluster are using it
    Update non-VM network to be VM network
    """
    __test__ = True
    restore_mtu = False
    net = multi_host_conf.NETS[2][0]
    new_net_name = "multihost_net"
    vnic_2_name = conf.NIC_NAME[1]
    dc = conf.DC_0

    @polarion("RHEVM3-4079")
    def test_update_net_name(self):
        """
        1) Try to update network name when the network resides on the Host
        2) Try to update network name when the network resides on VM
        3) Try to update network name when the network resides on Template
        All cases should fail being negative cases
        4) Update network name when the network resides only on DC and Cluster
        Test should succeed
        """
        testflow.step(
            "Negative: update network name when the network resides on the "
            "Host"
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=False, network=self.net, data_center=self.dc,
                name=self.new_net_name
            )
        )
        self.assertTrue(
            hl_host_network.clean_host_interfaces(host_name=conf.HOST_0_NAME)
        )
        self.assertTrue(
            ll_vms.addNic(
                positive=True, vm=conf.VM_1, name=self.vnic_2_name,
                network=self.net
            )
        )
        testflow.step(
            "Negative: Try to update network name when network resides on VM"
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=False, network=self.net, data_center=self.dc,
                name=self.new_net_name
            )
        )
        self.assertTrue(
            ll_vms.removeNic(
                positive=True, vm=conf.VM_1, nic=self.vnic_2_name
            )
        )
        self.assertTrue(
            ll_templates.addTemplateNic(
                positive=True, template=conf.TEMPLATE_NAME[0],
                name=self.vnic_2_name, data_center=self.dc, network=self.net
            )
        )
        testflow.step(
            "Negative: Try to update network name when network resides "
            "on Template"
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=False, network=self.net, data_center=self.dc,
                name=self.vnic_2_name
            )
        )
        self.assertTrue(
            ll_templates.removeTemplateNic(
                positive=True, template=conf.TEMPLATE_NAME[0],
                nic=self.vnic_2_name
            )
        )
        testflow.step(
            "Update network name when network resides only on DC and Cluster"
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=True, network=self.net, data_center=self.dc,
                name=self.new_net_name
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_03.__name__)
class TestMultiHostCase03(NetworkTest):
    """
    Update network on running/non-running VM:
    1) Positive: Change MTU on net when running VM is using it
    2) Positive: Change VLAN on net when running VM is using it
    3) Positive: Change MTU on net when non-running VM is using it
    4) Positive: Change VLAN on net when non-running VM is using it
    5) Negative: Update non-VM network to be VM network used by non-running VM
    """
    __test__ = True
    restore_mtu = True
    net = multi_host_conf.NETS[3][0]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]
    vlan = multi_host_conf.VLAN_IDS[2]
    vm_nic = conf.NIC_NAME[1]
    vm_list = conf.VM_NAME[:2]
    vm_0 = conf.VM_0

    @polarion("RHEVM3-4074")
    def test_update_net_on_vm(self):
        """
        1) Positive: Change MTU on net when running VM is using it
        2) Positive: Change VLAN on net when running VM is using it
        3) Positive: Change MTU on net when non-running VM is using it
        4) Positive: Change VLAN on net when non-running VM is using it
        5) Negative: Update non-VM network to be VM network used by
        non-running VM
        """
        testflow.step(
            "Change MTU on net when running VM is using it and Change MTU on "
            "net when non-running VM is using it"
        )
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, mtu=self.mtu_9000
            )
        )
        testflow.step(
            "Change VLAN on net when running VM is using it and Change VLAN "
            "on net when non-running VM is using it"
        )
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan
            )
        )
        testflow.step(
            "Negative: Update non-VM network to be VM network used by "
            "non-running VM"
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=False, network=self.net, data_center=conf.DC_0,
                usages=""
            )
        )
        self.assertTrue(
            ll_networks.is_host_network_is_vm(
                vds_resource=conf.VDS_0_HOST, net_name=self.net
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_04.__name__)
class TestMultiHostCase04(NetworkTest):
    """
    Update network when template is using it:
    1) Negative: Try to update network from VM to non-VM when template is
    using it
    2) Positive: Try to change MTU on net when template is using it
    3) Positive: Try to change VLAN on net when template is using it
    """
    __test__ = True
    restore_mtu = True
    net = multi_host_conf.NETS[4][0]
    vm_nic = conf.NIC_NAME[1]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]
    vlan = multi_host_conf.VLAN_IDS[3]
    dc = conf.DC_0
    template = conf.TEMPLATE_NAME[0]

    @polarion("RHEVM3-4073")
    def test_update_net_on_template(self):
        """
        1) Negative: Try to update network from VM to non-VM when template is
        using it
        2) Positive: Try to change MTU on net when template is using it
        3) Positive: Try to change VLAN on net when template is using it
        """
        testflow.step(
            "Negative: Try to update network from VM to non-VM when template "
            "is using it"
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=False, network=self.net, data_center=conf.DC_0,
                usages=""
            )
        )
        testflow.step("Try to change MTU on net when template is using it")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, mtu=self.mtu_9000
            )
        )
        testflow.step("Try to change VLAN on net when template is using it")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_05.__name__)
class TestMultiHostCase05(NetworkTest):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC/Cluster
    Make sure all the changes exist on both Hosts
    """
    __test__ = True
    restore_mtu = True
    net = multi_host_conf.NETS[5][0]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]
    vlan = multi_host_conf.VLAN_IDS[4]

    @polarion("RHEVM3-4078")
    def test_update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan, mtu=self.mtu_9000,
                hosts=conf.HOSTS_LIST, vds_hosts=conf.VDS_HOSTS_LIST, matches=2
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_06.__name__)
class TestMultiHostCase06(NetworkTest):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC, but under different Clusters of the same DC
    Make sure all the changes exist on both Hosts
    """
    __test__ = True
    net = multi_host_conf.NETS[6][0]
    mtu_1500 = conf.MTU[-1]
    restore_mtu = True
    cl_name2 = "new_CL_case08"
    dc = conf.DC_0
    cpu = conf.CPU_NAME
    version = conf.COMP_VERSION
    cl = conf.CL_0

    @polarion("RHEVM3-4077")
    def test_update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """
        mtu_dict1 = {"mtu": conf.MTU[0]}
        sample1 = []
        vlan_id = multi_host_conf.VLAN_IDS[5]
        mtu_9000 = conf.MTU[0]

        testflow.step(
            "Update network with VLAN %s and MTU %s ", vlan_id, mtu_9000
        )
        self.assertTrue(
            ll_networks.updateNetwork(
                positive=True, network=self.net, data_center=self.dc,
                vlan_id=vlan_id, mtu=mtu_9000
            )
        )

        for host, nic in zip(
            conf.HOSTS_LIST, (conf.HOST_0_NICS[1], conf.HOST_1_NICS[1])
        ):
            sample1.append(
                apis_utils.TimeoutingSampler(
                    timeout=conf.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=hl_networks.check_host_nic_params,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            self.assertTrue(sample1[i].waitForFuncStatus(result=True))

        testflow.step(
            "Check that the both hosts were updated with VLAN and MTU 9000"
        )
        for vds_host in conf.VDS_HOSTS_LIST:
            nic = vds_host.nics[1]
            self.assertTrue(
                test_utils.check_mtu(
                    vds_resource=vds_host, mtu=mtu_9000,
                    physical_layer=False, network=self.net, nic=nic
                )
            )
            self.assertTrue(
                test_utils.check_mtu(
                    vds_resource=vds_host, mtu=mtu_9000, nic=nic
                )
            )
            self.assertTrue(
                ll_networks.is_vlan_on_host_network(
                    vds_resource=vds_host, interface=nic, vlan=vlan_id
                )
            )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(fixture_case_07.__name__)
class TestMultiHostCase07(NetworkTest):
    """
    Update network with VLAN/VM/Non-VM/MTU on BOND
    """
    __test__ = True
    restore_mtu = False
    net = multi_host_conf.NETS[7][0]
    mtu_1500 = conf.MTU[-1]
    mtu_9000 = conf.MTU[0]
    bond = conf.BOND[0]
    vlan_1 = multi_host_conf.VLAN_IDS[6]
    vlan_2 = multi_host_conf.VLAN_IDS[7]

    @polarion("RHEVM3-4069")
    def test_update_with_vlan_bond(self):
        """
        There is a bz for updating network to be tagged - 1081489

        1) Update network with VLAN 162
        2) Check that the Host was updated with VLAN 162
        3) Update network with VLAN 163
        4) Check that the Host was updated with VLAN 163
        """
        testflow.step("Update network with VLAN %s on BOND", self.vlan_1)
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan_1, nic=self.bond
            )
        )
        testflow.step("Update network with VLAN %s on BOND", self.vlan_2)
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, vlan_id=self.vlan_2, nic=self.bond
            )
        )

    @polarion("RHEVM3-4068")
    def test_update_with_mtu_bond(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        testflow.step("Update network with MTU 9000 on BOND")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, mtu=self.mtu_9000, nic=self.bond
            )
        )
        testflow.step("Update network with MTU 1500 on BOND")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, mtu=self.mtu_1500, nic=self.bond
            )
        )

    @polarion("RHEVM3-4081")
    def test_update_with_non_vm_nonvm_bond(self):
        """
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        testflow.step("Update network to be non-VM network on BOND")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, bridge=False, nic=self.bond
            )
        )
        testflow.step("Update network to be VM network on BOND")
        self.assertTrue(
            helper.update_network_and_check_changes(
                net=self.net, bridge=True, nic=self.bond
            )
        )
