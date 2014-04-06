'''
Testing Multiple Gateways feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Multiple Gateway will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
Only static IP configuration is tested.
'''

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from networking import config
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException, ClusterException
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from art.rhevm_api.tests_lib.low_level.datacenters import\
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.clusters import\
    addCluster, removeCluster
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, removeNetwork
from art.rhevm_api.tests_lib.low_level.networks import checkIPRule
from art.rhevm_api.tests_lib.low_level.hosts import genSNNic,\
    sendSNRequest, deactivateHost, activateHost, updateHost

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

IP = config.SOURCE_IP
NETMASK = config.NETMASK
GATEWAY = config.MG_GATEWAY
SUBNET = config.SUBNET
TIMEOUT = config.TIMEOUT

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class GatewaysCase1(TestCase):
    """
    Verify you can configure additional network beside MGMT with gateway
    Verify you can remove network configured with gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration (including gateway)
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 282894)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @istest
    @tcms(9768, 289696)
    def detach_gw_net(self):
        """
        Remove network with gw configuration from setup
        """
        self.assertTrue(sendSNRequest(True, host=config.HOSTS[0],
                                      auto_nics=[config.HOST_NICS[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from DC/CLuster")
        if not removeNetwork(True, network=config.NETWORKS[0]):
            raise NetworkException("Cannot remove network from DC/Cluster")


@attr(tier=1)
class GatewaysCase2(TestCase):
    """
    Verify you can configure additional VLAN network with static IP and gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged network on DC/Cluster/Hosts.
        Configure it with static IP configuration.
        """

        local_dict = {config.VLAN_NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false',
                                                'bootproto': 'static',
                                                'address': [IP],
                                                'netmask': [NETMASK],
                                                'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 282901)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase3(TestCase):
    """
    Verify you can configure additional bridgeless network with static IP.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-vm network on DC/Cluster/Hosts
        Configure it with static IP configuration
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'usages': '',
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 282902)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase4(TestCase):
    """
    Verify you can configure additional display network with static ip config.
    Mgmt network should be static
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical display network on DC/Cluster/Hosts
        Configure it with static IP configuration
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'cluster_usages': 'display',
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 283407)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase5(TestCase):
    """
    Try to assign to vm network incorrect static IP and gw addresses
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        local_dict1 = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                            'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create and attach first network")

    @istest
    @tcms(9768, 283968)
    def check_incorrect_config(self):
        """
        Try to create logical  network on DC/Cluster/Hosts
        Configure it with static IP configuration and incorrect gateway or IP
        """

        logger.info("Trying to attach network with incorrect IP on NIC. "
                    "The test should fail to do it")
        net_obj = []
        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.NETWORKS[0],
                           boot_protocol='static',
                           address='1.1.1.298', netmask=NETMASK,
                           gateway=GATEWAY)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(False, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force='false'):
            raise NetworkException("Can setupNetworks when shouldn't")

        logger.info("Trying to attach network with incorrect gw on NIC. "
                    "The test should fail to do it")
        net_obj = []
        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.NETWORKS[0],
                           boot_protocol='static',
                           address=IP, netmask=NETMASK,
                           gateway='1.1.1.289')
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(False, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force='false'):
            raise NetworkException("Can setupNetworks when shouldn't")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase6(TestCase):
    """
    Verify you can configure additional network with gateway 0.0.0.0
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(9768, 289770)
    def check_ip_rule(self):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration and gateway of 0.0.0.0
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': ['0.0.0.0']}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase7(TestCase):
    """
    Verify you can add additional NIC to the already created bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration on bond of 2 NICs
        """
        local_dict = {config.NETWORKS[0]: {'nic': 'bond0',
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 289694)
    def check_ip_rule(self):
        """
        Add additional NIC to the bond and check IP rule
        """
        logger.info("Checking IP rule before adding 3rd NIC")
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

        logger.info("Generating network object for 3 NIC bond ")
        net_obj = []
        rc, out = genSNNic(nic='bond0',
                           network=config.NETWORKS[0],
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3],
                                   config.HOST_NICS[1]],
                           boot_protocol='static',
                           address=IP, netmask=NETMASK,
                           gateway=GATEWAY)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force='false'):
            raise NetworkException("Cannot update bond to have 2 NICs")
        logger.info("Checking IP rule after adding 3rd NIC")
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase8(TestCase):
    """
    Verify you can remove Nic from bond having network with gw configured on it
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts and attach it to bond.
        Bond should have 3 NICs
        Configure it with static IP configuration (including gateway)
        """
        local_dict = {config.NETWORKS[0]: {'nic': 'bond0',
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3],
                                                      config.HOST_NICS[1]],
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 289695)
    def check_ip_rule(self):
        """
        Check the appearance of the subnet with ip rule command
        Remove a NIC from bond and check ip rule again
        """
        logger.info("Checking the IP rule before removing one NIC from bond")
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

        logger.info("Generating network object for 2 NIC bond ")
        net_obj = []
        rc, out = genSNNic(nic='bond0',
                           network=config.NETWORKS[0],
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]],
                           boot_protocol='static',
                           address=IP, netmask=NETMASK,
                           gateway=GATEWAY)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force='false'):
            raise NetworkException("Cannot update bond to have 2 NICs")
        logger.info("Checking the IP rule after removing one NIC from bond")
        self.assertTrue(checkIPRule(host=config.HOSTS[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class GatewaysCase9(TestCase):
    """
    Verify you can't configure gateway on the network in 3.2 Cluster
    """
    __test__ = False
    """
    There is a bug 1008999, as a result this case fails and is False till fixed
    """

    @classmethod
    def setup_class(cls):
        """
        Create 3.2 Cluster for DC 3.3
        """
        if not addCluster(positive=True, name=config.CLUSTER_NAME[1],
                          cpu=config.CPU_NAME, data_center=config.DC_NAME[0],
                          version=config.COMP_VERSION):
            raise ClusterException("Cannot create second Cluster")

    @istest
    @tcms(9768, 284029)
    def add_host_to_another_cluster(self):
        """
        Add host to the 3.2 Cluster
        Try to configure static IP with dg - should fail as in 3.2
        it is not supported
        """
        logger.info("Put the host on another Cluster")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))
        assert(waitForDataCenterState(name=config.DC_NAME[0]))
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}
        self.assertFalse(
            createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                     cluster=config.CLUSTER_NAME[1],
                                     host=config.HOSTS[0],
                                     network_dict=local_dict,
                                     auto_nics=[config.HOST_NICS[0]]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Add host to 3.3 DC")
        logger.info("Put the host on original Cluster")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))
        assert(waitForDataCenterState(name=config.DC_NAME[0]))
        logger.info("Remove Cluster 3.2 from DC")
        if not removeCluster(True, config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot remove Cluster from DC")


@attr(tier=1)
class GatewaysCase10(TestCase):
    """
    Verify you can configure additional network without gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration without gateway
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(9768, 282904)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertFalse(checkIPRule(host=config.HOSTS[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")
