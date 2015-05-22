"""
Testing Network Custom properties feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Network Custom properties will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
import logging
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN, update_network_host, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level.networks import (
    check_bridge_file_exist, check_bridge_opts, check_ethtool_opts
)

logger = logging.getLogger("Network_Custom_Properties_Cases")
HOST_NICS = None  # filled in setup module

# #######################################################################

# #######################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    """
    Obtain Host Nics
    """
    global HOST_NICS
    HOST_NICS = config.VDS_HOSTS[0].nics


class TestNCPCaseBase(TestCase):
    """
    base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            data_center=config.DC_NAME[0], all_net=True,
            mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Cannot remove networks from setup")


@attr(tier=1)
class TestNetCustPrCase01(TestNCPCaseBase):
    """
    Verify bridge_opts doesn't exist for the non-VM network
    Verify bridge_opts exists for VM network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM and non-VM networks on DC/Cluster/Host
        """
        local_dict = {config.NETWORKS[0]: {"nic": 1,
                                           "required": "false"},
                      config.NETWORKS[1]: {'nic': 2,
                                           'usages': "",
                                           'required': "false"}}
        logger.info(
            "Create networks %s and %s on DC, Cluster, Host",
            config.NETWORKS[0], config.NETWORKS[1]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach networks %s and %s" %
                (config.NETWORKS[0], config.NETWORKS[1])
            )

    @polarion("RHEVM3-4178")
    def test_check_bridge_opts_exist(self):
        """
        Check bridge_opts exists for VM network only
        """
        logger.info(
            "Check that bridge_opts exists for VM network %s and doesn't "
            "exist for non-VM network %s", config.NETWORKS[0],
            config.NETWORKS[1]
        )
        if not check_bridge_file_exist(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.NETWORKS[0]
        ):
            raise NetworkException(
                "Bridge_opts doesn't exists for VM network %s " %
                config.NETWORKS[0]
            )

        if check_bridge_file_exist(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.NETWORKS[1]
        ):
            raise NetworkException(
                "Bridge_opts does exist for VM network %s but shouldn't" %
                config.NETWORKS[1]
            )


@attr(tier=1)
class TestNetCustPrCase02(TestNCPCaseBase):
    """
    Verify bridge_opts doesn't exist for the VLAN non-VM network over bond
    Verify bridge_opts exists for VLAN VM network over bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM and non-VM networks on DC/Cluster and Host Bond
        """
        local_dict = {None: {'nic': config.BOND[0], 'mode': 1,
                             'slaves': [2, 3]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "required": "false",
                                                "vlan_id": config.VLAN_ID[0]},
                      config.VLAN_NETWORKS[1]: {'nic': config.BOND[0],
                                                "usages": "",
                                                "required": "false",
                                                "vlan_id": config.VLAN_ID[1]}}
        logger.info("Create networks %s and %s on DC, Cluster and Host Bond",
                    config.NETWORKS[0], config.NETWORKS[1])
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach networks %s and %s" %
                (config.NETWORKS[0], config.NETWORKS[1])
            )

    @polarion("RHEVM3-4179")
    def test_check_bridge_opts_exist_bond(self):
        """
        Check bridge_opts exists for VLAN VM network only over Bond
        """
        logger.info(
            "Check that bridge_opts exists for VLAN VM network %s and doesn't "
            "exist for VLAN non-VM network %s over bond",
            config.NETWORKS[0], config.NETWORKS[1]
        )
        if not check_bridge_file_exist(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Bridge_opts doesn't exists for VM network %s " %
                config.NETWORKS[0]
            )

        if check_bridge_file_exist(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.VLAN_NETWORKS[1]
        ):
            raise NetworkException(
                "Bridge_opts does exist for VM network %s but shouldn't" %
                config.NETWORKS[1]
            )


@attr(tier=1)
class TestNetCustPrCase03(TestNCPCaseBase):
    """
    Configure bridge_opts with non-default value
    Verify bridge_opts were updated
    Update bridge_opts with default value
    Verify bridge_opts were updated with the default value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host with bridge_opts having
        non-default value for priority field
        """
        network_param_dict = {"nic": 1,
                              "required": "false",
                              "properties": {"bridge_opts": config.PRIORITY}}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host with bridge_opts"
            " having non-default value for priority field", config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-4180")
    def test_update_bridge_opts(self):
        """
        1) Verify bridge_opts have updated value for priority opts
        2) Update bridge_opts with the default value
        3) Verify bridge_opts have updated default value for priority opts
        """
        kwargs = {"properties": {"bridge_opts": config.DEFAULT_PRIORITY}}
        logger.info(
            "Check that bridge_opts parameter for priority  have an updated "
            "non-default value "
        )
        if not check_bridge_opts(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.NETWORKS[0], config.KEY1,
            config.BRIDGE_OPTS.get(config.KEY1)[1]
        ):
            raise NetworkException(
                "Priority value of bridge_opts was not updated correctly"
            )

        logger.info(
            "Update bridge_opts for priority with the default parameter "
        )
        if not update_network_host(
            config.HOSTS[0], HOST_NICS[1], auto_nics=[HOST_NICS[0]],
            **kwargs
        ):
            raise NetworkException(
                "Couldn't update bridge_opts with default parameters for "
                "priority bridge_opts"
            )

        logger.info(
            "Check that bridge_opts parameter has an updated default value "
        )
        if not check_bridge_opts(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.NETWORKS[0], config.KEY1,
            config.BRIDGE_OPTS.get(config.KEY1)[0]
        ):
            raise NetworkException(
                "Priority value of bridge opts was not updated correctly"
            )


