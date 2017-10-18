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
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    hosts as ll_hosts
)
import config as io_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    NetworkTest,
    testflow,
    tier2,
)
from rhevmtests import helpers
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.fixture(scope="class")
def attach_label_to_network(request):
    """
    Attach label to network
    """
    network = request.node.cls.net_4
    label = request.node.cls.label_1
    label_dict = {
        label: {
            "networks": [network]
        }
    }
    testflow.setup("Attach label %s to network %s", label, network)
    assert ll_networks.add_label(**label_dict)


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
    test_1_valid_names = [
        {
            "name": [
                "endsWithNumber1",
                "nameMaxLengthhh",
                "1startsWithNumb",
                "1a2s3d4f5g6h",
                "01234567891011",
                "______",
                "networkWithMoreThanFifteenChars",
                "inv@lidName",
                "________________",
            ]
        }, True
    ]

    # Test 2 params - invalid network names
    test_2_invalid_names = [
        {
            "name": [
                "bond",
                "",
            ]
        }, False
    ]

    # Test 3 params - valid network MTU
    test_3_valid_mtu = [
        {
            "mtu": [68, 69, 9000, 65520, 2147483647]
        }, True
    ]

    # Test 4 params - invalid network MTU
    test_4_invalid_mtu = [
        {
            "mtu": [-5, 67, 2147483648]
        }, False
    ]

    # Test 5 params - invalid network usages
    test_5_invalid_usages = [
        {
            "usages": ["Unknown"]
        }, False
    ]

    # Test 6 params - valid network VLAN
    test_6_valid_vlan = [
        {
            "vlan_id": [4094, 1111, 111, 11, 1, 0]
        }, True
    ]

    # Test 7 params - invalid network VLAN
    test_7_invalid_vlan = [
        {
            "vlan_id": [-10, 4095, 4096]
        }, False
    ]

    # Test 8 params - valid network names with dash (-)
    test_8_valid_dash_name = [
        {
            "name": ["net-155", "net-1-5-5-b----", "m-b_1-2_3_4-3_5"]
        }, True
    ]

    @tier2
    @pytest.mark.parametrize(
        ("test_params", "positive"),
        [
            pytest.param(
                *test_1_valid_names, marks=(
                    (polarion("RHEVM3-4381"), bz({"1458407": {}}))
                    )
                ),
            pytest.param(
                *test_2_invalid_names, marks=(polarion("RHEVM3-14742"))
            ),
            pytest.param(*test_3_valid_mtu, marks=(polarion("RHEVM3-4377"))),
            pytest.param(
                *test_4_invalid_mtu, marks=(polarion("RHEVM3-14743"))
            ),
            pytest.param(
                *test_5_invalid_usages, marks=(polarion("RHEVM3-4376"))
            ),
            pytest.param(*test_6_valid_vlan, marks=(polarion("RHEVM3-4375"))),
            pytest.param(
                *test_7_invalid_vlan, marks=(polarion("RHEVM3-14744"))
            ),
            pytest.param(
                *test_8_valid_dash_name, marks=(polarion("RHEVM3-11877"))
            ),
        ],
        ids=[
            "Create_valid_names",
            "Try_to_create_invalid_names",
            "Create_valid_MTU",
            "Try_to_create_invalid_MTU",
            "Try_to_create_invalid_usages",
            "Create_valid_VLANs",
            "Try_to_invalid_VLANs",
            "Create_valid_dash_names"

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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__
)
class TestIOTest02(NetworkTest):
    """
    1. Negative: Trying to create networks with invalid IPs.
    2. Negative: Trying to create networks with invalid netmask.
    3. Negative: Trying to create a network with netmask but without an
        ip address.
    4. Negative: Trying to create a network with static ip but without netmask.
    5. Create networks with valid netmask.
    """
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": io_conf.CASE_2_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # clean_host_interfaces fixture
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

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
    test_01 = [net_1, test_1_invalid_ips]

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
    test_02 = [net_2, test_2_invalid_mask]

    # Test 3 params - netmask without network IP
    net_3 = io_conf.NETS[2][2]
    test_3_no_ip = {
        "netmask": ["255.255.255.0"]
    }
    test_03 = [net_3, test_3_no_ip]

    # Test 4 params - IP without network netmask
    net_4 = io_conf.NETS[2][3]
    test_4_no_mask = {
        "address": ["1.2.3.1"]
    }
    test_04 = [net_4, test_4_no_mask]

    # Test 5 params - valid network netmask
    net_5 = io_conf.NETS[2][4]
    test_5_valid_mask = {
        "netmask": ["255.255.255.0"]
    }
    test_05 = [net_5, test_5_valid_mask]

    # Test 6 params - invalid network gateway
    net_6 = io_conf.NETS[2][5]
    test_6_invalid_gateway = {
        "gateway": ["5.5.5.298"]
    }
    test_06 = [net_6, test_6_invalid_gateway]

    @tier2
    @pytest.mark.parametrize(
        ("network", "test_params"),
        [
            pytest.param(*test_01, marks=(polarion("RHEVM3-4380"))),
            pytest.param(*test_02, marks=(polarion("RHEVM3-19162"))),
            pytest.param(*test_03, marks=(polarion("RHEVM3-4378"))),
            pytest.param(*test_04, marks=(polarion("RHEVM3-4371"))),
            pytest.param(*test_05, marks=(polarion("RHEVM3-19164"))),
            pytest.param(*test_06, marks=(polarion("RHEVM3-3958"))),
        ],
        ids=[
            "invalid_IPs",
            "invalid_netmask",
            "netmask_without_IP",
            "IP_without_netmask",
            "valid_netmask",
            "invalid_gateway"
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__
)
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
    valid_name_1 = "C3_NET_changed%s" + "_" * 240
    valid_name_2 = "inv@lidName" + "!" * 245
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": io_conf.CASE_3_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # clean_host_interfaces fixture
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # Test 1 params - edit network name to valid name
    test_1_edit_name_valid = [
        {
            "name": [valid_name_1]
        }, True
    ]

    # Test 2 params - edit network name to valid name special characters
    test_2_edit_name_valid_special_characters = [
        {
            "name": [valid_name_2]
        }, True
    ]

    # Test 3 params - edit network name to invalid name
    test_3_edit_name_invalid = [
        {
            "name": ["io_net_%s" % "_" * 300]
        }, False
    ]

    # Test 4 params - edit network with valid VLAN
    test_4_edit_valid_vlan = [
        {
            "vlan_id": [2, 3, 15, 444, 4093]
        }, True
    ]

    # Test 5 params - edit network with invalid VLAN
    test_5_edit_invalid_vlan = [
        {
            "vlan_id": [-10, 4095, 4096]
        }, False
    ]

    # Test 6 params - edit network usages
    test_6_edit_valid_usages = [
        {
            "usages": [""]
        }, True
    ]

    @tier2
    @pytest.mark.parametrize(
        ("test_params", "positive"),
        [
            pytest.param(
                *test_1_edit_name_valid, marks=(
                    (polarion("RHEVM-21967"), bz({"1458407": {}}))
                )
            ),
            pytest.param(
                *test_2_edit_name_valid_special_characters, marks=(
                    (polarion("RHEVM-21968"), bz({"1458407": {}}))
                )
            ),
            pytest.param(
                *test_3_edit_name_invalid, marks=(polarion("RHEVM-21969"))
            ),
            pytest.param(
                *test_4_edit_valid_vlan, marks=(polarion("RHEVM3-4373"))
            ),
            pytest.param(
                *test_5_edit_invalid_vlan, marks=(polarion("RHEVM3-14746"))
            ),
            pytest.param(
                *test_6_edit_valid_usages, marks=(polarion("RHEVM3-4372"))
            ),
        ],
        ids=[
            "Edit_valid_network_name",
            "Edit_valid_network_name_with_special_characters",
            "Try_to_edit_invalid_network_name",
            "Edit_valid_VLAN",
            "Try_to_Edit_invalid_VLAN",
            "Edit_valid_usages"
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
                all_networks = ll_networks.get_all_networks()
                network_to_update = [
                    i.name for i in all_networks if i.name != conf.MGMT_BRIDGE
                ]
                assert network_to_update
                network_to_update = network_to_update[0]
                assert ll_networks.update_network(
                    positive=positive, network=network_to_update,
                    data_center=conf.DC_0, **param_dict
                )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    attach_label_to_network.__name__,
    clean_host_interfaces.__name__
)
class TestIOTest04(NetworkTest):
    """
    Check network label limitation:
    1. Positive case: Create label with length of 50 chars
    2. Positive case: Assign many labels to interface (10)
    3. Negative case: Try to create a label which does not comply with the
        pattern: numbers, digits, dash or underscore [0-9a-zA-Z_-].
    4. Negative case: Try to assign more than one label to network
    """
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": io_conf.CASE_4_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # clean_host_interfaces fixture
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # Test 1 params - label characters on network
    net_1 = io_conf.NETS[4][0]
    label_1 = io_conf.LABEL_NAME[4][0]
    net_1_labels = ["a" * 50]
    test_01 = [net_1, net_1_labels, None, True]

    # Test 2 params - label non_restriction on host NIC
    net_2 = io_conf.NETS[4][1]
    net_2_labels = io_conf.LABEL_NAME[4][1:]
    test_02 = [net_2, net_2_labels, 1, True]

    # Test 3 params - label restriction on network
    net_3 = io_conf.NETS[4][2]
    net_3_labels = ["asd?f", "dfg/gd"]
    test_03 = [net_3, net_3_labels, None, False]

    # Test 4 params - more then 1 label on network
    net_4 = io_conf.NETS[4][3]
    net_4_labels = io_conf.LABEL_NAME[4][:5]
    test_04 = [net_4, net_4_labels, None, False]

    @tier2
    @pytest.mark.parametrize(
        ("network", "labels", "nic", "positive"),
        [
            pytest.param(*test_01, marks=(polarion("RHEVM3-16952"))),
            pytest.param(*test_02, marks=(polarion("RHEVM3-14807"))),
            pytest.param(*test_03, marks=(polarion("RHEVM3-14806"))),
            pytest.param(*test_04, marks=(polarion("RHEVM3-16953"))),
        ],
        ids=[
            "Create_label_with_length_of_50_chars",
            "Assign_many_labels_to_interface_(10)",
            "Try_to_create_invalid_label_names",
            "Try_to_assign_many_labels_on_network"
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
                label_dict[label]["host"] = ll_hosts.get_host_object(
                    host_name=conf.HOST_0_NAME
                )
                label_dict[label]["nic"] = conf.HOST_0_NICS[nic]
            else:
                label_dict[label]["networks"] = [network]

            assert positive == ll_networks.add_label(**label_dict)
