
"""
Testing Input/Output feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Positive and negative cases for creating/editing networks
with valid/invalid names, IPs, netmask, VLAN, usages.
"""
import logging
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level.networks import(
    addNetwork, addNetworkToCluster, updateNetwork,
    create_network_in_datacenter
)
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking import config

logger = logging.getLogger("IO_Test_Cases")

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class TestIOTestCaseBase(TestCase):
    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup and clean up host
        """
        logger.info("Starting teardown")
        if not remove_net_from_setup(
                host=config.HOSTS[0], data_center=config.DC_NAME[0],
                all_net=True, mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Cannot remove network from setup")


@attr(tier=2)
class TestIOTest01(TestIOTestCaseBase):
    """
    Positive: Creating & adding networks with valid names to the cluster
    Negative: Trying to create networks with invalid names
    """
    __test__ = True

    @polarion("RHEVM3-4381")
    def test_check_network_names(self):
        """
        Positive: Should succeed creating networks with valid names
        Negative: Should fail to create networks with invalid names
        """
        valid_names = [
            "endsWithNumber1",
            "nameMaxLengthhh",
            "1startsWithNumb",
            "1a2s3d4f5g6h",
            "01234567891011",
            "______",
        ]
        invalid_names = [
            "networkWithMoreThanFifteenChars",
            "inv@lidName",
            "________________",
            "bond",
            "",
        ]

        for networkName in valid_names:
            logger.info(
                "Trying to create networks with the name %s", networkName,
            )
            if not addNetwork(
                    positive=True, name=networkName,
                    data_center=config.DC_NAME[0]
            ):
                raise NetworkException(
                    "The network %s was not created although it should have" %
                    networkName
                )

            logger.info(
                "Trying to add %s to cluster %s",
                networkName, config.CLUSTER_NAME[0],
            )
            if not addNetworkToCluster(
                    positive=True, network=networkName,
                    cluster=config.CLUSTER_NAME[0]
            ):
                raise NetworkException(
                    "Cannot add network %s to Cluster" % networkName
                )
        for networkName in invalid_names:
            logger.info(
                "Trying to create networks with the name %s - should fail",
                networkName
            )
            if addNetwork(
                    positive=True,
                    name=networkName,
                    data_center=config.DC_NAME[0]
            ):
                raise NetworkException(
                    "The network %s was created although it shouldn't have" %
                    networkName
                )


@attr(tier=2)
class TestIOTest02(TestIOTestCaseBase):
    """
    Negative: Trying to create networks with invalid IPs
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Add new network
        """
        local_dict = {"invalid_ips": {"required": "false"}}

        logger.info("Add Network to setup")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create new Network")

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
            logger.info(
                "Trying to create a network with invalid IP %s",
                invalid_ip,
            )

            local_dict = {
                "invalid_ips": {
                    "nic": 1,
                    "bootproto": "static",
                    "address": invalid_ip,
                    "netmask": ["255.255.255.0"],
                    "required": "false",
                },
            }

            if createAndAttachNetworkSN(
                host=config.VDS_HOSTS[0], network_dict=local_dict,
                auto_nics=[0]
            ):
                raise NetworkException(
                    "Network with invalid IP (%s) was created" % invalid_ip
                )


@attr(tier=2)
class TestIOTest03(TestIOTestCaseBase):
    """
    Negative: Trying to create networks with invalid netmask
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Add new network
        """
        local_dict = {
            "invalid_netmask": {
                "required": "false",
            },
        }

        logger.info("Add Network to setup")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict,
        ):
            raise NetworkException("Cannot create new Network")

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
            logger.info(
                "Trying to create a network with netmask %s", invalid_netmask,
            )

            local_dict = {
                "invalid_netmask": {
                    "nic": 1, "bootproto": "static", "address": ["1.1.1.1"],
                    "netmask": invalid_netmask, "required": "false"
                }
            }

            if createAndAttachNetworkSN(
                host=config.VDS_HOSTS[0], network_dict=local_dict,
                auto_nics=[0]
            ):
                raise NetworkException(
                    "Network invalid_netmask with invalid ip (%s) was created"
                    % invalid_netmask
                )


@attr(tier=2)
class TestIOTest04(TestIOTestCaseBase):
    """
    Negative: Trying to create a network with netmask but without an ip address
    """
    __test__ = True

    @polarion("RHEVM3-4378")
    def test_check_netmask_without_ip(self):
        """
        Negative: Trying to create a network with netmask but without an
        IP address
        """
        logger.info(
            "Trying to create a network with netmask but without ip address"
        )
        local_dict = {
            "netmaskWithNoIP": {
                "nic": 1,
                "bootproto": "static",
                "netmask": ["255.255.255.0"],
                "required": "false"
            }
        }
        if createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Network without ip was created although it shouldn't have"
            )


@attr(tier=2)
class TestIOTest05(TestIOTestCaseBase):
    """
    Negative: Trying to create a network with static ip but without netmask
    """
    __test__ = True

    @polarion("RHEVM3-4371")
    def test_check_static_ip_without_netmask(self):
        """
        Negative: Trying to create a network with static IP but without netmask
        """
        logger.info(
            "Trying to create a network with static ip but without netmask"
        )
        local_dict = {
            "ipWithNoNetmask": {
                "nic": 1, "bootproto": "static", "address": ["1.1.1.1"],
                "required": "false"
            }
        }
        if createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Network without netmask was created although it shouldn't "
                "have"
            )


@attr(tier=2)
class TestIOTest06(TestIOTestCaseBase):
    """
    Positive: Creating networks with valid MTU and adding them to a cluster.
    Negative: Trying to create a network with invalid MTUs - should fail.
    """
    __test__ = True

    @polarion("RHEVM3-4377")
    def test_check_mtu(self):
        """
        Positive: Creating networks with valid MTUs and adding them to a
        cluster.
        Negative: Trying to create a network with invalid MTUs - should fail.
        """
        # as per #BZ 1010663, upper capping for MTU was removed, rising tested
        # MTUs

        valid_mtus = [68, 69, 9000, 65520, 2147483647]
        invalid_mtus = [-5, 67, 2147483648]
        for index_1, invalid_mtu in enumerate(invalid_mtus):
            logger.info(
                "Trying to create networks with mtu = %s - Should fail.",
                invalid_mtu,
            )
            if addNetwork(
                positive=True, name="invalid_mtu%s" % index_1, mtu=invalid_mtu,
                data_center=config.DC_NAME[0]
            ):
                raise NetworkException(
                    "Network with mtu = %s was created although it shouldn't"
                    " have" % invalid_mtu
                )

        for index_2, valid_mtu in enumerate(valid_mtus):
            logger.info("Creating networks with mtu = %s", valid_mtu)
            if not addNetwork(
                positive=True, name="valid_mtu%s" % index_2, mtu=valid_mtu,
                data_center=config.DC_NAME[0]
            ):
                raise NetworkException(
                    "Network with mtu = %s was not created" % valid_mtu
                )

            logger.info(
                "Adding valid_mtu%s to cluster %s", index_2,
                config.CLUSTER_NAME[0]
            )
            if not addNetworkToCluster(
                positive=True, network="valid_mtu%s" % index_2,
                cluster=config.CLUSTER_NAME[0]
            ):
                raise NetworkException(
                    "Cannot add network valid_mtu%s to Cluster" % index_2
                )


@attr(tier=2)
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
        usages = "Unknown"
        logger.info("Trying to create network with usages = %s", usages)
        if addNetwork(
            positive=True, name="invalid_usage", usages=usages,
            data_center=config.DC_NAME[0]
        ):
            raise NetworkException(
                "Network with usages = %s was created" % usages
            )


@attr(tier=2)
class TestIOTest08(TestIOTestCaseBase):
    """
    Positive: Creating networks with valid VLAN IDs & adding them to a cluster.
    Negative: Trying to create networks with invalid VLAN IDs.
    """
    __test__ = True

    @polarion("RHEVM3-4375")
    def test_check_vlan_ids(self):
        """
        Positive: Creating networks with valid VLAN IDs & adding them to a
        cluster.
        Negative: Trying to create networks with invalid VLAN IDs.
        """
        valid_vlan_ids = [4094, 1111, 111, 11, 1, 0]
        invalid_vlan_ids = [-10, 4095, 4096]
        for invalid_index, vlan_id in enumerate(invalid_vlan_ids):
            logger.info(
                "Trying to create network with vlan id = %s - should fail",
                vlan_id
            )
            if addNetwork(
                positive=True,
                name="invalid_vlan_id%s" % invalid_index,
                vlan_id=vlan_id,
                data_center=config.DC_NAME[0],
            ):
                raise NetworkException(
                    "Network with VLAN id = %s was created although "
                    "it shouldn't have (Valid range = [0,4094])" % vlan_id
                )

        for valid_index, vlan_id in enumerate(valid_vlan_ids):
            logger.info(
                "Creating network with vlan id = %s", vlan_id,
            )
            if not addNetwork(
                positive=True,
                name="valid_vlan_id%s" % valid_index,
                vlan_id=vlan_id,
                data_center=config.DC_NAME[0],
            ):
                raise NetworkException(
                    "Network with VLAN ID %s was not created although "
                    "it should have" % vlan_id
                )

            logger.info(
                "Adding valid VLAN ID %s to cluster %s",
                vlan_id,
                config.CLUSTER_NAME[0],
            )
            if not addNetworkToCluster(
                positive=True,
                network="valid_vlan_id%s" % valid_index,
                cluster=config.CLUSTER_NAME[0]
            ):
                raise NetworkException(
                    "Cannot add network %s to Cluster %s" % (
                        vlan_id,
                        config.CLUSTER_NAME[0],
                    )
                )


@attr(tier=2)
class TestIOTest09(TestIOTestCaseBase):
    """
    Positive: Create network and edit its name to valid name
    Negative: Try to edit its name to invalid name
    """
    initial_name = "NET_default"

    __test__ = True

    @classmethod
    def setup_class(cls, initial_name=initial_name):
        """
        Create network in data center with valid name and description
        """
        kwargs_dict = {
            "name": initial_name,
            "description": "network with initial valid name",
        }

        logger.info(
            "Creating network %s on data center %s",
            initial_name,
            config.DC_NAME[0],
        )
        if not create_network_in_datacenter(
            True,
            config.DC_NAME[0],
            **kwargs_dict
        ):
            raise NetworkException(
                "Failed to create %s network on %s" % (
                    initial_name,
                    config.DC_NAME[0],
                )
            )

    @polarion("RHEVM3-4374")
    def test_edit_network_name(self, initial_name=initial_name):
        """
        Positive: Should succeed editing network to valid name
        Negative: Should fail to edit networks with invalid names
        """

        valid_name = "NET_changed"
        invalid_name = "inv@lidName"

        logger.info(
            "Trying to change name of network %s to %s - should succeed",
            initial_name,  valid_name,
        )
        if not updateNetwork(
            positive=True, network=initial_name, name=valid_name,
            description="network with changed name"
        ):
            raise NetworkException(
                "Failed to change the name of network %s to %s" %
                (initial_name, valid_name)
            )

        logger.info(
            "Trying to change name of network %s to %s - should fail",
            valid_name, invalid_name
        )
        if updateNetwork(
            positive=True, network=valid_name, name=invalid_name
        ):
            raise NetworkException(
                "Changed the name of network %s to %s - should fail" %
                (valid_name, invalid_name)
            )


@attr(tier=2)
class TestIOTest10(TestIOTestCaseBase):
    """
    Positive: change network VLAN tag to valid VLAN tag
    Negative: change network VLAN tag to invalid VLAN tag
    """
    __test__ = True

    default_name = "NET_edit_tag"

    @classmethod
    def setup_class(cls, default_name=default_name):
        """
        Create network in the data center with valid name and description
        """
        kwargs_dict = {
            "name": default_name,
            "description": "initial network with valid name without VLAN ID",
        }

        logger.info(
            "Creating network %s on data center %s",
            default_name, config.DC_NAME[0]
        )

        if not create_network_in_datacenter(
            True, config.DC_NAME[0], **kwargs_dict
        ):
            raise NetworkException(
                "Failed to create %s network on %s" %
                (default_name, config.DC_NAME[0])
            )

    @polarion("RHEVM3-4373")
    def test_edit_network_tag(self, default_name=default_name):
        """
        Positive: Should succeed editing network to valid VLAN tags
        Negative: Should fail to edit networks with invalid VLAN tags
        """
        valid_tags = [0, 1, 15, 444, 4094]
        invalid_tags = [-1, 4099]

        for valid_tag in valid_tags:
            logger.info(
                "Change VLAN tag of network %s to %s - should succeed",
                default_name, valid_tag
            )
            if not updateNetwork(
                positive=True, network=default_name, vlan_id=valid_tag
            ):
                raise NetworkException(
                    "Failed to change VLAN tag of network %s to %s" %
                    (default_name, valid_tag)
                )

        for invalid_tag in invalid_tags:
            logger.info(
                "Trying to change VLAN tag of network %s to %s - should fail",
                default_name, invalid_tag
            )
            if updateNetwork(
                positive=True, network=default_name, vlan_id=invalid_tag
            ):
                raise NetworkException(
                    "Changed the VLAN tag of network %s to %s - should fail" %
                    (default_name, invalid_tag)
                )


@attr(tier=2)
class TestIOTest11(TestIOTestCaseBase):
    """
    Positive: Change VM network to be non-VM network
    Positive: Change non-VM network to be VM network
    """
    __test__ = True

    default_name = "VM_network"

    @classmethod
    def setup_class(cls, default_name=default_name):
        """
        Create network in the  Data center with valid name and valid
        description
        """
        kwargs_dict = {
            "name": default_name,
            "description": "VM network",
        }

        logger.info(
            "Creating VM network %s on data center %s",
            default_name, config.DC_NAME[0],
        )

        if not create_network_in_datacenter(
            True, config.DC_NAME[0], **kwargs_dict
        ):
            raise NetworkException(
                "Failed to create %s network in DC %s" %
                (default_name, config.DC_NAME[0])
            )

    @polarion("RHEVM3-4372")
    def test_edit_vm_network(self, default_name=default_name):
        """
        Positive: Should succeed changing VM network to non-VM network
        """
        logger.info(
            "Trying to change VM network %s to nonVM network - should succeed",
            default_name
        )
        if not updateNetwork(
            positive=True, network=default_name, usages="",
            description="nonVM network"
        ):
            raise NetworkException(
                "Failed to change network %s to nonVM network" % default_name
            )

        logger.info(
            "Trying to change nonVM network %s back to be VM network - "
            "it should succeed", default_name
        )
        if not updateNetwork(
            positive=True, network=default_name, usages="vm",
            description="VM network again"
        ):
            raise NetworkException(
                "Failed to change network %s to VM network" % default_name
            )