@attr(tier=1)
class TestNetCustPrCase04(TestNCPCaseBase):
    """
    Configure bridge_opts with non-default value
    Verify bridge_opts was updated
    Update the network with additional bridge_opts key: value pair
    Verify bridge_opts were updated with both values
    Update both values of bridge_opts with the default values
    Verify bridge_opts were updated accordingly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM and network on DC/Cluster/Host with bridge_opts
        having non-default value for priority field
        """
        network_param_dict = {"nic": 1,
                              "required": "false",
                              "properties": {"bridge_opts": config.PRIORITY}}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host with bridge_opts"
            " having non-default value for priority field", config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-4181")
    def test_check_several_bridge_opts_exist_nic(self):
        """
        1) Update bridge_opts with additional parameter (multicast_querier)
        2) Verify bridge_opts have updated value for Priority and
        multicast_querier
        3) Update bridge_opts with the default value for both keys
        4) Verify bridge_opts have updated default value
        """
        default_bridge_opts = " ".join(
            [config.DEFAULT_PRIORITY, config.DEFAULT_MULT_QUERIER]
        )
        non_default_bridge_opts = " ".join(
            [config.PRIORITY, config.MULT_QUERIER]
        )
        kwargs1 = {"properties": {"bridge_opts": non_default_bridge_opts}}
        kwargs2 = {"properties": {"bridge_opts": default_bridge_opts}}
        logger.info(
            "Update bridge_opts with additional parameter for multicast_"
            "querier"
        )
        if not update_network_host(
            config.HOSTS[0], HOST_NICS[1], auto_nics=[HOST_NICS[0]],
            **kwargs1
        ):
            raise NetworkException(
                "Couldn't update bridge_opts with additional key:value "
                "parameters"
            )

        logger.info("Check that bridge_opts parameter has an updated value ")
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[1]
            ):
                raise NetworkException(
                    "Value of bridge opts key %s was not updated correctly "
                    "with value %s" % (key, value[1])
                )

        logger.info("Update bridge_opts with the default parameter ")
        if not update_network_host(
            config.HOSTS[0], HOST_NICS[1], auto_nics=[HOST_NICS[0]],
            **kwargs2
        ):
            raise NetworkException(
                "Couldn't update bridge_opts with default parameters for "
                "both values"
            )

        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        for key, value in config.BRIDGE_OPTS.items():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[0]
            ):
                raise NetworkException(
                    "Priority value of bridge opts key %s was not updated "
                    "correctly with value %s" % (key, value[0])
                )


@attr(tier=1)
class TestNetCustPrCase05(TestNCPCaseBase):
    """
    Configure bridge_opts with non-default value over bond
    Verify bridge_opts were updated
    Update the network with additional bridge_opts key: value pair
    Verify bridge_opts were updated with both values
    Update both values of bridge_opts with the default values
    Verify bridge_opts were updated accordingly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC, Cluster and Host bond with bridge_opts
         having non-default value for priority field
        """
        network_param_dict = {"nic": config.BOND[0],
                              "slaves": [2, 3],
                              "required": "false",
                              "properties": {"bridge_opts": config.PRIORITY}}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host bond with "
            "bridge_opts having non-default value for priority field",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4182")
    def test_check_several_bridge_opts_exist_bond(self):
        """
        1) Update bridge_opts with additional parameter (multicast_querier)
        2) Veify bridge_opts have updated value for Priority and
        multicast_querier
        3) Update bridge_opts with the default value for both keys
        4) Verify bridge_opts have updated default value
        """
        default_bridge_opts = " ".join(
            [config.DEFAULT_PRIORITY, config.DEFAULT_MULT_QUERIER]
        )
        non_default_bridge_opts = " ".join(
            [config.PRIORITY, config.MULT_QUERIER]
        )
        kwargs1 = {"properties": {"bridge_opts": non_default_bridge_opts}}
        kwargs2 = {"properties": {"bridge_opts": default_bridge_opts}}

        logger.info(
            "Update bridge_opts with additional parameter for multicast_"
            "querier"
        )
        if not update_network_host(
            config.HOSTS[0], config.BOND[0], auto_nics=[HOST_NICS[0]],
            **kwargs1
        ):
            raise NetworkException(
                "Couldn't update bridge_opts with additional key:value "
                "parameters"
            )

        logger.info("Check that bridge_opts parameter has an updated value ")
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[1]
            ):
                raise NetworkException(
                    "Value of bridge opts key %s was not updated correctly "
                    "with value %s" % (key, value[1])
                )

        logger.info("Update bridge_opts with the default parameters for keys ")
        if not update_network_host(
            config.HOSTS[0], config.BOND[0], auto_nics=[HOST_NICS[0]],
            **kwargs2
        ):
            raise NetworkException(
                "Couldn't update bridge_opts with default parameters for "
                "both keys"
            )

        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[0]
            ):
                raise NetworkException(
                    "Value of bridge opts key %s was not updated correctly "
                    "with value %s" % (key, value[0])
                )


