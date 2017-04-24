#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Input/Output feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Positive and negative cases for creating/editing networks
with valid/invalid names, IPs, netmask, VLAN, usages.
"""

import pytest

import art.core_api.apis_exceptions as exceptions
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as io_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from rhevmtests import helpers
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def attach_label_to_network(request):
    """
    Attach label to network
    """
    network = request.node.cls.net_4
    label = io_conf.LABEL_NAME[4][0]
    label_dict = {
        label: {
            "networks": [network]
        }
    }
    testflow.setup("Attach label %s to network %s", label, network)
    assert ll_networks.add_label(**label_dict)


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
    1. Positive: Creating & adding networks with valid names to the cluster.
    2. Negative: Trying to create networks with invalid names.
    3. Positive: Creating networks with valid MTU and adding them to
        data center.
    4. Negative: Trying to create a network with invalid MTUs.
    5. Negative: Trying to create a network with invalid usages value.
    6. Positive: Creating networks with valid VLAN IDs & adding them to a DC.
    7. Negative: Trying to create networks with invalid VLAN IDs.
    """
    # Test 1 params - valid network names
    test_1_valid_names = {
        "name": [
            "endsWithNumber1",
            "nameMaxLengthhh",
            "1startsWithNumb",
            "1a2s3d4f5g6h",
            "01234567891011",
            "______",
        ]
    }

    # Test 2 params - invalid network names
    test_2_invalid_names = {
        "name": [
            "networkWithMoreThanFifteenChars",
            "inv@lidName",
            "________________",
            "bond",
            "",
        ]
    }

    # Test 3 params - valid network MTU
    test_3_valid_mtu = {
        "mtu": [68, 69, 9000, 65520, 2147483647]
    }

    # Test 4 params - invalid network MTU
    test_4_invalid_mtu = {
        "mtu": [-5, 67, 2147483648]
    }

    # Test 5 params - invalid network usages
    test_5_invalid_usages = {
        "usages": ["Unknown"]
    }

    # Test 6 params - valid network VLAN
    test_6_valid_vlan = {
        "vlan_id": [4094, 1111, 111, 11, 1, 0]
    }

    # Test 7 params - invalid network VLAN
    test_7_invalid_vlan = {
        "vlan_id": [-10, 4095, 4096]
    }

    # Test 8 params - valid network names with dash (-)
    test_8_valid_dash_name = {
        "name": ["net-155", "net-1-5-5-b----", "m-b_1-2_3_4-3_5"]
    }

    @pytest.mark.parametrize(
        ("test_params", "positive"),
        [
            polarion("RHEVM3-4381")([test_1_valid_names, True]),
            polarion("RHEVM3-14742")([test_2_invalid_names, False]),
            polarion("RHEVM3-4377")([test_3_valid_mtu, True]),
            polarion("RHEVM3-14743")([test_4_invalid_mtu, False]),
            polarion("RHEVM3-4376")([test_5_invalid_usages, False]),
            polarion("RHEVM3-4375")([test_6_valid_vlan, True]),
            polarion("RHEVM3-14744")([test_7_invalid_vlan, False]),
            polarion("RHEVM3-11877")([test_8_valid_dash_name, True]),
        ],
        ids=[
            "Create valid names",
            "Try to create invalid names",
            "Create valid MTU",
            "Try to create invalid MTU",
            "Try to create invalid usages",
            "Create valid VLANs",
            "Try to invalid VLANs",
            "Create valid dash names"

        ]

    )
    def test_create_networks(self, test_params, positive):
        """
        Create network with valid and invalid name, MTU, VLAN and usages
        """
        type_ = test_params.keys()[0]
        network_params = test_params.get(type_)
        _id = helpers.get_test_parametrize_ids(
            item=self.test_create_networks.parametrize,
            params=[test_params, positive]
        )
        testflow.step(_id)
        for network_param in network_params:
            param = {type_: network_param}
            if type_ != "name":
                param["name"] = "io-%s" % str(network_param)

            assert ll_networks.add_network(
                positive=positive, data_center=conf.DC_0, **param
            )


