#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Input/Output feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Positive and negative cases for creating/editing networks
with valid/invalid names, IPs, netmask, VLAN, usages.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as io_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion, bz
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import(
    case_09_fixture, all_classes_teardown
)

logger = logging.getLogger("IO_Test_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest01(NetworkTest):
    """
    Positive: Creating & adding networks with valid names to the cluster
    Negative: Trying to create networks with invalid names
    """
    __test__ = True

    @polarion("RHEVM3-4381")
    def test_check_valid_network_names(self):
        """
        Positive: Should succeed creating networks with valid names
        """
        valid_names = [
            "endsWithNumber1",
            "nameMaxLengthhh",
            "1startsWithNumb",
            "1a2s3d4f5g6h",
            "01234567891011",
            "______",
        ]

        for network_name in valid_names:
            local_dict = {
                network_name: {}
            }
            testflow.step(
                "Create and attache network with valid name %s to "
                "datacenter %s and to cluster %s", network_name, conf.DC_0,
                conf.CL_0
            )
            self.assertTrue(
                hl_networks.createAndAttachNetworkSN(
                    data_center=conf.DC_0, cluster=conf.CL_0,
                    network_dict=local_dict
                )
            )

    @polarion("RHEVM3-14742")
    def test_check_invalid_network_names(self):
        """
        Negative: Should fail to create networks with invalid names
        """
        invalid_names = [
            "networkWithMoreThanFifteenChars",
            "inv@lidName",
            "________________",
            "bond",
            "",
        ]

        for network_name in invalid_names:
            testflow.step(
                "Try to create and attache network with invalid name %s to "
                "datacenter %s and to cluster %s", network_name, conf.DC_0,
                conf.CL_0
            )
            self.assertTrue(
                ll_networks.add_network(
                    positive=False, name=network_name, data_center=conf.DC_0,
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest02(NetworkTest):
    """
    Negative: Trying to create networks with invalid IPs
    """
    __test__ = True

    @polarion("RHEVM3-4380")
    def test_check_invalid_ips(self):
        """
        Negative: Trying to create networks with invalid IPs
        (Creation should fail)
        """
        invalid_ips = [
            ["1.1.1.260"],
            ["1.1.260.1"],
            ["1.260.1.1"],
            ["260.1.1.1"],
            ["1.2.3"],
            ["1.1.1.X"],
        ]

        for invalid_ip in invalid_ips:
            local_dict = {
                "add": {
                    "1": {
                        "network":  "invalid_ips",
                        "nic": conf.HOST_0_NICS[1],
                        "ip": {
                            "1": {
                                "address": invalid_ip,
                                "netmask": ["255.255.255.0"],
                                "boot_protocol": "static"
                            }
                        }
                    }
                }
            }
            testflow.step(
                "Try to create network with invalid IP %s",
                invalid_ip
            )
            self.assertFalse(
                hl_host_network.setup_networks(
                    host_name=conf.HOST_0_NAME, **local_dict
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest03(NetworkTest):
    """
    Negative: Trying to create networks with invalid netmask
    """
    __test__ = True

    @polarion("RHEVM3-4379")
    def test_check_invalid_netmask(self):
        """
        Negative: Trying to create networks with invalid netmask
        """
        invalid_netmasks = [
            ["255.255.255.260"],
            ["255.255.260.0"],
            ["255.260.255.0"],
            ["260.255.255.0"],
            ["255.255.255."],
            ["255.255.255.X"],
        ]

        for invalid_netmask in invalid_netmasks:
            local_dict = {
                "add": {
                    "1": {
                        "network": "invalid_netmask",
                        "nic": conf.HOST_0_NICS[1],
                        "ip": {
                            "1": {
                                "address": ["1.1.1.1"],
                                "netmask": invalid_netmask,
                                "boot_protocol": "static"
                            }
                        }
                    }
                }
            }
            testflow.step(
                "Try to create network with invalid netmask %s",
                invalid_netmask
            )
            self.assertFalse(
                hl_host_network.setup_networks(
                    host_name=conf.HOST_0_NAME, **local_dict
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest04(NetworkTest):
    """
    Negative: Trying to create a network with netmask but without an ip address
    """
    __test__ = True
    netmask = ["255.255.255.0"]
    net = io_conf.NETS[4][0]

    @polarion("RHEVM3-4378")
    def test_check_netmask_without_ip(self):
        """
        Negative: Trying to create a network with netmask but without an
        IP address
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "netmask": self.netmask,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        testflow.step(
            "Try to create a network %s with netmask %s but "
            "without an IP address", self.net, self.netmask
        )
        self.assertFalse(
            hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **local_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest05(NetworkTest):
    """
    Negative: Trying to create a network with static ip but without netmask
    """
    __test__ = True
    static_ip = network_helper.create_random_ips(num_of_ips=1)
    net = io_conf.NETS[5][0]

    @polarion("RHEVM3-4371")
    def test_check_static_ip_without_netmask(self):
        """
        Negative: Trying to create a network with static IP but without netmask
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "address": self.static_ip,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        testflow.step(
            "Try to create a network %s with static IP %s but without netmask",
            self.net, self.static_ip
        )
        self.assertFalse(
            hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **local_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest06(NetworkTest):
    """
    Positive: Creating networks with valid MTU and adding them to data center.
    Negative: Trying to create a network with invalid MTUs.
    """
    __test__ = True

    @polarion("RHEVM3-4377")
    def test_check_valid_mtu(self):
        """
        Positive: Creating networks with valid MTUs and adding them to a
        data center.
        """
        valid_mtus = [68, 69, 9000, 65520, 2147483647]
        testflow.step(
            "Creating networks with valid MTUs %s and adding "
            "them to a data center %s", valid_mtus, conf.DC_0
        )
        self.assertTrue(
            helper.create_networks(
                positive=True, params=valid_mtus, type_="mtu"
            )
        )

    @polarion("RHEVM3-14743")
    def test_check_invalid_mtu(self):
        """
        Negative: Trying to create a network with invalid MTUs - should fail.
        """
        invalid_mtus = [-5, 67, 2147483648]

        testflow.step(
            "Try to create a network with invalid MTUs %s", invalid_mtus
        )
        self.assertTrue(
            helper.create_networks(
                positive=False, params=invalid_mtus, type_="mtu"
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest07(NetworkTest):
    """
    Negative: Trying to create a network with invalid usages value
    """
    __test__ = True

    @polarion("RHEVM3-4376")
    def test_check_invalid_usages(self):
        """
        Trying to create a network with invalid usages value
        """
        local_dict = {
            "invalid_usage": {
                "usages": "Unknown"
            }
        }
        testflow.step(
            "Try to create a network with invalid usages value"
        )
        self.assertFalse(
            hl_networks.createAndAttachNetworkSN(
                data_center=conf.DC_0, network_dict=local_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest08(NetworkTest):
    """
    Positive: Creating networks with valid VLAN IDs & adding them to a DC.
    Negative: Trying to create networks with invalid VLAN IDs.
    """
    __test__ = True

    @polarion("RHEVM3-4375")
    def test_check_valid_vlan_ids(self):
        """
        Positive: Creating networks with valid VLAN IDs & adding them to a
        DC.
        """
        valid_vlan_ids = [4094, 1111, 111, 11, 1, 0]

        testflow.step(
            "Create networks with valid VLAN IDs %s and adding "
            "them to a DC %s", valid_vlan_ids, conf.DC_0
        )
        self.assertTrue(
            helper.create_networks(
                positive=True, params=valid_vlan_ids, type_="vlan_id"
            )
        )

    @polarion("RHEVM3-14744")
    def test_check_invalid_vlan_ids(self):
        """
        Negative: Trying to create networks with invalid VLAN IDs.
        """
        invalid_vlan_ids = [-10, 4095, 4096]

        testflow.step(
            "Try to create networks with invalid VLAN IDs %s", invalid_vlan_ids
        )
        self.assertTrue(
            helper.create_networks(
                positive=False, params=invalid_vlan_ids, type_="vlan_id"
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_09_fixture.__name__)
class TestIOTest09(NetworkTest):
    """
    Positive: Create network and edit its name to valid name.
    Negative: Try to edit its name to invalid name.
    Positive: change network VLAN tag to valid VLAN tag.
    Negative: change network VLAN tag to invalid VLAN tag.
    Positive: Change VM network to be non-VM network.
    Positive: Change non-VM network to be VM network.
    """
    initial_name = "NET_default"

    __test__ = True

    @polarion("RHEVM3-4374")
    def test_edit_network_name(self, initial_name=initial_name):
        """
        Positive: Should succeed editing network to valid name
        """
        valid_name = "NET_changed"

        testflow.step(
            "Create network %s and edit its name to valid name %s",
            initial_name, valid_name
        )
        self.assertTrue(
            ll_networks.update_network(
                positive=True, network=initial_name, name=valid_name
            )
        )

    @polarion("RHEVM3-14745")
    def test_edit_network_name_to_invalid_name(self):
        """
        Negative: Should fail to edit networks with invalid name
        """
        valid_name = "NET_changed"
        invalid_name = "inv@lidName"

        testflow.step(
            "Try to edit valid network name %s to invalid name %s",
            valid_name, invalid_name
        )
        self.assertTrue(
            ll_networks.update_network(
                positive=False, network=valid_name, name=invalid_name
            )
        )

    @polarion("RHEVM3-4373")
    def test_check_valid_vlan_tag(self, default_name=initial_name):
        """
        Positive: Should succeed editing network to valid VLAN tags
        """
        valid_tags = [2, 3, 15, 444, 4093]

        testflow.step(
            "Change network %s VLAN tag to valid VLAN tag %s",
            default_name, valid_tags
        )
        for valid_tag in valid_tags:
            self.assertTrue(
                ll_networks.update_network(
                    positive=True, network=default_name, vlan_id=valid_tag
                )
            )

    @polarion("RHEVM3-14746")
    @bz({"1339907": {}})
    def test_check_invalid_vlan_tag(self, default_name=initial_name):
        """
        Negative: Should fail to edit networks with invalid VLAN tags
        """
        invalid_tags = [-1, 4099]

        testflow.step(
            "Try to edit network %s with invalid VLAN tags %s",
            default_name, invalid_tags
        )
        for invalid_tag in invalid_tags:
            self.assertTrue(
                ll_networks.update_network(
                    positive=False, network=default_name, vlan_id=invalid_tag
                )
            )

    @polarion("RHEVM3-4372")
    def test_edit_vm_network(self):
        """
        Positive: Should succeed changing VM network to non-VM network
        """
        valid_name = "NET_changed"

        testflow.step(
            "Change VM network %s to be non-VM network", valid_name
        )
        self.assertTrue(
            ll_networks.update_network(
                positive=True, network=valid_name, usages="",
                description="nonVM network"
            )
        )

        testflow.step(
            "Change non-VM network %s to be VM network", valid_name
        )
        self.assertTrue(
            ll_networks.update_network(
                positive=True, network=valid_name, usages="vm",
                description="VM network again"
            )
        )


@attr(tier=2)
@bz({"1338522": {}})
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestIOTest10(NetworkTest):
    """
    Check network label limitation:
    1) Negative case: Try to create a label which does not comply with the
        pattern: numbers, digits, dash or underscore [0-9a-zA-Z_-].
    2) Negative case: Try to assign more than one label to network
    3) Positive case: Create label with length of 50 chars
    4) Positive case: Assign many labels to interface (10)
    """
    __test__ = True
    net_1 = io_conf.NETS[10][0]
    net_2 = io_conf.NETS[10][1]
    label_1 = io_conf.LABEL_NAME[10][0]
    label_2 = io_conf.LABEL_NAME[10][1]

    @polarion("RHEVM3-14806")
    def test_label_restriction(self):
        """
        1) Negative case Try to attach label with incorrect format to the
        network
        2) Negative case: Try to assign additional label to the network with
        attached label
        """
        special_char_labels = ["asd?f", "dfg/gd"]

        testflow.step(
            "Try to attach label with incorrect format %s to the network %s",
            special_char_labels, self.net_2
        )
        for label in special_char_labels:
            self.assertFalse(
                ll_networks.add_label(label=label, networks=[self.net_2])
            )

        testflow.step(
            "Try to assign additional label %s to the network %s"
            " with attached label %s", self.label_2, self.net_1, self.label_1
        )
        self.assertFalse(
            ll_networks.add_label(
                label=self.label_2, networks=[self.net_1]
            )
        )

    @polarion("RHEVM3-14807")
    def test_label_non_restrict(self):
        """
        1) Attach label with 50 characters to a network.
        2) Attach 10 labels to the interface on the Host when one of those
        networks is attached to the network and check that the network is
        attached to the Host interface
        """
        long_label = "a" * 50

        testflow.step(
            "Attach label with 50 characters to a network %s", self.net_1
        )
        self.assertTrue(
            ll_networks.add_label(
                label=long_label, networks=[self.net_1]
            )
        )

        testflow.step(
            "Attach 10 labels %s to the interface on the Host %s when one of "
            "those networks is attached to the network and check that "
            "the network is attached to the Host interface %s",
            io_conf.LABEL_NAME[10][1:], conf.HOST_0_NAME, conf.HOST_0_NICS[1]
        )
        for label in io_conf.LABEL_NAME[10][1:]:
            self.assertTrue(
                ll_networks.add_label(
                    label=label,
                    host_nic_dict={
                        conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                    }
                )
            )