@attr(tier=1)
class TestNetCustPrCase06(TestNCPCaseBase):
    """
    Configure bridge_opts with non-default value for VLAN network over NIC
    Configure bridge_opts with non-default value for network over bond
    Verify bridge_opts were updated for both networks
    Detach both networks from Host
    Reattach both networks to the appropriate NIC and bond interfaces
    Verify bridge_opts have the default values when reattached (not updated
    values)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 logical VM networks on DC, Cluster and Host when the
        untagged one is attached to the bond and tagged one is attached to
        the host interface (bridge_opts is configured for both)
        """
        local_dict = {config.NETWORKS[0]: {
            "nic": config.BOND[0], "slaves": [2, 3], "required": "false",
            "properties": {"bridge_opts": config.PRIORITY}
        }, config.VLAN_NETWORKS[0]: {
            "nic": 1, 'vlan_id': config.VLAN_ID[0], "required": "false",
            "properties": {"bridge_opts": config.PRIORITY}}
        }
        logger.info("Create 2 logical VM networks on DC, Cluster and Host when"
                    " the untagged %s is attached to the bond %s and tagged "
                    "%s is attached to the host interface %s"
                    "(bridge_opts is configured for both)",
                    config.NETWORKS[0], config.BOND[0],
                    config.VLAN_NETWORKS[0], HOST_NICS[1])
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach networks %s and %s" %
                (config.NETWORKS[0], config.VLAN_NETWORKS[0])
            )

    @polarion("RHEVM3-4183")
    def test_check_reattach_network(self):
        """
        1) Verify bridge_opts have updated values for both networks
        2) Detach networks from the Host
        3) Reattach networks to the Host again
        4) Verify bridge_opts have updated default value
        """
        logger.info("Check that bridge_opts parameter has an updated value ")
        for network in (config.NETWORKS[0], config.VLAN_NETWORKS[0]):
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                network, config.KEY1,
                config.BRIDGE_OPTS.get(config.KEY1)[1]
            ):
                raise NetworkException(
                    "Priority value of bridge opts key was not updated "
                    "correctly with value %s" %
                    config.BRIDGE_OPTS.get(config.KEY1)[1]
                )
        logger.info(
            "Detach networks %s and %s from Host", config.NETWORKS[0],
            config.VLAN_NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict={}, auto_nics=[0]
        ):
            raise NetworkException("Cannot detach networks from setup")

        logger.info(
            "Reattach networks %s and %s to Host", config.NETWORKS[0],
            config.VLAN_NETWORKS[0]
        )
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                           "slaves": [2, 3],
                                           "required": "false"},
                      config.VLAN_NETWORKS[0]: {"nic": 1,
                                                "vlan_id": config.VLAN_ID[0],
                                                "required": "false"}}

        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        for network in (config.NETWORKS[0], config.VLAN_NETWORKS[0]):
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                network, config.KEY1,
                config.BRIDGE_OPTS.get(config.KEY1)[0]
            ):
                raise NetworkException(
                    "Value of bridge opts key was not updated correctly "
                    "with value %s" % config.BRIDGE_OPTS.get(config.KEY1)[0]
                )


@attr(tier=1)
class NetCustPrCase07(TestNCPCaseBase):
    """
    Configure ethtool with non-default value
    Verify ethtool_opts were updated
    Update ethtool_opts with default value
    Verify ethtool_opts were updated with the default value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VLAN VM network on DC/Cluster/Host with ethtool_opts
        having non-default value for tx_checksum field
        """
        prop_dict = {"ethtool_opts": config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="off")}
        network_param_dict = {"nic": 1, "required": "false",
                              "vlan_id": config.VLAN_ID[0],
                              "properties": prop_dict}

        local_dict = {config.VLAN_NETWORKS[0]: network_param_dict}
        logger.info("Create logical VLAN VM network %s on DC/Cluster/Host "
                    "with ethtool_opts having non-default value for "
                    "tx_checksum field", config.VLAN_NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0, 1]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @polarion("RHEVM3-4187")
    def test_update_ethtool_opts(self):
        """
        1) Verify ethtool_opts have updated value for tx_checksum opts
        2) Update ethtool_opts with the default value
        3) Verify ethtool_opts have updated default value for tx_checksum opts
        """
        kwargs = {"properties": {"ethtool_opts": config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="on")}}

        logger.info("Check that ethtool_opts parameter for tx_checksum have "
                    "an updated non-default value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "off"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly with non-default value")

        logger.info("Update ethtool_opts for tx_checksum with the default "
                    "parameter ")
        if not update_network_host(config.HOSTS[0],
                                   ".".join([HOST_NICS[1],
                                             config.VLAN_ID[0]]),
                                   auto_nics=HOST_NICS[:2], **kwargs):
            raise NetworkException("Couldn't update ethtool_opts with default "
                                   "parameters for tx_checksum_opts")

        logger.info("Check that ethtool_opts parameter has an updated default "
                    "value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "on"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly with default value")