@attr(tier=2)
class TestIOTest02(NetworkTest):
    """
    1. Negative: Trying to create networks with invalid IPs.
    2. Negative: Trying to create networks with invalid netmask.
    3. Negative: Trying to create a network with netmask but without an
        ip address.
    4. Negative: Trying to create a network with static ip but without netmask.
    5. Create networks with valid netmask.
    """
    # Test 1 params - invalid network IP
    net_1 = io_conf.NETS[2][0]
    test_1_invalid_ips = {
        "address": [
            "1.1.1.260",
            "1.1.260.1",
            "1.260.1.1",
            "260.1.1.1",
            "1.2.3",
            "1.1.1.X",
        ]
    }

    # Test 2 params - invalid network netmask
    net_2 = io_conf.NETS[2][1]
    test_2_invalid_mask = {
        "netmask": [
            "255.255.255.260",
            "255.255.260.0",
            "255.260.255.0",
            "260.255.255.0",
            "255.255.255.",
            "255.255.255.X",
            "40",
        ]
    }

    # Test 3 params - netmask without network IP
    net_3 = io_conf.NETS[2][2]
    test_3_no_ip = {
        "netmask": ["255.255.255.0"]
    }

    # Test 4 params - IP without network netmask
    net_4 = io_conf.NETS[2][3]
    test_4_no_mask = {
        "address": ["1.2.3.1"]
    }

    # Test 5 params - valid network netmask
    net_5 = io_conf.NETS[2][4]
    test_5_valid_mask = {
        "netmask": ["255.255.255.0"]
    }

    # Test 6 params - invalid network gateway
    net_6 = io_conf.NETS[2][5]
    test_6_invalid_gateway = {
        "gateway": ["5.5.5.298"]
    }

    @pytest.mark.parametrize(
        ("network", "test_params"),
        [
            polarion("RHEVM3-4380")([net_1, test_1_invalid_ips]),
            polarion("RHEVM3-19162")([net_2, test_2_invalid_mask]),
            polarion("RHEVM3-4378")([net_3, test_3_no_ip]),
            polarion("RHEVM3-4371")([net_4, test_4_no_mask]),
            polarion("RHEVM3-19164")([net_5, test_5_valid_mask]),
            polarion("RHEVM3-3958")([net_6, test_6_invalid_gateway]),
        ],
        ids=[
            "invalid IPs",
            "invalid netmask",
            "netmask without IP",
            "IP without netmask",
            "valid netmask",
            "invalid gateway"
        ]
    )
    def test_check_ip(self, network, test_params):
        """
        1. Negative: Trying to create networks with invalid IPs, netmask and
        missing IP or netmask
        2. Create network with valid netmask
        """
        log = (
            "Try to create network %s with invalid %s %s"
            if network != self.net_5 else
            "Create network %s with valid %s %s"
        )
        sn_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }

        if network == self.net_1:
            sn_dict["add"]["1"]["ip"]["1"]["netmask"] = "255.255.255.0"

        if network == self.net_2:
            sn_dict["add"]["1"]["ip"]["1"]["address"] = "1.2.3.2"

        if network == self.net_5:
            sn_dict["add"]["1"]["ip"]["1"]["address"] = "1.2.3.3"

        if network == self.net_6:
            sn_dict["add"]["1"]["ip"]["1"]["address"] = "5.5.5.250"

        for key_, params in test_params.iteritems():
            for param in params:
                sn_dict["add"]["1"]["ip"]["1"][key_] = param
                testflow.step(log, network, key_, param)
                res = hl_host_network.setup_networks(
                    host_name=conf.HOST_0_NAME, **sn_dict
                )
                if network == self.net_5:
                    assert res
                else:
                    assert not res


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
    # General params
    initial_name = io_conf.NETS[3][0]
    valid_name = "C3_NET_changed"

    # Test 1 params - edit network name to valid name
    test_1_edit_name_valid = {
        "name": [valid_name]
        }

    # Test 2 params - edit network name to invalid name
    test_2_edit_name_invalid = {
        "name": ["inv@lidName"]
    }

    # Test 3 params - edit network with valid VLAN
    test_3_edit_valid_vlan = {
        "vlan_id": [2, 3, 15, 444, 4093]
    }

    # Test 4 params - edit network with invalid VLAN
    test_4_edit_invalid_vlan = {
        "vlan_id": [-10, 4095, 4096]
    }

    # Test 5 params - edit network usages
    test_5_edit_valid_usages = {
        "usages": [""]
    }

    @pytest.mark.parametrize(
        ("test_params", "positive"),
        [
            polarion("RHEVM3-4374")([test_1_edit_name_valid, True]),
            polarion("RHEVM3-14745")([test_2_edit_name_invalid, False]),
            polarion("RHEVM3-4373")([test_3_edit_valid_vlan, True]),
            polarion("RHEVM3-14746")([test_4_edit_invalid_vlan, False]),
            polarion("RHEVM3-4372")([test_5_edit_valid_usages, True]),
        ],
        ids=[
            "Edit valid name",
            "Try to edit invalid name",
            "Edit valid VLAN",
            "Try to Edit invalid VLAN",
            "Edit valid usages"
        ]
    )
    def test_update_network(self, test_params, positive):
        """
        Edit network with valid and invalid name, MTU, VLAN and usages
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_update_network.parametrize,
            params=[test_params, positive]
        )
        testflow.step(_id)
        for type_, params in test_params.iteritems():
            for param in params:
                param_dict = {type_: param}
                try:
                    ll_networks.find_network(network=self.valid_name)
                    network_to_update = self.valid_name
                except exceptions.EntityNotFound:
                    network_to_update = self.initial_name

                assert ll_networks.update_network(
                    positive=positive, network=network_to_update,
                    data_center=conf.DC_0, **param_dict
                )


@attr(tier=2)
@pytest.mark.incremental
class TestIOTest04(NetworkTest):
    """
    Check network label limitation:
    1. Positive case: Create label with length of 50 chars
    2. Positive case: Assign many labels to interface (10)
    3. Negative case: Try to create a label which does not comply with the
        pattern: numbers, digits, dash or underscore [0-9a-zA-Z_-].
    4. Negative case: Try to assign more than one label to network

    """
    # Test 1 params - label characters on network
    net_1 = io_conf.NETS[4][0]
    net_1_labels = ["a" * 50]

    # Test 2 params - label non_restriction on host NIC
    net_2 = io_conf.NETS[4][1]
    net_2_labels = io_conf.LABEL_NAME[4][1:]

    # Test 3 params - label restriction on network
    net_3 = io_conf.NETS[4][2]
    net_3_labels = ["asd?f", "dfg/gd"]

    # Test 4 params - more then 1 label on network
    net_4 = io_conf.NETS[4][3]
    net_4_labels = io_conf.LABEL_NAME[4][:5]

    @pytest.mark.usefixtures(attach_label_to_network.__name__)
    @pytest.mark.parametrize(
        ("network", "labels", "nic", "positive"),
        [
            polarion("RHEVM3-16952")([net_1, net_1_labels, None, True]),
            polarion("RHEVM-14807")([net_2, net_2_labels, 1, True]),
            polarion("RHEVM3-14806")([net_3, net_3_labels, None, False]),
            polarion("RHEVM-16953")([net_4, net_4_labels, None, False]),
        ],
        ids=[
            "Create label with length of 50 chars",
            "Assign many labels to interface (10)",
            "Try to create invalid label names",
            "Try to assign many labels on network"
        ]
    )
    def test_labels(self, network, labels, nic, positive):
        """
        Check valid and invalid labels.
        More then one label on host NIC
        Valid names
        Invalid names
        More then one label on network (negative)
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_labels.parametrize,
            params=[network, labels, nic, positive]
        )
        testflow.step(_id)
        for label in labels:
            label_dict = {
                label: dict()
            }
            if nic:
                label_dict[label]["host"] = conf.HOST_0_NAME
                label_dict[label]["nic"] = conf.HOST_0_NICS[nic]
            else:
                label_dict[label]["networks"] = [network]

            assert positive == ll_networks.add_label(**label_dict)
