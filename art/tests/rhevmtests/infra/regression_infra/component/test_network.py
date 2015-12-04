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
from art.rhevm_api.tests_lib.high_level import networks

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
        logger.info(
            "Create network %s on DC/Cluster/Host", config.NETWORK
        )
        local_dict = {
            config.NETWORK:
            {"required": "false", "nic": 1}
        }
        if not networks.createAndAttachNetworkSN(
            data_center=config.DATA_CENTER_1_NAME, host=self.vds,
            cluster=config.CLUSTER_1_NAME, network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    def test02_remove_network(self):
        """
        remove network from DC/CL
        """
        if not networks.remove_net_from_setup(
            host=config.HOST_NAME, all_net=True,
            mgmt_network=config.MGMT_BRIDGE,
            data_center=config.DATA_CENTER_1_NAME
        ):
            logger.error("Cannot remove network from setup")