@attr(tier=1)
class TestNetCustPrCase08(TestNCPCaseBase):
    """
    Configure ethtool_opts with non-default value
    Verify ethtool_opts was updated
    Update the NIC with additional ethtool_opts value
    Verify ethtool_opts were updated with both values
    Update both values of ethtool_opts with the default values
    Verify ethtool_opts were updated accordingly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-VM and network on DC/Cluster/Host with
        ethtool_opts having non-default value for tx_checksum field
        """
        prop_dict = {"ethtool_opts": config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="off")}
        network_param_dict = {"nic": 1, "required": "false",
                              "usages": "",
                              "properties": prop_dict}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info("Create logical non-VM and network %s on DC/Cluster/Host "
                    "with ethtool_opts having non - default value for "
                    "tx_checksum field", config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @polarion("RHEVM3-4188")
    def test_check_several_ethtool_opts_exist_nic(self):
        """
        1) Update ethtool_opts with additional parameter (autoneg)
        2) Verify ethtool_opts have updated value for tx_checksum and autoneg
        3) Update ethtool_opts with the default value for both keys
        4) Verify ethtool_opts have updated default value
        """
        default_ethtool_opts = " ".join([config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="on"), config.AUTONEG.format(
                nic=HOST_NICS[1], state="on")])
        non_default_ethtool_opts = " ".join([config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="off"), config.AUTONEG.format(
                nic=HOST_NICS[1], state="off")]
        )
        kwargs1 = {"properties": {"ethtool_opts": non_default_ethtool_opts}}
        kwargs2 = {"properties": {"ethtool_opts": default_ethtool_opts}}
        logger.info("Update ethtool_opts with additional parameter for "
                    "auto negotiation")
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs1):
            raise NetworkException("Couldn't update bridge_opts with "
                                   "additional autoneg parameter")

        logger.info("Check that ethtool_opts parameter has an updated value ")
        for prop in ("Autonegotiate", "tx-checksumming"):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, HOST_NICS[1],
                                      prop, "off"):
                raise NetworkException("tx-checksum value of ethtool_opts was "
                                       "not updated correctly with non-default"
                                       " value")

        logger.info("Update ethtool_opts with the default parameters for "
                    "both checksum and autoneg values ")
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs2):
            raise NetworkException("Couldn't update ethtool_opts with default "
                                   "parameters for both values")

        logger.info("Check that ethtool_opts parameters have an updated "
                    "default value for checksum and autoneg")
        for prop in ("Autonegotiate", "tx-checksumming"):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, HOST_NICS[1],
                                      prop, "on"):
                raise NetworkException("tx-checksum and autoneg values of "
                                       "ethtool_opts were not updated "
                                       "correctly with default value")


@attr(tier=1)
class TestNetCustPrCase09(TestNCPCaseBase):
    """
    Configure ethtool with non-default value for the NIC with network
    Verify ethtool_opts were updated
    Remove network from Host NIC
    Reattach network to the Host NIC
    Verify ethtool_opts has the non-default value for the NIC with network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host with ethtool_opts
        having non-default value for tx_checksum field
        """
        prop_dict = {"ethtool_opts": config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="off")}
        network_param_dict = {"nic": 1, "required": "false",
                              "properties": prop_dict}

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info("Create logical VM network %s on DC/Cluster/Host with "
                    "ethtool_opts having non-default value for tx_checksum "
                    "field", config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

        logger.info("Check that ethtool_opts parameter for tx_checksum have "
                    "an updated non-default value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "off"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly")

    @polarion("RHEVM3-4191")
    def test_reattach_network(self):
        """
        1) Detach the network from the Host NIC
        2) Verify ethtool_opts has non default value on the NIC
        3) Reattach network to the same NIC
        3) Verify ethtool_opts has non default value on the NIC
        """
        logger.info("Remove network %s from the Host NIC", config.NETWORKS[0])
        if not createAndAttachNetworkSN(host=config.VDS_HOSTS[0],
                                        network_dict={},
                                        auto_nics=[0]):
            raise NetworkException("Couldn't remove network %s from the Host "
                                   "NIC" % config.NETWORKS[0])

        logger.info("Check that ethtool_opts parameter has an updated "
                    "non-default value after removing network")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "off"):
            raise NetworkException("tx-checksum value of ethtool_has default "
                                   "value, but shouldn't")

        logger.info("Reattach the network %s to the same Host NIC",
                    config.NETWORKS[0])
        network_param_dict = {"nic": 1, "required": "false"}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        if not createAndAttachNetworkSN(host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

        logger.info("Check that ethtool_opts parameter has non-default value "
                    "after reattaching new network")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "off"):
            raise NetworkException("tx-checksum value of ethtool_has default "
                                   "value, but shouldn't")

    @classmethod
    def teardown_class(cls):
        """
        Update ethtool with the default values and remove networks from the
        setup.
        """
        def_ethtool_opts = config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="on")
        kwargs2 = {"properties": {"ethtool_opts": def_ethtool_opts}}

        logger.info("Update ethtool_opts with the default parameters for "
                    "checksum value ")
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs2):
            logger.error(
                "Couldn't update ethtool_opts with default parameter"
            )

        logger.info("Check that ethtool_opts parameters have an updated "
                    "default value for checksum")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "on"):
            logger.error(
                "tx-checksum value of ethtool_opts was not updated correctly"
                " with default value"
            )
        super(TestNetCustPrCase09, cls).teardown_class()


@attr(tier=1)
class TestNetCustPrCase10(TestNCPCaseBase):
    """
    Configure ethtool and bridge opts with non-default value
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host with ethtool_opts
        and bridge_opts having non-default values
        """

        prop_dict = {
            "ethtool_opts": config.TX_CHECKSUM.format(
                nic=HOST_NICS[1], state="off"
            ), "bridge_opts": config.PRIORITY
        }
        network_param_dict = {"nic": 1,
                              "required": "false",
                              "properties": prop_dict}

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info("Create logical VM network %s on DC/Cluster/Host with "
                    "ethtool_opts and bridge_opts having non-default "
                    "values", config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @polarion("RHEVM3-4192")
    def test_update_ethtool_bridge_opts(self):
        """
        1) Verify ethtool_and bridge opts have updated values
        2) Update ethtool and bridge_opts with the default value
        3) Verify ethtool_and bridge opts have been updated with default values
        """
        logger.info("Check that ethtool_opts parameter for tx_checksum "
                    "have an updated non-default value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "off"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly with non-default value")

        logger.info("Check that bridge_opts parameter for priority  have an "
                    "updated non-default value ")
        if not check_bridge_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[1]):
            raise NetworkException("Priority value of bridge_opts was not "
                                   "updated correctly with non-default value")

        logger.info("Update ethtool_opts for tx_checksum and bridge_opts "
                    "for priority with the default parameters ")
        kwargs = {"properties": {
            "ethtool_opts": config.TX_CHECKSUM.format(
                nic=HOST_NICS[1], state="on"
            ), "bridge_opts": config.DEFAULT_PRIORITY}
        }
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs):
            raise NetworkException("Couldn't update ethtool and bridge_opts "
                                   "with default parameters for tx_checksum "
                                   "and priority opts")

        logger.info("Check that ethtool_opts parameter has an updated default "
                    "value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "on"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly with default value")

        logger.info("Check that bridge_opts parameter has an updated default "
                    "value ")
        if not check_bridge_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[0]):
            raise NetworkException("Priority value of bridge opts was not "
                                   "updated correctly with default value")


