"""
Testing Network Custom properties feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Network Custom properties will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
import logging

from art.test_handler.exceptions import NetworkException

from rhevmtests.networking import config

from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, update_network_host, remove_all_networks
from art.rhevm_api.tests_lib.low_level.networks import \
    check_bridge_file_exist, check_bridge_opts

logger = logging.getLogger(__name__)

# #######################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class NCPTestCaseBase(TestCase):
    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        if not (remove_all_networks(datacenter=config.DC_NAME[0],
                                    mgmt_network=config.MGMT_BRIDGE) and
                createAndAttachNetworkSN(host=config.HOSTS[0], network_dict={},
                                         auto_nics=[config.HOST_NICS[0]])):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class NetCustPrCase01(NCPTestCaseBase):
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
        local_dict = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                           "required": "false"},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'usages': "", '"required': "false"}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13967, 372428)
    def check_bridge_opts_exist(self):
        """
        Check bridge_opts exists for VM network only
        """
        logger.info("Check that bridge_opts exists for VM network %s and "
                    "doesn't exist for non-VM network %s", config.NETWORKS[0],
                    config.NETWORKS[1])
        if not check_bridge_file_exist(config.HOSTS[0], config.HOSTS_USER,
                                       config.HOSTS_PW, config.NETWORKS[0]):
            raise NetworkException("Bridge_opts doesn't exists for VM "
                                   "network %s " % config.NETWORKS[0])

        if check_bridge_file_exist(config.HOSTS[0], config.HOSTS_USER,
                                   config.HOSTS_PW, config.NETWORKS[1]):
            raise NetworkException("Bridge_opts does exist for VM network %s "
                                   "but shouldn't" % config.NETWORKS[1])


@attr(tier=1)
class NetCustPrCase02(NCPTestCaseBase):
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
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "required": "false",
                                                "vlan_id": config.VLAN_ID[0]},
                      config.VLAN_NETWORKS[1]: {'nic': config.BOND[0],
                                                "usages": "",
                                                "required": "false",
                                                "vlan_id": config.VLAN_ID[1]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13967, 372468)
    def check_bridge_opts_exist_bond(self):
        """
        Check bridge_opts exists for VLAN VM network only over Bond
        """
        logger.info("Check that bridge_opts exists for VLAN VM network %s and "
                    "doesn't exist for VLAN non-VM network %s over bond",
                    config.NETWORKS[0], config.NETWORKS[1])
        if not check_bridge_file_exist(config.HOSTS[0], config.HOSTS_USER,
                                       config.HOSTS_PW,
                                       config.VLAN_NETWORKS[0]):
            raise NetworkException("Bridge_opts doesn't exists for VM "
                                   "network %s " % config.NETWORKS[0])

        if check_bridge_file_exist(config.HOSTS[0], config.HOSTS_USER,
                                   config.HOSTS_PW, config.VLAN_NETWORKS[1]):
            raise NetworkException("Bridge_opts does exist for VM network %s "
                                   "but shouldn't" % config.NETWORKS[1])


@attr(tier=1)
class NetCustPrCase03(NCPTestCaseBase):
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
        network_param_dict = {"nic": config.HOST_NICS[1], "required": "false",
                              "properties": {"bridge_opts": config.PRIORITY}}
        local_dict = {config.NETWORKS[0]: network_param_dict}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13967, 372628)
    def update_bridge_opts(self):
        """
        1) Verify bridge_opts have updated value for priority opts
        2) Update bridge_opts with the default value
        3) Verify bridge_opts have updated default value for priority opts
        """
        kwargs = {"properties": {"bridge_opts": config.DEFAULT_PRIORITY}}
        logger.info("Check that bridge_opts parameter for priority  have an "
                    "updated non-default value ")
        if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[1]):
            raise NetworkException("Priority value of bridge_opts was not "
                                   "updated correctly")

        logger.info("Update bridge_opts for priority with the default "
                    "parameter ")
        if not update_network_host(config.HOSTS[0], config.HOST_NICS[1],
                                   auto_nics=[config.HOST_NICS[0]], **kwargs):
            raise NetworkException("Couldn't update bridge_opts with default "
                                   "parameters for priority bridge_opts")

        logger.info("Check that bridge_opts parameter has an updated default "
                    "value ")
        if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                 config.HOSTS_PW, config.NETWORKS[0],
                                 config.KEY1,
                                 config.BRIDGE_OPTS.get(config.KEY1)[0]):
            raise NetworkException("Priority value of bridge opts was not "
                                   "updated correctly")


@attr(tier=1)
class NetCustPrCase04(NCPTestCaseBase):
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
        network_param_dict = {"nic": config.HOST_NICS[1], "required": "false",
                              "properties": {"bridge_opts": config.PRIORITY}}
        local_dict = {config.NETWORKS[0]: network_param_dict}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13967, 372701)
    def check_several_bridge_opts_exist_nic(self):
        """
        1) Update bridge_opts with additional parameter (multicast_querier)
        2) Verify bridge_opts have updated value for Priority and
        multicast_querier
        3) Update bridge_opts with the default value for both keys
        4) Verify bridge_opts have updated default value
        """
        default_bridge_opts = " ".join([config.DEFAULT_PRIORITY,
                                        config.DEFAULT_MULT_QUERIER])
        non_default_bridge_opts = " ".join([config.PRIORITY,
                                            config.MULT_QUERIER])
        kwargs1 = {"properties": {"bridge_opts": non_default_bridge_opts}}
        kwargs2 = {"properties": {"bridge_opts": default_bridge_opts}}
        logger.info("Update bridge_opts with additional parameter for "
                    "multicast_querier")
        if not update_network_host(config.HOSTS[0], config.HOST_NICS[1],
                                   auto_nics=[config.HOST_NICS[0]], **kwargs1):
            raise NetworkException("Couldn't update bridge_opts with "
                                   "additional key:value parameters")

        logger.info("Check that bridge_opts parameter has an updated value ")
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, config.NETWORKS[0],
                                     key, value[1]):
                raise NetworkException("Value of bridge opts key %s was not "
                                       "updated correctly with value %s"
                                       % (key, value[1]))

        logger.info("Update bridge_opts with the default parameter ")
        if not update_network_host(config.HOSTS[0], config.HOST_NICS[1],
                                   auto_nics=[config.HOST_NICS[0]], **kwargs2):
            raise NetworkException("Couldn't update bridge_opts with default "
                                   "parameters for both values")

        logger.info("Check that bridge_opts parameter has an updated default "
                    "value ")
        for key, value in config.BRIDGE_OPTS.items():
            if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, config.NETWORKS[0],
                                     key, value[0]):
                raise NetworkException("Priority value of bridge opts key %s "
                                       "was not updated correctly with value"
                                       " %s" % (key, value[0]))


@attr(tier=1)
class NetCustPrCase05(NCPTestCaseBase):
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
                              "slaves": config.HOST_NICS[2:],
                              "required": "false",
                              "properties": {"bridge_opts": config.PRIORITY}}
        local_dict = {config.NETWORKS[0]: network_param_dict}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13967, 372788)
    def check_several_bridge_opts_exist_bond(self):
        """
        1) Update bridge_opts with additional parameter (multicast_querier)
        2) Veify bridge_opts have updated value for Priority and
        multicast_querier
        3) Update bridge_opts with the default value for both keys
        4) Verify bridge_opts have updated default value
        """
        default_bridge_opts = " ".join([config.DEFAULT_PRIORITY,
                                        config.DEFAULT_MULT_QUERIER])
        non_default_bridge_opts = " ".join([config.PRIORITY,
                                            config.MULT_QUERIER])
        kwargs1 = {"properties": {"bridge_opts": non_default_bridge_opts}}
        kwargs2 = {"properties": {"bridge_opts": default_bridge_opts}}

        logger.info("Update bridge_opts with additional parameter for "
                    "multicast_querier")
        if not update_network_host(config.HOSTS[0], config.BOND[0],
                                   auto_nics=[config.HOST_NICS[0]], **kwargs1):
            raise NetworkException("Couldn't update bridge_opts with "
                                   "additional key:value parameters")

        logger.info("Check that bridge_opts parameter has an updated value ")
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, config.NETWORKS[0],
                                     key, value[1]):
                raise NetworkException("Value of bridge opts key %s was not "
                                       "updated correctly with value %s" %
                                       (key, value[1]))

        logger.info("Update bridge_opts with the default parameters for keys ")
        if not update_network_host(config.HOSTS[0], config.BOND[0],
                                   auto_nics=[config.HOST_NICS[0]], **kwargs2):
            raise NetworkException("Couldn't update bridge_opts with default "
                                   "parameters for both keys")

        logger.info("Check that bridge_opts parameter has an updated default "
                    "value ")
        for key, value in config.BRIDGE_OPTS.iteritems():
            if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, config.NETWORKS[0],
                                     key, value[0]):
                raise NetworkException("Value of bridge opts key %s was not "
                                       "updated correctly with value %s" %
                                       (key, value[0]))


@attr(tier=1)
class NetCustPrCase06(NCPTestCaseBase):
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
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           "required": "false",
                                           "properties": {"bridge_opts":
                                                          config.PRIORITY}},
                      config.VLAN_NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                                'vlan_id': config.VLAN_ID[0],
                                                "required": "false",
                                                "properties": {
                                                    "bridge_opts":
                                                    config.PRIORITY}}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13967, 372857)
    def check_reattach_network(self):
        """
        1) Verify bridge_opts have updated values for both networks
        2) Detach networks from the Host
        3) Reattach networks to the Host again
        4) Verify bridge_opts have updated default value
        """
        logger.info("Check that bridge_opts parameter has an updated value ")
        for network in (config.NETWORKS[0], config.VLAN_NETWORKS[0]):
            if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, network,
                                     config.KEY1,
                                     config.BRIDGE_OPTS.get(config.KEY1)[1]):
                raise NetworkException("Priority value of bridge opts key "
                                       "was not updated correctly with value"
                                       " %s" %
                                       config.BRIDGE_OPTS.get(config.KEY1)[1])
        logger.info("Detach networks %s and %s from Host",
                    config.NETWORKS[0], config.VLAN_NETWORKS[0])
        if not createAndAttachNetworkSN(host=config.HOSTS[0],
                                        network_dict={},
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot detach networks from setup")

        logger.info("Reattach networks %s and %s to Host",
                    config.NETWORKS[0], config.VLAN_NETWORKS[0])
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           "required": "false"},
                      config.VLAN_NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                                'vlan_id': config.VLAN_ID[0],
                                                "required": "false"}}

        if not createAndAttachNetworkSN(host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Check that bridge_opts parameter has an updated "
                    "default value ")
        for network in (config.NETWORKS[0], config.VLAN_NETWORKS[0]):
            if not check_bridge_opts(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, network, config.KEY1,
                                     config.BRIDGE_OPTS.get(config.KEY1)[0]):
                raise NetworkException("Value of bridge opts key was not "
                                       "updated correctly with value %s" %
                                       config.BRIDGE_OPTS.get(config.KEY1)[0])
