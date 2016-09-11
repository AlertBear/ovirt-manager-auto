#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Input/Output feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Positive and negative cases for creating/editing networks
with valid/invalid names, IPs, netmask, VLAN, usages.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as io_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module", autouse=True)
def io_fixture_prepare_setup(request):
    """
    Prepare setup
    """
    io_fixture = NetworkFixtures()

    def fin():
        """
        Finalizer for remove networks
        """
        testflow.teardown("Remove network from setup")
        assert network_helper.remove_networks_from_setup(
            io_fixture.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Prepare Networks %s on datacenter %s and cluster %s",
        io_conf.NET_DICT, io_fixture.dc_0, io_fixture.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=io_conf.NET_DICT, dc=io_fixture.dc_0,
        cluster=io_fixture.cluster_0
    )


@attr(tier=2)
class TestIOTest01(NetworkTest):
    """
    1) Positive: Creating & adding networks with valid names to the cluster.
    2) Negative: Trying to create networks with invalid names.
    3) Positive: Creating networks with valid MTU and adding them to
        data center.
    4) Negative: Trying to create a network with invalid MTUs.
    5) Negative: Trying to create a network with invalid usages value.
    6) Positive: Creating networks with valid VLAN IDs & adding them to a DC.
    7) Negative: Trying to create networks with invalid VLAN IDs.
    """
    __test__ = True

    @polarion("RHEVM3-4381")
    def test_01_check_valid_network_names(self):
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
            testflow.step(
                "Create and attache network with valid name %s to "
                "datacenter %s", network_name, conf.DC_0
            )
            assert ll_networks.add_network(
                positive=True, name=network_name, data_center=conf.DC_0
            )

    @polarion("RHEVM3-14742")
    def test_02_check_invalid_network_names(self):
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
                "datacenter %s ", network_name, conf.DC_0
            )
            assert ll_networks.add_network(
                positive=False, name=network_name, data_center=conf.DC_0,
            )

    @polarion("RHEVM3-4377")
    def test_03_check_valid_mtu(self):
        """
        Positive: Creating networks with valid MTUs and adding them to a
        data center.
        """
        valid_mtus = [68, 69, 9000, 65520, 2147483647]
        testflow.step(
            "Creating networks with valid MTUs %s and adding "
            "them to a data center %s", valid_mtus, conf.DC_0
        )
        for valid_mtu in valid_mtus:
            assert ll_networks.add_network(
                positive=True, data_center=conf.DC_0, mtu=valid_mtu,
                name="io_%s" % str(valid_mtu)
            )

    @polarion("RHEVM3-14743")
    def test_04_check_invalid_mtu(self):
        """
        Negative: Trying to create a network with invalid MTUs - should fail.
        """
        invalid_mtus = [-5, 67, 2147483648]

        testflow.step(
            "Try to create a network with invalid MTUs %s", invalid_mtus
        )
        for invalid_mtu in invalid_mtus:
            assert ll_networks.add_network(
                positive=False, data_center=conf.DC_0, mtu=invalid_mtu,
                name="io_%s" % str(invalid_mtu)
            )

    @polarion("RHEVM3-4376")
    def test_05_check_invalid_usages(self):
        """
        Trying to create a network with invalid usages value
        """
        testflow.step(
            "Try to create a network with invalid usages value"
        )
        assert ll_networks.add_network(
            positive=False, data_center=conf.DC_0, name="io_invalid_usage",
            usages="Unknown"
        )

    @polarion("RHEVM3-4375")
    def test_06_check_valid_vlan_ids(self):
        """
        Positive: Creating networks with valid VLAN IDs & adding them to a
        DC.
        """
        valid_vlan_ids = [4094, 1111, 111, 11, 1, 0]

        testflow.step(
            "Create networks with valid VLAN IDs %s and adding "
            "them to a DC %s", valid_vlan_ids, conf.DC_0
        )
        for valid_vlan_id in valid_vlan_ids:
            assert ll_networks.add_network(
                positive=True, data_center=conf.DC_0,  vlan_id=valid_vlan_id,
                name="io_%s" % str(valid_vlan_id),

            )

    @polarion("RHEVM3-14744")
    def test_07_check_invalid_vlan_ids(self):
        """
        Negative: Trying to create networks with invalid VLAN IDs.
        """
        invalid_vlan_ids = [-10, 4095, 4096]

        testflow.step(
            "Try to create networks with invalid VLAN IDs %s", invalid_vlan_ids
        )
        for invalid_vlan_id in invalid_vlan_ids:
            assert ll_networks.add_network(
                positive=False, data_center=conf.DC_0, vlan_id=invalid_vlan_id,
                name="io_%s" % str(invalid_vlan_id),

            )