@attr(tier=1)
class TestNetCustPrCase11(TestNCPCaseBase):
    """
    Create a network without ethtool or bridge opts configured
    Configure ethtool and bridge opts with non-default value
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host
        """
        network_param_dict = {"nic": 1,
                              "required": "false"}

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info("Create logical VM network %s on DC/Cluster/Host",
                    config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @polarion("RHEVM3-4193")
    def test_update_bridge_ethtool_opts(self):
        """
        1) Update existing network with non-default values for bridge and
        ethtool opts
        2) Verify ethtool_and bridge opts have updated non-default values
        3) Update ethtool and bridge_opts with the default value
        4) Verify ethtool_and bridge opts have been updated with default values
        """
        logger.info("Update ethtool and bridge opts for tx_checksum and "
                    "priority appropriately with the default parameters ")
        kwargs = {"properties": {
            "ethtool_opts": config.TX_CHECKSUM.format(
                nic=HOST_NICS[1], state="off"
            ), "bridge_opts": config.PRIORITY}
        }
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs):
            raise NetworkException("Couldn't update ethtool and bridge opts "
                                   "with non default parameters for "
                                   "tx_checksum and priority opts")
        logger.info("Check that ethtool_opts parameter for tx_checksum "
                    "have an updated non-default value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "off"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly with non-default value")

        logger.info("Check that bridge_opts parameter for priority  have an "
                    "updated non-default value ")
        if not check_bridge_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[1]):
            raise NetworkException("Priority value of bridge_opts was not "
                                   "updated correctly with non-default value")

        logger.info("Update ethtool and bridge opts for tx_checksum and "
                    "priority appropriately with the default parameters ")
        kwargs = {"properties": {
            "ethtool_opts": config.TX_CHECKSUM.format(
                nic=HOST_NICS[1], state="on"
            ), "bridge_opts": config.DEFAULT_PRIORITY}
        }
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs):
            raise NetworkException("Couldn't update ethtool and bridge_opts "
                                   "with default parameters for tx_checksum "
                                   "and priority opts accordingly")

        logger.info("Check that ethtool_opts parameter has an updated default "
                    "value ")
        if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                  config.HOSTS_PW, HOST_NICS[1],
                                  "tx-checksumming", "on"):
            raise NetworkException("tx-checksum value of ethtool_opts was not "
                                   "updated correctly with default value")

        logger.info("Check that bridge_opts parameter has an updated default "
                    "value ")
        if not check_bridge_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[0]):
            raise NetworkException("Priority value of bridge opts was not "
                                   "updated correctly with default value")


@attr(tier=1)
class TestNetCustPrCase12(TestNCPCaseBase):
    """
    Configure several ethtool_opts  with non-default value for the NIC with
     attached Network (different key:value)
    Configure several bridge_opts with non-default value for the same network
     attached to the NIC (different key:value)
    Test on the Host that the ethtool values were updated correctly
    Test on the Host that bridge_opts values were updated correctly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host
        """
        network_param_dict = {"nic": 1, "required": "false"}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info("Attach network %s to DC/Cluste/Host", config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @polarion("RHEVM3-4194")
    def test_check_several_bridge_ethtool_opts_exist(self):
        """
        1) Configure several ethtool_opts  with non-default value for the
        NIC with attached Network (different key:value)
        2) Configure several bridge_opts with non-default value for the same
        network attached to the NIC (different key:value)
        3) Test on the Host that the ethtool values were updated correctly
        4) Test on the Host that bridge_opts values were updated correctly
        """
        default_ethtool_opts = " ".join([config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="on"), config.AUTONEG.format(
                nic=HOST_NICS[1], state="on")])
        non_default_ethtool_opts = " ".join([config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="off"), config.AUTONEG.format(
                nic=HOST_NICS[1], state="off")]
        )
        default_bridge_opts = " ".join(
            [config.DEFAULT_PRIORITY, config.DEFAULT_MULT_QUERIER]
        )
        non_default_bridge_opts = " ".join(
            [config.PRIORITY, config.MULT_QUERIER]
        )
        kwargs1 = {"properties": {"ethtool_opts": non_default_ethtool_opts,
                                  "bridge_opts": non_default_bridge_opts}}
        kwargs2 = {"properties": {"ethtool_opts": default_ethtool_opts,
                                  "bridge_opts": default_bridge_opts}}
        logger.info("Update ethtool_opts with non-default parameters for "
                    "tx_checksup and autoneg and priority and "
                    "querier of bridge opts")
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs1):
            raise NetworkException("Couldn't update bridge_opts with "
                                   "additional autoneg parameter")

        logger.info("Check that ethtool_opts parameter has an updated value ")
        for prop in ("Autonegotiate", "tx-checksumming"):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, HOST_NICS[1],
                                      prop, "off"):
                raise NetworkException("tx-checksum value of ethtool_opts was "
                                       "not updated correctly with non-default"
                                       " value")
        logger.info("Check that bridge_opts parameter has an updated value ")
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[1]
            ):
                raise NetworkException(
                    "Value of bridge opts key %s was not updated correctly "
                    "with value %s" % (key, value[1])
                )

        logger.info("Update ethtool_opts with default parameters for "
                    "tx_checksup and autoneg and priority and "
                    "querier of bridge opts")
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs2):
            raise NetworkException("Couldn't update ethtool_opts with default "
                                   "parameters for both values")

        logger.info("Check that ethtool_opts parameters have an updated "
                    "default value for checksum and autoneg")
        for prop in ("Autonegotiate", "tx-checksumming"):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, HOST_NICS[1],
                                      prop, "on"):
                raise NetworkException("tx-checksum and autoneg values of "
                                       "ethtool_opts were not updated "
                                       "correctly with default value")
        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        for key, value in config.BRIDGE_OPTS.items():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[0]
            ):
                raise NetworkException(
                    "Priority value of bridge opts key %s was not updated "
                    "correctly with value %s" % (key, value[0])
                )


