
"""
Testing Input/Output feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Positive and negative cases for creating/editing networks
with valid/invalid names, IPs, netmask, VLAN, usages.
"""
import logging
import helper
import config as conf
from art.unittest_lib import attr, NetworkTest
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network


logger = logging.getLogger("IO_Test_Cases")


@attr(tier=2)
class TestIOTestCaseBase(NetworkTest):
    """
    Base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the host
        """
        network_helper.remove_networks_from_host()


class TestIOTest01(TestIOTestCaseBase):
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

            if not hl_networks.createAndAttachNetworkSN(
                data_center=conf.DC_0, cluster=conf.CL_0,
                network_dict=local_dict
            ):
                raise conf.NET_EXCEPTION()

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
            if not ll_networks.add_network(
                positive=False, name=network_name, data_center=conf.DC_0,
            ):
                raise conf.NET_EXCEPTION()


class TestIOTest02(TestIOTestCaseBase):
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

            if hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **local_dict
            ):
                raise conf.NET_EXCEPTION()


class TestIOTest03(TestIOTestCaseBase):
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
            if hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **local_dict
            ):
                raise conf.NET_EXCEPTION()


class TestIOTest04(TestIOTestCaseBase):
    """
    Negative: Trying to create a network with netmask but without an ip address
    """
    __test__ = True
    netmask = ["255.255.255.0"]
    net = conf.NETS[4][0]

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

        if hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        ):
            raise conf.NET_EXCEPTION()


class TestIOTest05(TestIOTestCaseBase):
    """
    Negative: Trying to create a network with static ip but without netmask
    """
    __test__ = True
    static_ip = network_helper.create_random_ips(num_of_ips=1)
    net = conf.NETS[5][0]

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

        if hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        ):
            raise conf.NET_EXCEPTION()


class TestIOTest06(TestIOTestCaseBase):
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

        helper.create_networks(positive=True, params=valid_mtus, type="mtu")

    @polarion("RHEVM3-14743")
    def test_check_invalid_mtu(self):
        """
        Negative: Trying to create a network with invalid MTUs - should fail.
        """
        invalid_mtus = [-5, 67, 2147483648]

        helper.create_networks(positive=False, params=invalid_mtus, type="mtu")


class TestIOTest07(TestIOTestCaseBase):
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

        if hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, network_dict=local_dict
        ):
            raise conf.NET_EXCEPTION()


class TestIOTest08(TestIOTestCaseBase):
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

        helper.create_networks(
            positive=True, params=valid_vlan_ids, type="vlan_id"
        )

    @polarion("RHEVM3-14744")
    def test_check_invalid_vlan_ids(self):
        """
        Negative: Trying to create networks with invalid VLAN IDs.
        """
        invalid_vlan_ids = [-10, 4095, 4096]

        helper.create_networks(
            positive=False, params=invalid_vlan_ids, type="vlan_id"
        )


class TestIOTest09(TestIOTestCaseBase):
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

    @classmethod
    def setup_class(cls, initial_name=initial_name):
        """
        Create network in data center with valid name
        """
        local_dict = {
            initial_name: {}
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, network_dict=local_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4374")
    def test_edit_network_name(self, initial_name=initial_name):
        """
        Positive: Should succeed editing network to valid name
        """
        valid_name = "NET_changed"

        if not ll_networks.updateNetwork(
            positive=True, network=initial_name, name=valid_name
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14745")
    def test_edit_network_name_to_invalid_name(self):
        """
        Negative: Should fail to edit networks with invalid name
        """
        valid_name = "NET_changed"
        invalid_name = "inv@lidName"

        if not ll_networks.updateNetwork(
            positive=False, network=valid_name, name=invalid_name
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4373")
    def test_check_valid_vlan_tag(self, default_name=initial_name):
        """
        Positive: Should succeed editing network to valid VLAN tags
        """
        valid_tags = [2, 3, 15, 444, 4093]

        for valid_tag in valid_tags:
            if not ll_networks.updateNetwork(
                positive=True, network=default_name, vlan_id=valid_tag
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14746")
    def test_check_invalid_vlan_tag(self, default_name=initial_name):
        """
        Negative: Should fail to edit networks with invalid VLAN tags
        """
        invalid_tags = [-1, 4099]

        for invalid_tag in invalid_tags:
            if not ll_networks.updateNetwork(
                positive=False, network=default_name, vlan_id=invalid_tag
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4372")
    def test_edit_vm_network(self):
        """
        Positive: Should succeed changing VM network to non-VM network
        """
        valid_name = "NET_changed"

        if not ll_networks.updateNetwork(
            positive=True, network=valid_name, usages="",
            description="nonVM network"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.updateNetwork(
            positive=True, network=valid_name, usages="vm",
            description="VM network again"
        ):
            raise conf.NET_EXCEPTION()
