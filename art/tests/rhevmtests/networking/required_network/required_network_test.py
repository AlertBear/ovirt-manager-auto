#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing RequiredNetwork network feature.
1 DC, 1 Cluster, 1 Hosts will be created for testing.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as required_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, attr
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, NetworkFixtures, clean_host_interfaces
)  # flake8: noqa
from fixtures import activate_host, create_network_on_setup


@pytest.fixture(scope="module", autouse=True)
def required_network_prepare_setup(request):
    """
    Deactivate hosts
    """
    NetworkFixtures()

    def fin1():
        """
        Activate hosts
        """
        testflow.teardown("Activate hosts")
        for host in conf.HOSTS:
            hl_hosts.activate_host_if_not_up(host=host)
    request.addfinalizer(fin1)

    testflow.setup("Deactivate hosts")
    assert helper.deactivate_hosts()


@attr(tier=2)
class TestRequiredNetwork01(NetworkTest):
    """
    Check that management network is required by default
    Try to set it to non required.
    """
    __test__ = True
    cluster = conf.CL_0
    mgmt = conf.MGMT_BRIDGE

    @polarion("RHEVM3-3753")
    def test_mgmt(self):
        """
        Check that management network is required by default
        Try to set it to non required.
        """

        testflow.step("Check that management network is required by default")
        assert ll_networks.is_network_required(
            network=self.mgmt, cluster=self.cluster
        )

        testflow.step("Try to set management network to non required.")
        assert ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster, network=self.mgmt,
            required="false"
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_network_on_setup.__name__,
    setup_networks_fixture.__name__,
    activate_host.__name__
)
class TestRequiredNetwork02(NetworkTest):
    """
    Attach required non-VM network to host
    Set host NIC down
    Check that host is non-operational
    """
    __test__ = True
    net = required_conf.NETS[2][0]
    net_dict = {
        net: {
            "required": "true",
            "usages": ""
        }
    }
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net
            }
        }
    }

    @polarion("RHEVM3-3744")
    def test_nonoperational(self):
        """
        Set host NIC down
        Check that host is non-operational
        """
        testflow.step(
            "Set host NIC down and check that host is non-operational"
        )
        assert helper.set_nics_and_wait_for_host_status(
            nics=[conf.HOST_0_NICS[1]],
            nic_status=required_conf.NIC_STATE_DOWN,
            host_status=conf.HOST_NONOPERATIONAL
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_network_on_setup.__name__,
    setup_networks_fixture.__name__,
    activate_host.__name__
)
class TestRequiredNetwork03(NetworkTest):
    """
    Attach required VLAN network over BOND.
    Set BOND slaves down
    Check that host is non-operational
    Set BOND slaves up
    Check that host is operational
    """
    __test__ = True
    net = required_conf.NETS[3][0]
    net_dict = {
        net: {
            "required": "true",
            "vlan_id": required_conf.VLAN_ID
        }
    }
    bond = "bond4"
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": bond,
                "network": net,
                "slaves": [2, 3],
            }
        }
    }

    @polarion("RHEVM3-3752")
    def test_1_nonoperational_bond_down(self):
        """
        Set bond SLAVES DOWN
        Check that host is non-operational
        """
        testflow.step(
            "Set bond SLAVES DOWN and check that host is non-operational"
        )
        assert helper.set_nics_and_wait_for_host_status(
            nics=conf.HOST_0_NICS[2:4],
            nic_status=required_conf.NIC_STATE_DOWN,
            host_status=conf.HOST_NONOPERATIONAL
        )

    @polarion("RHEVM3-3745")
    def test_2_nonoperational_bond_down(self):
        """
        Set BOND slaves up
        Check that host is operational
        """
        testflow.step("Set bond slaves up and check that host is operatinal")
        assert helper.set_nics_and_wait_for_host_status(
            nics=conf.HOST_0_NICS[2:4], nic_status=required_conf.NIC_STATE_UP
        )
