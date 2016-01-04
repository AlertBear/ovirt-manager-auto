"""
-----------------
test_network
-----------------

    @author: Nelly Credi
"""
import logging

from art.unittest_lib import attr
from art.unittest_lib import BaseTestCase as TestCase

from art.test_handler.exceptions import NetworkException

from art.rhevm_api import resources
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    host_network as hl_host_network,
)

from rhevmtests.infra.regression_infra import help_functions
from rhevmtests.infra.regression_infra import config

logger = logging.getLogger(__name__)


def setup_module():
    """
    Setup prerequisites for testing scenario:
    create data center, cluster & host
    """
    help_functions.utils.reverse_env_list = []
    help_functions.utils.add_dc()
    help_functions.utils.add_cluster()
    help_functions.utils.add_host()


def teardown_module():
    """
    Tear down prerequisites for testing host functionality:
    remove data center, cluster & host
    """
    help_functions.utils.clean_environment()


@attr(team='automationInfra')
class TestCaseNetwork(TestCase):
    """
    Network sanity test the basic operations of network
    """

    apis = TestCase.apis - set(['cli'])

    vds = None

    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.vds = resources.VDS(
            config.HOST_NAME, config.HOSTS_PW,
        )

    def test01_create_network(self):
        """
        create network on DC/CL and attach it to host
        """

        sn_dict = {
            config.NETWORK:
            {"required": "false", "nic": 1}
        }

        network_host_api_dict = {
            "add": {
                "1": {
                    "network": config.NETWORK,
                    "nic": self.vds.nics[1]
                }
            }
        }

        logger.info(
            "Create network %s on DC/Cluster", config.NETWORK
        )

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DATA_CENTER_1_NAME,
            cluster=config.CLUSTER_1_NAME, network_dict=sn_dict
        ):
            raise NetworkException(
                "Cannot create and attach %s" % config.NETWORK)

        logger.info(
            "Attaching %s to %s on %s",
            config.NETWORK, self.vds.nics[1], self.vds
        )
        if not hl_host_network.setup_networks(
            host_name=config.HOST_NAME, **network_host_api_dict
        ):
            raise NetworkException(
                "Failed to attach %s to %s on %s" %
                (config.NETWORK, self.vds.nics[1], self.vds)
            )

    def test02_remove_network(self):
        """
        remove network from DC/CL
        """
        if not hl_networks.remove_net_from_setup(
            host=config.HOST_NAME, network=[config.NETWORK],
            mgmt_network=config.MGMT_BRIDGE,
            data_center=config.DATA_CENTER_1_NAME
        ):
            raise NetworkException(
                "Cannot remove %s from setup" % config.NETWORK)