@attr(tier=1)
class TestNetCustPrCase13(TestNCPCaseBase):
    """
    Create several ethtool and bridge opts while adding network to the Host
    Configure several ethtool_opts  with non-default value for the NIC with
     attached Network (different key:value)
    Configure several bridge_opts with non-default value for the same network
     attached to the NIC (different key:value)
    Test on the Host that the ethtool values were updated correctly
    Test on the Host that bridge_opts values were updated correctly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host with several ethtool
        and bridge opts configured
        """
        default_ethtool_opts = " ".join(
            [config.TX_CHECKSUM.format(nic=HOST_NICS[1], state="on"),
             config.AUTONEG.format(nic=HOST_NICS[1], state="on")])
        default_bridge_opts = " ".join(
            [config.DEFAULT_PRIORITY, config.DEFAULT_MULT_QUERIER]
        )
        prop_dict = {"ethtool_opts": default_ethtool_opts,
                     "bridge_opts": default_bridge_opts}
        network_param_dict = {"nic": 1,
                              "required": "false",
                              "properties": prop_dict}
        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create network %s with ethtool and bridge opts",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-4195")
    def test_check_several_bridge_ethtool_opts_exist(self):
        """
        1) Update several ethtool_opts for the NIC with attached Network
        with additional parameter and non-default value (different key:value)
        2) Update several bridge_opts for Network, attached to the NIC with
        additional parameter and non-default value (different key:value)
        3) Test on the Host that the ethtool values were updated correctly
        for the ethtool_opts
        4) Test for the network on the the Host that the bridge values were
        updated correctlydefault_bridge_opts = " ".join(
            [config.DEFAULT_PRIORITY, config.DEFAULT_MULT_QUERIER]
        )
        5) Update  ethtool_opts with the default values for configured values.
        6) Update  bridge_opts with the default values for configured values.
        7) Test on the Host that the ethtool values were updated correctly
        8) Test for the network on the the Host that the bridge values were
        updated correctly

        """
        default_ethtool_opts = " ".join([config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="on"), config.AUTONEG.format(
            nic=HOST_NICS[1], state="on")])
        non_default_ethtool_opts = " ".join([config.TX_CHECKSUM.format(
            nic=HOST_NICS[1], state="off"), config.AUTONEG.format(
            nic=HOST_NICS[1], state="off")])
        default_bridge_opts = " ".join(
            [config.DEFAULT_PRIORITY, config.DEFAULT_MULT_QUERIER]
        )
        non_default_bridge_opts = " ".join(
            [config.PRIORITY, config.MULT_QUERIER]
        )
        kwargs1 = {"properties": {"ethtool_opts": non_default_ethtool_opts,
                                  "bridge_opts": non_default_bridge_opts}}
        kwargs2 = {"properties": {"ethtool_opts": default_ethtool_opts,
                                  "bridge_opts": default_bridge_opts}}
        logger.info("Update ethtool_opts with non-default parameters for "
                    "tx_checksup and autoneg and priority and "
                    "querier of bridge opts")
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs1):
            raise NetworkException(
                "Couldn't update bridge_opts with additional autoneg parameter"
            )

        logger.info(
            "Check that ethtool_opts parameter has an updated value "
        )
        for prop in ("Autonegotiate", "tx-checksumming"):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, HOST_NICS[1],
                                      prop, "off"):
                raise NetworkException(
                    "tx-checksum value of ethtool_opts was not updated "
                    "correctly with non-default value"
                )
        logger.info(
            "Check that bridge_opts parameter has an updated value "
        )
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[1]
            ):
                raise NetworkException(
                    "Value of bridge opts key %s was not updated correctly "
                    "with value %s" % (key, value[1])
                )

        logger.info(
            "Update ethtool_opts with default parameters for tx_checksum and "
            "autoneg and priority and querier of bridge opts"
        )
        if not update_network_host(config.HOSTS[0], HOST_NICS[1],
                                   auto_nics=[HOST_NICS[0]], **kwargs2):
            raise NetworkException(
                "Couldn't update ethtool_opts with default parameters for "
                "both values"
            )

        logger.info("Check that ethtool_opts parameters have an updated "
                    "default value for checksum and autoneg")
        for prop in ("Autonegotiate", "tx-checksumming"):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, HOST_NICS[1],
                                      prop, "on"):
                raise NetworkException("tx-checksum and autoneg values of "
                                       "ethtool_opts were not updated "
                                       "correctly with default value")
        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        for key, value in config.BRIDGE_OPTS.items():
            if not check_bridge_opts(
                config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
                config.NETWORKS[0], key, value[0]
            ):
                raise NetworkException(
                    "Priority value of bridge opts key %s was not updated "
                    "correctly with value %s" % (key, value[0])
                )

    def tearDown(self):
        """
        Removing custom properties from host NIC
        """
        kwargs = {"properties": {
            "ethtool_opts": None, "bridge_opts": None}
        }
        logger.info("Update ethtool_opts and bridge_opts to None (clear)")
        if not update_network_host(
            config.HOSTS[0], HOST_NICS[1], auto_nics=[HOST_NICS[0]], **kwargs
        ):
            logger.error("Couldn't clear ethtool_optsbridge_opts")
        super(TestNetCustPrCase13, self).tearDown()


