"""
Testing Multiple Gateways feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Multiple Gateway will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
Only static IP configuration is tested.
"""

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from rhevmtests.networking import config
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup, removeNetwork,
    create_basic_setup, remove_basic_setup
)
from art.rhevm_api.tests_lib.low_level.networks import checkIPRule
from art.rhevm_api.tests_lib.low_level.hosts import(
    genSNNic, sendSNRequest, deactivateHost, activateHost, updateHost
)

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
IP = config.MG_IP_ADDR
NETMASK = config.NETMASK
GATEWAY = config.MG_GATEWAY
SUBNET = config.SUBNET
TIMEOUT = config.CONNECT_TIMEOUT
cl_name_1 = "".join([config.TEST_NAME, "_CL", "1"])
config.CLUSTER_NAME.append(cl_name_1)
logger = logging.getLogger(__name__)

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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 282894)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
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
                                      auto_nics=[config.VDS_HOSTS[0].nics[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force=False))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from DC/CLuster", config.NETWORKS[0])
        if not removeNetwork(True, network=config.NETWORKS[0]):
            raise NetworkException("Cannot remove network %s from DC/Cluster" %
                                   config.NETWORKS[0])


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

        local_dict = {config.VLAN_NETWORKS[0]: {'nic': 1,
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': False,
                                                'bootproto': 'static',
                                                'address': [IP],
                                                'netmask': [NETMASK],
                                                'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0, 1]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 282901)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from setup", config.VLAN_NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.VLAN_NETWORKS[0])


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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'usages': '',
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 282902)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.NETWORKS[0])


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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'cluster_usages': 'display',
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 283407)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup %s", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.NETWORKS[0])


@attr(tier=1)
class GatewaysCase5(TestCase):
    """
    Try to assign to vm network incorrect static IP and gw addresses
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        local_dict1 = {config.NETWORKS[0]: {'nic': 1,
                                            'required': False}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 283968)
    def check_incorrect_config(self):
        """
        Try to create logical  network on DC/Cluster/Hosts
        Configure it with static IP configuration and incorrect gateway or IP
        """

        logger.info("Trying to attach network %s with incorrect IP on NIC %s. "
                    "The test should fail to do it", config.NETWORKS[0],
                    config.HOST_NICS[1])
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
                             auto_nics=[config.VDS_HOSTS[0].nics[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force=False):
            raise NetworkException("Can setupNetworks when shouldn't")

        logger.info("Trying to attach network %s with incorrect gateway on NIC"
                    " %s. The test should fail to do it", config.NETWORKS[0],
                    config.HOST_NICS[1])
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
                             auto_nics=[config.VDS_HOSTS[0].nics[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force=False):
            raise NetworkException("Can setupNetworks when shouldn't")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.NETWORKS[0])


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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': ['0.0.0.0']}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.NETWORKS[0])


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
                                           'slaves': [2, 3],
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s")

    @istest
    @tcms(9768, 289694)
    def check_ip_rule(self):
        """
        Add additional NIC to the bond and check IP rule
        """
        logger.info("Checking IP rule before adding 3rd NIC")
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
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
                             auto_nics=[config.VDS_HOSTS[0].nics[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force=False):
            raise NetworkException("Cannot update bond to have 2 NICs")
        logger.info("Checking IP rule after adding 3rd NIC")
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.NETWORKS[0])


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
                                           'slaves': [2, 3, 1],
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 289695)
    def check_ip_rule(self):
        """
        Check the appearance of the subnet with ip rule command
        Remove a NIC from bond and check ip rule again
        """
        logger.info("Checking the IP rule before removing one NIC from bond")
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
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
                             auto_nics=[config.VDS_HOSTS[0].nics[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT, force=False):
            raise NetworkException("Cannot update bond to have 2 NICs")
        logger.info("Checking the IP rule after removing one NIC from bond")
        self.assertTrue(checkIPRule(config.HOSTS_IP[0],
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup",
                                   config.NETWORKS[0])


@attr(tier=1)
class GatewaysCase9(TestCase):
    """
    Verify you can't configure gateway on the network in 3.2 Cluster
    """
    __test__ = True
    uncomp_dc = "new_DC_case09"
    uncomp_cl = "new_CL_case09"

    @classmethod
    def setup_class(cls):
        """
        Create 3.2 Cluster and 3.2 DC
        """
        logger.info("Create Datacenter %s and Cluster %s , version %s",
                    cls.uncomp_dc, cls.uncomp_cl, config.VERSION[2])

        if not create_basic_setup(datacenter=cls.uncomp_dc,
                                  storage_type=config.STORAGE_TYPE,
                                  version=config.VERSION[2],
                                  cluster=cls.uncomp_cl,
                                  cpu=config.CPU_NAME):
            raise NetworkException("Failed to create Datacenter %s or Cluster "
                                   "%s" % (cls.uncomp_dc, cls.uncomp_cl))

    @istest
    @tcms(9768, 284029)
    def add_host_to_another_cluster(self):
        """
        Add host to the 3.2 Cluster
        Try to configure static IP with dg - should fail as in 3.2
        it is not supported
        """
        logger.info("Put the host %s on another Cluster %s",
                    config.HOSTS[0], self.uncomp_cl)
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=self.uncomp_cl):
            raise NetworkException("Cannot move host %s to another Cluster %s"
                                   % (config.HOSTS[0], self.uncomp_cl))
        assert(activateHost(True, host=config.HOSTS[0]))
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK],
                                           'gateway': [GATEWAY]}}
        self.assertFalse(
            createAndAttachNetworkSN(data_center=self.uncomp_dc,
                                     cluster=self.uncomp_cl,
                                     host=config.VDS_HOSTS[0],
                                     network_dict=local_dict,
                                     auto_nics=[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Put the host %s back to original Cluster %s",
                    config.HOSTS[0], config.CLUSTER_NAME[0])
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host %s to Cluster %s",
                                   (config.HOSTS[0], config.CLUSTER_NAME[0]))
        assert(activateHost(True, host=config.HOSTS[0]))
        logger.info("Removing DC %s and Cluster %s from the setup",
                    cls.uncomp_dc, cls.uncomp_cl)
        if not remove_basic_setup(datacenter=cls.uncomp_dc,
                                  cluster=cls.uncomp_cl):
            raise NetworkException("Failed to remove 3.2 DC and Cluster from "
                                   "setup")


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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': False,
                                           'bootproto': 'static',
                                           'address': [IP],
                                           'netmask': [NETMASK]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

    @istest
    @tcms(9768, 282904)
    def check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertFalse(checkIPRule(config.HOSTS_IP[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     subnet=SUBNET))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup" %
                                   config.NETWORKS[0])
