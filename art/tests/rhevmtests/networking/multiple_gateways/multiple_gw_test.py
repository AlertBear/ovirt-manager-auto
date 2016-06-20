#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Multiple Gateways feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Multiple Gateway will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
Only static IP configuration is tested.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as multiple_gw_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest as TestCase
from art.unittest_lib import attr, testflow
from fixtures import attach_networks_to_host, teardown_all_cases

logger = logging.getLogger("Multiple_Gateway_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(attach_networks_to_host.__name__)
class TestGatewaysCase01(TestCase):
    """
    Verify you can configure additional VLAN network with static IP and gateway
    """
    __test__ = True
    ip = multiple_gw_conf.IPS[1]
    net = multiple_gw_conf.NETS[1][0]
    nic = 1
    slaves = None

    @polarion("RHEVM3-3953")
    def test_check_ip_rule_vlan(self):
        """
        Check correct configuration with ip rule function
        """
        testflow.step(
            "Check correct configuration with ip rule command on VLAN network"
        )
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=conf.SUBNET
        )


@attr(tier=2)
@pytest.mark.usefixtures(attach_networks_to_host.__name__)
class TestGatewaysCase02(TestCase):
    """
    Verify you can configure additional bridgeless network with static IP.
    """
    __test__ = True
    ip = multiple_gw_conf.IPS[2]
    net = multiple_gw_conf.NETS[2][0]
    nic = 1
    slaves = None

    @polarion("RHEVM3-3954")
    def test_check_ip_rule_non_vm(self):
        """
        Check correct configuration with ip rule function
        """
        testflow.step(
            "Check correct configuration with ip rule command on non-VM "
            "network"
        )
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=conf.SUBNET
        )


@attr(tier=2)
@pytest.mark.usefixtures(attach_networks_to_host.__name__)
class TestGatewaysCase03(TestCase):
    """
    Verify you can configure additional display network with static ip config.
    Mgmt network should be static
    """
    __test__ = True
    ip = multiple_gw_conf.IPS[3]
    net = multiple_gw_conf.NETS[3][0]
    nic = 1
    slaves = None

    @polarion("RHEVM3-3956")
    def test_check_ip_rule_display(self):
        """
        Check correct configuration with ip rule function
        """
        testflow.step(
            "Check correct configuration with ip rule command on display "
            "network"
        )
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=conf.SUBNET
        )


@attr(tier=2)
class TestGatewaysCase04(TestCase):
    """
    Try to assign to vm network incorrect static IP and gw addresses
    """
    __test__ = True
    ip = multiple_gw_conf.IPS[4]
    net = multiple_gw_conf.NETS[4][0]
    incorrect_value = "5.5.5.298"
    slaves = None

    @polarion("RHEVM3-3958")
    def test_check_incorrect_config_incorrect(self):
        """
        Try to create logical  network on DC/Cluster/Hosts
        Configure it with static IP configuration and incorrect gateway or IP
        """
        testflow.step(
            "Negative: Attach network %s with incorrect IP", self.net
        )
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "address": self.incorrect_value,
                            "netmask": conf.NETMASK,
                            "gateway": conf.MG_GATEWAY,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
        testflow.step(
            "Negative: Attach network %s with incorrect gateway", self.net
        )
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "address": self.ip,
                            "netmask": conf.NETMASK,
                            "gateway": self.incorrect_value,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases.__name__)
class TestGatewaysCase05(TestCase):
    """
    Verify you can configure additional network with gateway 0.0.0.0
    """
    __test__ = True
    gateway = "0.0.0.0"
    ip = multiple_gw_conf.IPS[5]
    net = multiple_gw_conf.NETS[5][0]
    slaves = None

    @polarion("RHEVM3-3966")
    def test_check_ip_rule_zero_gw(self):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration and gateway of 0.0.0.0
        """
        testflow.step(
            "Configure it with static IP configuration and gateway of 0.0.0.0"
        )
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "address": self.ip,
                            "netmask": conf.NETMASK,
                            "gateway": self.gateway,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(attach_networks_to_host.__name__)
class TestGatewaysCase06(TestCase):
    """
    Verify you can add additional NIC to the already created bond
    Verify you can remove slave from already created bond
    """
    __test__ = True
    net = multiple_gw_conf.NETS[6][0]
    nic = "bond06"
    ip = multiple_gw_conf.IPS[6]
    slaves = [-2, -1]

    @polarion("RHEVM3-3963")
    def test_check_ip_rule_add_slave(self):
        """
        Add additional NIC to the bond and check IP rule
        """
        testflow.step("Checking IP rule on BOND before adding 3rd slave")
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=conf.SUBNET
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.nic,
                    "slaves": [conf.VDS_0_HOST.nics[-3]]
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step("Checking IP rule after adding 3rd slave")
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=conf.SUBNET
        )

    @polarion("RHEVM3-3964")
    def test_check_ip_rule_remove_slave(self):
        """
        Remove a NIC from bond and check ip rule
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.nic,
                    "slaves": [conf.VDS_0_HOST.nics[-3]]
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Checking the IP rule after removing one slave from bond"
        )
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=conf.SUBNET
        )