@attr(tier=1)
class TestNetCustPrCase14(TestNCPCaseBase):
    """
    Configure ethtool with non-default value over bond
    Verify ethtool_opts were updated for each slave of the bond
    Update ethtool_opts with default value over bond
    Verify ethtool_opts were updated with the default value for each slave
    of the bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host
        """
        network_param_dict = {"nic": config.BOND[0],
                              "slaves": [2, 3],
                              "required": "false"}

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host bond",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s to bond %s" %
                (config.NETWORKS[0], config.BOND[0])
            )

    @polarion("RHEVM3-4190")
    def test_update_ethtool_opts_bond(self):
        """
        1) Configure ethtool_opts tx_checksum value to be non-default on Bond
        1) Verify ethtool_opts have updated value for tx_checksum opts for
        each slave of the bond
        2) Update ethtool_opts with the default value for the bond
        3) Verify ethtool_opts have updated default value for tx_checksum
        opts for each slave of the bond
        """
        kwargs1 = {"properties": {"ethtool_opts": config.TX_CHECKSUM.format(
            nic="*", state="off")}}
        kwargs2 = {"properties": {"ethtool_opts": config.TX_CHECKSUM.format(
            nic="*", state="on")}}

        logger.info(
            "Update ethtool_opts for tx_checksum with the non-default "
            "parameter "
        )
        if not update_network_host(config.HOSTS[0],
                                   config.BOND[0],
                                   auto_nics=[HOST_NICS[0]], **kwargs1):
            raise NetworkException(
                "Couldn't update ethtool_opts with default parameters for "
                "tx_checksum_opts"
            )

        logger.info(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value for both slaves"
        )
        for interface in (HOST_NICS[2], HOST_NICS[3]):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, interface,
                                      "tx-checksumming", "off"):
                raise NetworkException(
                    "tx-checksum value of ethtool_opts was not updated "
                    "correctly with non-default value"
                )

        logger.info(
            "Update ethtool_opts for tx_checksum with the default parameter"
        )
        if not update_network_host(config.HOSTS[0],
                                   config.BOND[0],
                                   auto_nics=[HOST_NICS[0]], **kwargs2):
            raise NetworkException(
                "Couldn't update ethtool_opts with default parameters for "
                "tx_checksum_opts"
            )

        logger.info(
            "Check that ethtool_opts parameter has an updated default "
            "value for both slaves of the bond "
        )
        for interface in (HOST_NICS[2], HOST_NICS[3]):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, interface,
                                      "tx-checksumming", "on"):
                raise NetworkException(
                    "tx-checksum value of ethtool_opts was not updated "
                    "correctly with default value"
                )