@attr(tier=2)
class TestIOTest02(NetworkTest):
    """
    1) Negative: Trying to create networks with invalid IPs.
    2) Negative: Trying to create networks with invalid netmask.
    3) Negative: Trying to create a network with netmask but without an
        ip address.
    4) Negative: Trying to create a network with static ip but without netmask.
    """
    __test__ = True
    net_1 = io_conf.NETS[2][0]
    net_2 = io_conf.NETS[2][1]
    net_3 = io_conf.NETS[2][2]
    net_4 = io_conf.NETS[2][3]
    static_ip = network_helper.create_random_ips(num_of_ips=1)

    @polarion("RHEVM3-4380")
    def test_01_check_invalid_ips(self):
        """
        Negative: Trying to create networks with invalid IPs
        (Creation should fail)
        """
        invalid_ips = [
            "1.1.1.260",
            "1.1.260.1",
            "1.260.1.1",
            "260.1.1.1",
            "1.2.3",
            "1.1.1.X",
        ]

        for invalid_ip in invalid_ips:
            local_dict = {
                "add": {
                    "1": {
                        "network":  self.net_1,
                        "nic": conf.HOST_0_NICS[1],
                        "ip": {
                            "1": {
                                "address": invalid_ip,
                                "netmask": "255.255.255.0",
                                "boot_protocol": "static"
                            }
                        }
                    }
                }
            }
            testflow.step(
                "Try to create network with invalid IP %s", invalid_ip
            )
            assert not hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **local_dict
            )

    def test_02_check_invalid_netmask(self):
        """
        Negative: Trying to create networks with invalid netmask
        """
        invalid_netmasks = [
            "255.255.255.260",
            "255.255.260.0",
            "255.260.255.0",
            "260.255.255.0",
            "255.255.255.",
            "255.255.255.X",
        ]

        for invalid_netmask in invalid_netmasks:
            local_dict = {
                "add": {
                    "1": {
                        "network": self.net_2,
                        "nic": conf.HOST_0_NICS[2],
                        "ip": {
                            "1": {
                                "address": "1.1.1.1",
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
            assert not hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **local_dict
            )

    @polarion("RHEVM3-4378")
    def test_03_check_netmask_without_ip(self):
        """
        Negative: Trying to create a network with netmask but without an
        IP address
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net_3,
                    "nic": conf.HOST_0_NICS[3],
                    "ip": {
                        "1": {
                            "netmask": "255.255.255.0",
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        testflow.step(
            "Try to create a network %s with netmask 255.255.255.0 but "
            "without an IP address", self.net_3
        )
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )

    @polarion("RHEVM3-4371")
    def test_04_check_static_ip_without_netmask(self):
        """
        Negative: Trying to create a network with static IP but without netmask
        """
        local_dict = {
            "add": {
                "1": {
                    "network": self.net_4,
                    "nic": conf.HOST_0_NICS[4],
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
            self.net_4, self.static_ip
        )
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )


@attr(tier=2)
class TestIOTest03(NetworkTest):
    """
    Positive: Create network and edit its name to valid name.
    Negative: Try to edit its name to invalid name.
    Positive: change network VLAN tag to valid VLAN tag.
    Negative: change network VLAN tag to invalid VLAN tag.
    Positive: Change VM network to be non-VM network.
    Positive: Change non-VM network to be VM network.
    """

    initial_name = io_conf.NETS[3][0]
    valid_name = "C3_NET_changed"

    __test__ = True

    @polarion("RHEVM3-4374")
    def test_01_edit_network_name(self):
        """
        Positive: Should succeed editing network to valid name
        """

        testflow.step(
            "Update network %s and edit its name to valid name %s",
            self.initial_name, self.valid_name
        )
        assert ll_networks.update_network(
            positive=True, network=self.initial_name, name=self.valid_name
        )

    @polarion("RHEVM3-14745")
    def test_02_edit_network_name_to_invalid_name(self):
        """
        Negative: Should fail to edit networks with invalid name
        """
        invalid_name = "inv@lidName"

        testflow.step(
            "Try to edit valid network name %s to invalid name %s",
            self.valid_name, invalid_name
        )
        assert ll_networks.update_network(
            positive=False, network=self.valid_name, name=invalid_name
        )

    @polarion("RHEVM3-4373")
    def test_03_check_valid_vlan_tag(self):
        """
        Positive: Should succeed editing network to valid VLAN tags
        """
        valid_tags = [2, 3, 15, 444, 4093]

        testflow.step(
            "Change network %s VLAN tag to valid VLAN tag %s",
            self.valid_name, valid_tags
        )
        for valid_tag in valid_tags:
            assert ll_networks.update_network(
                positive=True, network=self.valid_name, vlan_id=valid_tag
            )

    @polarion("RHEVM3-14746")
    def test_04_check_invalid_vlan_tag(self):
        """
        Negative: Should fail to edit networks with invalid VLAN tags
        """
        invalid_tags = [-1, 4099]

        testflow.step(
            "Try to edit network %s with invalid VLAN tags %s",
            self.valid_name, invalid_tags
        )
        for invalid_tag in invalid_tags:
            assert ll_networks.update_network(
                positive=False, network=self.valid_name, vlan_id=invalid_tag
            )

    @polarion("RHEVM3-4372")
    def test_05_edit_vm_network(self):
        """
        Positive: Should succeed changing VM network to non-VM network
        """
        testflow.step(
            "Change VM network %s to be non-VM network", self.valid_name
        )
        assert ll_networks.update_network(
            positive=True, network=self.valid_name, usages="",
            description="nonVM network"
        )

        testflow.step(
            "Change non-VM network %s to be VM network", self.valid_name
        )
        assert ll_networks.update_network(
            positive=True, network=self.valid_name, usages="vm",
            description="VM network again"
        )


@attr(tier=2)
@pytest.mark.incremental
class TestIOTest04(NetworkTest):
    """
    Check network label limitation:
    1) Positive case: Create label with length of 50 chars
    2) Positive case: Assign many labels to interface (10)
    3) Negative case: Try to create a label which does not comply with the
        pattern: numbers, digits, dash or underscore [0-9a-zA-Z_-].
    4) Negative case: Try to assign more than one label to network

    """
    __test__ = True
    net_1 = io_conf.NETS[4][0]
    net_2 = io_conf.NETS[4][1]
    label_1 = io_conf.LABEL_NAME[4][0]
    label_2 = io_conf.LABEL_NAME[4][1]

    @polarion("RHEVM3-16952")
    def test_01_label_with_50_characters(self):
        """
        1) Attach label with 50 characters to a network.
        2) Attach 10 labels to the interface on the Host when one of those
        networks is attached to the network
        """
        long_label = "a" * 50
        testflow.step(
            "Attach label with 50 characters to a network %s", self.net_1
        )
        label_dict = {
            long_label: {
                "networks": [self.net_1]
            }
        }
        assert ll_networks.add_label(**label_dict)

    @polarion("RHEVM3-14807")
    def test_02_label_non_restriction(self):
        testflow.step(
            "Attach 10 labels %s to the interface on the Host %s",
            io_conf.LABEL_NAME[4][1:], conf.HOST_0_NAME,
        )
        for label in io_conf.LABEL_NAME[4][1:]:
            label_dict = {
                label: {
                    "host": conf.HOST_0_NAME,
                    "nic": conf.HOST_0_NICS[5]
                }
            }
            assert ll_networks.add_label(**label_dict)

    @polarion("RHEVM3-14806")
    def test_03_label_restriction(self):
        """
        Negative case Try to attach label with incorrect format to the
        network
        """
        special_char_labels = ["asd?f", "dfg/gd"]
        testflow.step(
            "Try to attach label with incorrect format %s to the network %s",
            special_char_labels, self.net_2
        )
        for label in special_char_labels:
            label_dict = {
                label: {
                    "networks": [self.net_2]
                }
            }
            assert not ll_networks.add_label(**label_dict)

    @polarion("RHEVM3-16953")
    def test_04_assign_more_than_one_label_to_network(self):
        """
        Negative case: Try to assign additional label to the network with
        attached label
        """
        testflow.step(
            "Try to assign additional label %s to the network %s"
            " with attached label %s", self.label_2, self.net_1, self.label_1
        )
        label_dict = {
            self.label_2: {
                "networks": [self.net_1]
            }
        }
        assert not ll_networks.add_label(**label_dict)