@attr(tier=1)
class TestNetCustPrCase15(TestNCPCaseBase):
    """
    Configure ethtool_opts with non-default value
    Verify ethtool_opts was updated
    Update the NIC with additional ethtool_opts value
    Verify ethtool_opts were updated with both values
    Update both values of ethtool_opts with the default values
    Verify ethtool_opts were updated accordingly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster and Host Bond
        """
        network_param_dict = {"nic": config.BOND[0],
                              "slaves": [2, 3],
                              "required": "false"}

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host bond",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s to bond %s" %
                (config.NETWORKS[0], config.BOND[0])
            )

    @polarion("RHEVM3-4189")
    def test_check_several_ethtool_opts_exist_bond(self):
        """
        1) Update ethtool_opts with non-default parameter (tx_checksum)
        2) Verify ethtool_opts have updated value for tx_checksum
        1) Update ethtool_opts with additional parameter (autoneg)
        2) Verify ethtool_opts have updated value for tx_checksum and autoneg
        3) Update ethtool_opts with the default value for both keys
        4) Verify ethtool_opts have updated default value
        """
        kwargs = {"properties": {"ethtool_opts": config.TX_CHECKSUM.format(
            nic="*", state="off")}}

        logger.info(
            "Update ethtool_opts for tx_checksum with the non-default "
            "parameter "
        )
        if not update_network_host(config.HOSTS[0],
                                   config.BOND[0],
                                   auto_nics=[HOST_NICS[0]], **kwargs):
            raise NetworkException(
                "Couldn't update ethtool_opts with default parameters for "
                "tx_checksum_opts"
            )

        logger.info(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value for both slaves"
        )
        for interface in (HOST_NICS[2], HOST_NICS[3]):
            if not check_ethtool_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                      config.HOSTS_PW, interface,
                                      "tx-checksumming", "off"):
                raise NetworkException(
                    "tx-checksum value of ethtool_opts was not updated "
                    "correctly with non-default value"
                )

        default_ethtool_opts = " ".join(
            [config.TX_CHECKSUM.format(nic="*", state="on"),
             config.AUTONEG.format(nic="*", state="on")])
        non_default_ethtool_opts = " ".join(
            [config.TX_CHECKSUM.format(nic="*", state="off"),
             config.AUTONEG.format(nic="*", state="off")])
        kwargs1 = {"properties": {"ethtool_opts": non_default_ethtool_opts}}
        kwargs2 = {"properties": {"ethtool_opts": default_ethtool_opts}}
        logger.info("Update ethtool_opts with additional parameter for "
                    "auto negotiation")
        if not update_network_host(config.HOSTS[0], config.BOND[0],
                                   auto_nics=[HOST_NICS[0]], **kwargs1):
            raise NetworkException(
                "Couldn't update bridge_opts with additional autoneg parameter"
            )
        logger.info(
            "Check that ethtool_opts parameter has an updated value "
            "for autonet and tx_checksumming for both slaves of the bond"
        )
        for prop in ("Autonegotiate", "tx-checksumming"):
            for interface in (HOST_NICS[2], HOST_NICS[3]):
                if not check_ethtool_opts(config.HOSTS_IP[0],
                                          config.HOSTS_USER,
                                          config.HOSTS_PW, interface,
                                          prop, "off"):
                    raise NetworkException(
                        "tx-checksum value of ethtool_opts was not updated "
                        "correctly with non-default value"
                    )

        logger.info(
            "Update ethtool_opts with the default parameters for both "
            "checksum and autoneg values for Bond "
        )
        if not update_network_host(config.HOSTS[0], config.BOND[0],
                                   auto_nics=[HOST_NICS[0]], **kwargs2):
            raise NetworkException(
                "Couldn't update ethtool_opts with default parameters for "
                "both values"
            )

        logger.info(
            "Check that ethtool_opts parameters have an updated default value "
            "for checksum and autoneg"
        )
        for prop in ("Autonegotiate", "tx-checksumming"):
            for interface in (HOST_NICS[2], HOST_NICS[3]):
                if not check_ethtool_opts(config.HOSTS_IP[0],
                                          config.HOSTS_USER,
                                          config.HOSTS_PW, interface,
                                          prop, "on"):
                    raise NetworkException(
                        "tx-checksum and autoneg values of ethtool_opts were "
                        "not updated correctly with default value for "
                        "both slaves of the bond"
                    )


@attr(tier=1)
class TestNetCustPrCase16(TestNCPCaseBase):
    """
    Configure ethtool and bridge opts with non-default value over Bond
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value over Bond
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host Bond with ethtool_opts
        and bridge_opts having non-default values
        """

        prop_dict = {"ethtool_opts": config.TX_CHECKSUM.format(
            nic="*", state="off"), "bridge_opts": config.PRIORITY}
        network_param_dict = {"nic": config.BOND[0],
                              "slaves": [2, 3],
                              "required": "false",
                              "properties": prop_dict}

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host with "
            "ethtool_opts and bridge_opts having non-default "
            "values over Bond", config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s over Bond %s" %
                (config.NETWORKS[0], config.BOND[0])
            )

    @polarion("RHEVM3-4196")
    def test_update_ethtool_bridge_opts_bond(self):
        """
        1) Verify ethtool_and bridge opts have updated values over Bond
        2) Update ethtool and bridge_opts with the default value over Bond
        3) Verify ethtool_and bridge opts have been updated with default values
        """

        logger.info(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value for every slave of the Bond"
        )
        for interface in (HOST_NICS[2], HOST_NICS[3]):
            if not check_ethtool_opts(config.HOSTS_IP[0],
                                      config.HOSTS_USER,
                                      config.HOSTS_PW, interface,
                                      "tx-checksumming", "off"):
                raise NetworkException(
                    "tx-checksum value of ethtool_opts was"
                    " not updated correctly with non-default value for Bond "
                    "slaves"
                )

        logger.info(
            "Check that bridge_opts parameter for priority  have an updated "
            "non-default value "
        )
        if not check_bridge_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[1]):
            raise NetworkException(
                "Priority value of bridge_opts was not updated correctly "
                "with non-default value"
            )

        logger.info(
            "Update ethtool_opts for tx_checksum and bridge_opts for "
            "priority with the default parameters ")
        kwargs = {"properties": {
            "ethtool_opts": config.TX_CHECKSUM.format(
                nic="*", state="on"
            ), "bridge_opts": config.DEFAULT_PRIORITY}
        }
        if not update_network_host(config.HOSTS[0], config.BOND[0],
                                   auto_nics=[HOST_NICS[0]], **kwargs):
            raise NetworkException(
                "Couldn't update ethtool and bridge_opts with default "
                "parameters for tx_checksum and priority opts"
            )

        logger.info(
            "Check that ethtool_opts parameter has an updated default value "
            "for both slaves of the Bond"
        )
        for interface in (HOST_NICS[2], HOST_NICS[3]):
            if not check_ethtool_opts(config.HOSTS_IP[0],
                                      config.HOSTS_USER,
                                      config.HOSTS_PW, interface,
                                      "tx-checksumming", "on"):
                raise NetworkException(
                    "tx-checksum value of ethtool_opts was not updated "
                    "correctly with default value for Bond Slaves"
                )

        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        if not check_bridge_opts(config.HOSTS_IP[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[0]):
            raise NetworkException(
                "Priority value of bridge opts was not updated correctly "
                "with default value"
            )
