'''
Testing Sanity for the network features.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
Sanity will test untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
'''
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase
from art.test_handler.tools import tcms
import logging
from art.rhevm_api.tests_lib.high_level.storagedomains import addNFSDomain
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException,\
    StorageDomainException, VMException
from art.test_handler.settings import opts

import config
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, createDummyInterface,\
    deleteDummyInterface
from art.rhevm_api.tests_lib.low_level.hosts import \
    checkNetworkFilteringDumpxml, genSNNic, sendSNRequest, waitForHostsStates,\
    waitForSPM
from art.rhevm_api.tests_lib.low_level.vms import addNic,\
    removeNic, startVm,\
    checkVMConnectivity, waitForVmsStates, importVm, removeVm,\
    exportVm, shutdownVm, removeVmFromExportDomain, getVmNicLinked,\
    getVmNicPlugged, updateNic
from art.rhevm_api.tests_lib.low_level.networks import \
    updateClusterNetwork, isVMNetwork, isNetworkRequired,\
    updateNetwork, addVnicProfile, removeVnicProfile, removeNetwork
from art.rhevm_api.utils.test_utils import checkMTU,\
    checkSpoofingFilterRuleByVer
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    removeStorageDomain, detachStorageDomain, deactivateStorageDomain
from art.unittest_lib.network import skipBOND


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
TIMEOUT = 60
logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class SanityCase01_CheckManagment(TestCase):
    """
    Validate that MANAGEMENT is Required by default
    """
    __test__ = True

    @istest
    def validateMGMT(self):
        """
        Check that MGMT is required
        """
        logger.info("Checking that mgmt network is required by "
                    "default")
        self.assertTrue(isNetworkRequired(network=config.MGMT_BRIDGE,
                                          cluster=config.CLUSTER_NAME),
                        "mgmt network is not required by default")

########################################################################

########################################################################


class SanityCase02_CheckStaticIPHost(TestCase):
    """
    Check static ip:
    Creating network (sw162) with static ip, Attaching it to eth1,
    and finally, remove the network.
    """
    __test__ = True

    @istest
    def checkStaticIP(self):
        """
        Create vlan sw162 with static ip (1.1.1.1) on eth1
        """
        logger.info("Create network and attach it to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false',
                                                'bootproto': 'static',
                                                'address': ['1.1.1.1'],
                                                'netmask': ['255.255.255.0']}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network sw162 from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase03_CheckingVMNetworks_vlan(TestCase):
    """
    Check VM network & NON_VM network (vlan test):
    Creating two networks (sw162 & sw163) on eth1 while one is VM network
    and the other is NON_VM network. Then, Check that the creation of the
    networks created a proper networks (VM & NON_VM).
    Finally, removing the networks.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create vm network sw162 & non-vm network sw163
        Attach to the host as multi-networks with vlan (eth1)
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'usages': '',
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkNetworksUsages(self):
        """
        Checking that sw162 is a vm network & sw163 is a non-vm network
        """
        logger.info("Checking bridged network %s", config.VLAN_NETWORKS[0])
        self.assertTrue(isVMNetwork(network=config.VLAN_NETWORKS[0],
                                    cluster=config.CLUSTER_NAME),
                        "%s is not VM Network" % config.VLAN_NETWORKS[0])

        logger.info("Checking bridged network %s", config.VLAN_NETWORKS[1])
        self.assertFalse((isVMNetwork(network=config.VLAN_NETWORKS[1],
                                      cluster=config.CLUSTER_NAME)),
                         "%s is not NON_VM network" % config.VLAN_NETWORKS[1])

    @classmethod
    def teardown_class(cls):
        """
        Removing networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0],
                                            config.VLAN_NETWORKS[1]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase04_CheckingVMNetworks_bond(TestCase):
    """
    Check VM network & NON_VM network (bond test):
    Creating network sw164 on bond, composed of eth2 & eth3 as VM network than:
    1. Check that the creation of the network created a proper network (VM).
    2. Update sw164 to be NON_VM
    3. Check that the update of the network is proper (NON_VM).
    Finally, removing the networks.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create vm network sw164
        """
        logger.info("Create network and attach it to the host")
        local_dict = {config.VLAN_NETWORKS[2]: {'vlan_id': config.VLAN_ID[2],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkNetworksUsages(self):
        """
        Checking that sw164 is a vm network, Changing it to non_vm network
        and checking that it is not non_vm
        """
        logger.info("Checking bridged network %s", config.VLAN_NETWORKS[2])
        self.assertTrue(isVMNetwork(network=config.VLAN_NETWORKS[2],
                                    cluster=config.CLUSTER_NAME),
                        "%s is NON_VM network when it should be VM"
                        % config.VLAN_NETWORKS[2])

        logger.info("Updating %s to be NON_VM network",
                    config.VLAN_NETWORKS[2])
        if not updateNetwork(positive=True,
                             network=config.VLAN_NETWORKS[2],
                             cluster=config.CLUSTER_NAME, usages=''):
            logger.error("Failed to update %s to be NON_VM network",
                         config.VLAN_NETWORKS[2])
            return False

        logger.info("Checking bridged network %s", config.VLAN_NETWORKS[2])

        self.assertFalse(isVMNetwork(network=config.VLAN_NETWORKS[2],
                                     cluster=config.CLUSTER_NAME),
                         "%s is VM network when it should be NON_VM"
                         % config.VLAN_NETWORKS[2])

    @classmethod
    def teardown_class(cls):
        """
        Removing sw164 network from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetwork(True, config.VLAN_NETWORKS[2]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase05_CheckingPortMirroring_vlan(TestCase):
    """
    Checking Port Mirroring (vlan test):
    Creating vnic profile with network sw162 and port mirroring enabled,
    attaching it to eth1.
    Finally, remove nic and network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating sw162, adding to the to host and adding nic2 with this network
        """
        logger.info("Create profile with network sw162 and port mirroring"
                    "enabled and attach it to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create profile with %s network and port mirroring"
                    "enabled",
                    config.VLAN_NETWORKS[0])
        if not addVnicProfile(positive=True, name=config.VNIC_PROFILE[0],
                              cluster=config.CLUSTER_NAME,
                              network=config.VLAN_NETWORKS[0],
                              port_mirroring=True):
            logger.error("Failed to add %s profile with %s network to %s",
                         config.VNIC_PROFILE[0], config.VLAN_NETWORKS[0],
                         config.CLUSTER_NAME)

    @istest
    def attachVnicToVm(self):
        """
        Attaching vnic to VM
        """
        if not addNic(positive=True, vm=config.VM_NAME[0], name='nic2',
                      network=config.VLAN_NETWORKS[0]):
            logger.error("Adding nic2 failed")
            return False

    @classmethod
    def teardown_class(cls):
        """
        Remove nic and network from the setup
        """
        logger.info("Starting the teardown_class")
        if not updateNic(positive=True,
                         vm=config.VM_NAME[0],
                         nic='nic2',
                         plugged=False):
            logger.error("Unplug nic2 failed")
            return False

        if not removeNic(positive=True, vm=config.VM_NAME[0], nic='nic2'):
            logger.error("Removing nic2 failed")
            return False

        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0]])):
            raise NetworkException("Cannot remove network from setup")

        if not removeVnicProfile(positive=True,
                                 vnic_profile_name=config.VNIC_PROFILE[0],
                                 network=config.VLAN_NETWORKS[0]):
            logger.error("Failed to remove %s profile", config.VNIC_PROFILE[0])

########################################################################

########################################################################


class SanityCase07_CheckingRequiredNetwork_vlan(TestCase):
    """
    Checking required network (vlan test):
    Creating network sw162 as required and attaching it to the host(eth1),
    then:
    1. Verifying that the network is required
    2. Updating network to be not required
    3. Checking that the network is non-required
    Finally, removing the network from the setup.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating network sw162 as required and attaching it to the host
        """
        logger.info("Create network and attach it to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'true'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkRequired(self):
        """
        Verifying that the network is required,
        updating network to be not required and checking
        that the network is non-required
        """
        logger.info("network = %s, cluster = %s", config.VLAN_NETWORKS[0],
                    config.CLUSTER_NAME)
        self.assertTrue(isNetworkRequired(network=config.VLAN_NETWORKS[0],
                                          cluster=config.CLUSTER_NAME),
                        "Network %s is non-required, Should be required"
                        % config.VLAN_NETWORKS[0])

        if not updateClusterNetwork(positive=True,
                                    cluster=config.CLUSTER_NAME,
                                    network=config.VLAN_NETWORKS[0],
                                    required=False):
            logger.error("Updating %s to non-required failed"
                         % config.VLAN_NETWORKS[0])
            return False

        logger.info("network = %s, cluster = %s", config.VLAN_NETWORKS[0],
                    config.CLUSTER_NAME)
        self.assertFalse(isNetworkRequired(network=config.VLAN_NETWORKS[0],
                                           cluster=config.CLUSTER_NAME),
                         "Network %s is required, Should be non-required"
                         % config.VLAN_NETWORKS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0]])):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################


class SanityCase08_CheckingRequiredNetwork_bond(TestCase):
    """
    Checking required network (bond test):
    Creating network sw163 as required and attaching it to the host
    (eth2 & eth3), then:
    1. Verifying that the network is required
    2. Updating network to be not required
    3. Checking that the network is non-required
    Finally, removing the network from the setup.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info("Create network and attach it to the host")
        local_dict = {None: {'nic': config.BOND[0],
                             'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[1]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[1],
                                                'required': 'true'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkRequired(self):
        """
        Verifying that the network is required, updating network to be
        not required and then checking that the network is non-required
        """
        logger.info("network = %s, cluster = %s", config.VLAN_NETWORKS[1],
                    config.CLUSTER_NAME)
        self.assertTrue(isNetworkRequired(network=config.VLAN_NETWORKS[1],
                                          cluster=config.CLUSTER_NAME),
                        "Network %s is non-required, Should be required"
                        % config.VLAN_NETWORKS[1])

        if not updateClusterNetwork(positive=True, cluster=config.CLUSTER_NAME,
                                    network=config.VLAN_NETWORKS[1],
                                    required=False):
            logger.error("Updating %s to non-required failed"
                         % config.VLAN_NETWORKS[1])
            return False

        logger.info("network = %s, cluster = %s",
                    config.VLAN_NETWORKS[1],
                    config.CLUSTER_NAME)
        self.assertFalse(isNetworkRequired(network=config.VLAN_NETWORKS[1],
                                           cluster=config.CLUSTER_NAME),
                         "Network %s is required, Should be non-required"
                         % config.VLAN_NETWORKS[1])

    @classmethod
    def teardown_class(cls):
        """
        Removing the network from the setup.
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[1]])):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################

class SanityCase09_CheckingJumboFrames_vlan(TestCase):
    """
    Checking Jumbo Frame (vlan test):
    Creating and adding sw162 (MTU 9000) & sw163 (MTU 3500) to the host
    on eth1, then:
    1. Check that MTU on sw162 is really 9000
    2. Updating sw163's MTU to 1500
    2. Check that MTU on sw163 is really 1500
    Finally, removing sw162 & sw163 from the setup
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating and adding sw162 (MTU 9000) & sw163 (MTU 3500)to the host
        on eth1
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false',
                                                'mtu': 9000},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false',
                                                'mtu': 3500}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTU(self):
        """
        Check that MTU on sw162 and sw163 is really 9000 & 1500
        """
        self.assertTrue(checkMTU(host=config.HOSTS[0],
                                 user=config.HOSTS_USER,
                                 password=config.HOSTS_PW,
                                 mtu=9000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[0]),
                        "%s is not configured with MTU 9000"
                        % config.VLAN_NETWORKS[0])

        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 nic=config.HOST_NICS[1]))

        self.assertTrue(updateNetwork(positive=True,
                                      network=config.VLAN_NETWORKS[0],
                                      mtu=1500),
                        "%s was not updated" % config.VLAN_NETWORKS[0])

        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=checkMTU, host=config.HOSTS[0],
                                   user=config.HOSTS_USER,
                                   password=config.HOSTS_PW,
                                   mtu=1500,
                                   physical_layer=False,
                                   network=config.VLAN_NETWORKS[0],
                                   nic=config.HOST_NICS[1],
                                   vlan=config.VLAN_ID[0])

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU")

        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=3500,
                                 nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Removing sw162 & sw163 from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0],
                                            config.VLAN_NETWORKS[1]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase10_CheckingJumboFrames_bond(TestCase):
    """
    Checking Jumbo Frame (vlan test):
    Creating and adding sw162 (MTU 7000) to the host
    on eth2 & eth3, then checking that MTU on sw162 is really 7000
    Finally, removing sw162 from the setup
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating and adding sw162 (MTU 7000) to the host on eth2 & eth3
        """
        logger.info("Create network and attach it to the host")
        local_dict = {None: {'nic': config.BOND[0],
                             'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'mtu': 7000,
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTU(self):
        """
        Check that MTU on sw162 is really 7000
        """
        logger.info("Checking that %s was created with mtu = 7000"
                    % config.VLAN_NETWORKS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=7000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 nic=config.BOND[0],
                                 vlan=config.VLAN_ID[0]),
                        "%s is not configured with mtu = 7000"
                        % config.VLAN_NETWORKS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase11_CheckingNetworkFilter_vlan(TestCase):
    """
    Checking Network Filter (vlan test):
    Creating network sw162 and adding it to the host on eth1, then:
    test #1:
    1. Checking that network spoofing filter is enabled according to
       the rhevm's version.
    test #2:
    1. Checking that network spoofing filter is enabled on the vm via
       dumpxml
    Finally, Removing nic2 and sw162
    """
    __test__ = True
    """
    Need investigation, this test always fails
    """

    @classmethod
    def setup_class(cls):
        """
        Creating network sw162 and adding it to the host on eth1
        """
        logger.info("Create network and attach it to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkNwfilterOnRhevm(self):
        """
        Checking that network spoofing filter is enabled according to
        the rhevm's version.
        """
        logger.info("Checking that spoofing filter is enabled")
        self.assertTrue(checkSpoofingFilterRuleByVer(
            host=config.RHEVM_NAME,
            user=config.HOSTS_USER,
            passwd=config.HOSTS_PW),
            "Spoofing filter is not enabled")

    @istest
    def checkNwfilterOnVM(self):
        """
        Checking that network spoofing filter is enabled on the vm
        """
        logger.info("Checking that spoofing filter is enabled via dumpxml")
        self.assertTrue(checkNetworkFilteringDumpxml(
            positive=True,
            host=config.HOSTS[0],
            user=config.HOSTS_USER,
            passwd=config.HOSTS_PW,
            vm=config.VM_NAME[0],
            nics='1'), "DumpXML for 1 nic return wrong output")

        # Add nic is part of the test.
        if not addNic(positive=True, vm=config.VM_NAME[0], name='nic2',
                      network=config.VLAN_NETWORKS[0]):
            logger.error("Adding nic2 failed")
            return False

        self.assertTrue(checkNetworkFilteringDumpxml(
            positive=True,
            host=config.HOSTS[0],
            user=config.HOSTS_USER,
            passwd=config.HOSTS_PW,
            vm=config.VM_NAME[0],
            nics='2'), "DumpXML for 2 nics return wrong output")

    @classmethod
    def teardown_class(cls):
        """
        Remove nic2 and sw162 from the setup
        """
        logger.info("Starting the teardown_class")
        if not updateNic(positive=True,
                         vm=config.VM_NAME[0],
                         nic='nic2',
                         plugged=False):
            logger.error("Unplug nic2 failed")
            return False

        if not removeNic(positive=True, vm=config.VM_NAME[0], nic='nic2'):
            logger.error("Removing nic2 failed")
            return False

        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase12_CheckingLinking_vlan(TestCase):
    """
    Checking Linking Nic (vlan test):
    Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
    the host. Then creating vnics (with all permutations of plugged & linked)
    and attaching them to the vm, then:
    1. Checking that all the permutations of plugged & linked are correct
    Finally, Removing the nics and networks.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
        the host. Then creating vnics (with all permutations of
        plugged & linked) and attaching them to the vm
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[2]: {'vlan_id': config.VLAN_ID[2],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[3]: {'vlan_id': config.VLAN_ID[3],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [('true', 'true'), ('true', 'false'),
                                ('false', 'true'), ('false', 'false')]
        for i in range(len(plug_link_param_list)):
            if not addNic(True, config.VM_NAME[0], name='nic'+str(i+2),
                          network=config.VLAN_NETWORKS[i],
                          plugged=plug_link_param_list[i][0],
                          linked=plug_link_param_list[i][1]):
                raise VMException("Cannot add nic%s to VM" % (i+2))

    @istest
    def checkCombinationPluggedLinkedValues(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info("Checking Linked on nic2, nic4 is True")
        for nic_name in ('nic2', 'nic4'):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic2, nic3 is True")
        for nic_name in ('nic2', 'nic3'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        """
        Removing the nics and networks.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside mgmt network to "
                    "unplugged")
        for nic_name in ('nic2', 'nic3'):
            updateNic(True, config.VM_NAME[0], nic_name, plugged=False)
        logger.info("Removing all the VNICs besides mgmt network")
        for i in range(4):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0],
                                            config.VLAN_NETWORKS[1],
                                            config.VLAN_NETWORKS[2],
                                            config.VLAN_NETWORKS[3]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase13_CheckingLinking_bond(TestCase):
    """
    Checking Linking Nic (bond test):
    Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
    the host. Then creating vnics (with all permutations of plugged & linked)
    and attaching them to the vm, then:
    1. Checking that all the permutations of plugged & linked are correct
    Finally, Removing the nics and networks.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
        the host. Then creating vnics (with all permutations of plugged
        & linked) and attaching them to the vm
        """
        logger.info("Create network and attach it to the host")
        local_dict = {None: {'nic': config.BOND[0],
                             'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[2]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[2],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[3]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[3],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [('true', 'true'), ('true', 'false'),
                                ('false', 'true'), ('false', 'false')]
        for i in range(len(plug_link_param_list)):
            if not addNic(True, config.VM_NAME[0], name='nic'+str(i+2),
                          network=config.VLAN_NETWORKS[i],
                          plugged=plug_link_param_list[i][0],
                          linked=plug_link_param_list[i][1]):
                raise VMException("Cannot add nic%s to VM" % (i+2))

    @istest
    def checkCombinationPluggedLinkedValues(self):
        """
        Checking that all the permutations of plugged & linked are correct
        """
        logger.info("Checking Linked on nic2, nic4 is True")
        for nic_name in ('nic2', 'nic4'):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic2, nic3 is True")
        for nic_name in ('nic2', 'nic3'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        """
        Removing the nics and networks
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks besides mgmt network to "
                    "unplugged")
        for nic_name in ('nic2', 'nic3'):
            updateNic(True, config.VM_NAME[0], nic_name, plugged=False)
        logger.info("Removing all the VNICs beside mgmt network")
        for i in range(4):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0],
                                            config.VLAN_NETWORKS[1],
                                            config.VLAN_NETWORKS[2],
                                            config.VLAN_NETWORKS[3]])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class SanityCase14_CheckingImportExport_vlan(TestCase):
    """
    Checking import/export (vlan test):
    Creating and adding:
        Network: Create and attach sw162 to the host
        Storage: Adding import/export domain
    Then,
    1. Checking connectivity to vm
    2. Shutting down vm
    3. Exporting vm to the import/ export domain
    4. Removing the vm
    5. Importing vm from the import/ export domain
    6. Starting vm
    7. Checking connectivity to vm
    Finally, Removing import/ export domain & network sw162
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Creating and adding:
            Network: Create and attach network sw162 to the host
            Storage: Adding import/export domain
        """
        logger.info("Create network and attach it to the host")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Adding storage domain")
        if not addNFSDomain(host=config.HOSTS[0],
                            storage=config.EXPORT_STORAGE_NAME,
                            data_center=config.DC_NAME,
                            address=config.EXPORT_STORAGE_ADDRESS,
                            path=config.EXPORT_STORAGE_PATH,
                            sd_type='export'):
            raise StorageDomainException("Cannot add storage domain to DC")

    @istest
    def checkImportExportVM(self):
        """
        We check connectivity to the vm, shutting it down, exporting it to
        import/ export domain, removing it from the rhevm, importing the vm
        from the import/ export domain, starting vm and then checking
        connectivity to vm
        """
        logger.info("Checking connectivity with %s", config.VM_NAME[0])
        self.assertTrue(checkVMConnectivity(positive=True,
                                            vm=config.VM_NAME[0],
                                            osType="rhel",
                                            attempt=60,
                                            interval=3,
                                            user=config.HOSTS_USER,
                                            password=config.HOSTS_PW,
                                            nic='nic1'),
                        "Connectivity with %s failed" % config.VM_NAME[0])

        logger.info("Shutting down %s", config.VM_NAME[0])
        if not shutdownVm(positive=True,
                          vm=config.VM_NAME[0]):
            logger.error("Failed to shut down %s", config.VM_NAME[0])
            return False

        logger.info("Waiting for %s to reach down state", config.VM_NAME[0])
        if not waitForVmsStates(positive=True,
                                names=config.VM_NAME[0],
                                timeout=config.TIMEOUT,
                                states='down'):
            logger.error("VM's state is incorrect")
            return False

        logger.info("Exporting %s to %s",
                    config.VM_NAME[0], config.EXPORT_STORAGE_NAME)
        self.assertTrue(exportVm(positive=True,
                                 vm=config.VM_NAME[0],
                                 storagedomain=config.EXPORT_STORAGE_NAME),
                        "Exporting " + config.VM_NAME[0] + " to " +
                        config.EXPORT_STORAGE_NAME + " failed")

        logger.info("Removing %s", config.VM_NAME[0])
        if not removeVm(positive=True,
                        vm=config.VM_NAME[0]):
            logger.error("Unable to remove VM")
            return False

        logger.info("Importing %s from %s",
                    config.VM_NAME[0], config.EXPORT_STORAGE_NAME)
        self.assertTrue(importVm(positive=True,
                                 vm=config.VM_NAME[0],
                                 import_storagedomain=
                                 config.DC_NAME + '_data_domain0',
                                 export_storagedomain=
                                 config.EXPORT_STORAGE_NAME,
                                 cluster=config.CLUSTER_NAME),
                        "Importing " + config.VM_NAME[0] + " from " +
                        config.EXPORT_STORAGE_NAME + " failed")

        logger.info("Waiting for %s to reach down state", config.VM_NAME[0])
        if not waitForVmsStates(positive=True,
                                names=config.VM_NAME[0],
                                timeout=config.TIMEOUT,
                                states='down'):
            logger.error("VM's state is incorrect")
            return False

        logger.info("Starting %s", config.VM_NAME[0])
        if not startVm(positive=True,
                       vm=config.VM_NAME[0]):
            logger.error("VM failed to start")
            return False

        logger.info("Checking connectivity with %s", config.VM_NAME[0])
        self.assertTrue(checkVMConnectivity(positive=True,
                                            vm=config.VM_NAME[0],
                                            osType="rhel",
                                            attempt=60,
                                            interval=3,
                                            user=config.HOSTS_USER,
                                            password=config.HOSTS_PW,
                                            nic='nic1'),
                        "Connectivity with %s failed" % config.VM_NAME[0])

    @classmethod
    def teardown_class(cls):
        """
        Removing import/ export domain & network sw162
        """
        logger.info("Starting the teardown_class")
        logger.info("Removing %s from export domain", config.VM_NAME[0])
        if not removeVmFromExportDomain(positive=True,
                                        vm=config.VM_NAME[0],
                                        datacenter=config.DC_NAME,
                                        export_storagedomain=
                                        config.EXPORT_STORAGE_NAME):
            logger.error("removing %s from export domain failed",
                         config.DC_NAME)
            return False

        if not (removeNetFromSetup(host=config.HOSTS[0],
                                   auto_nics=[config.HOST_NICS[0]],
                                   network=[config.VLAN_NETWORKS[0]])):
            raise NetworkException("Cannot remove network from setup")

        logger.info("Deactivating storage domain (import/export)")
        if not (deactivateStorageDomain(positive=True,
                                        datacenter=config.DC_NAME,
                                        storagedomain=
                                        config.EXPORT_STORAGE_NAME)):
            raise NetworkException("Cannot deactivate storage domain")

        logger.info("Detaching storage domain")
        if not (detachStorageDomain(positive=True,
                                    datacenter=config.DC_NAME,
                                    storagedomain=config.EXPORT_STORAGE_NAME)):
            raise NetworkException("Cannot detach storage domain")

        logger.info("Removing storage domain")
        if not (removeStorageDomain(positive=True,
                                    storagedomain=config.EXPORT_STORAGE_NAME,
                                    host=config.HOSTS[0])):
            raise NetworkException("Cannot remove storage domain")


class SanityCase15_275464(TestCase):
    """
    Positive: Creates bridged network over bond on Host with custom name
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks on DC/Cluster/Hosts over bond with custom name
        """

        local_dict = {None: {'nic': 'bond012345', 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': 'bond012345',
                                                'mtu': 5000,
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(6957, 275464)
    def bondModeChange(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers for Jumbo bond ")
        logger.info("Checking logical layer of sw1 over bond")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond='bond012345',
                                 bridged=True))
        logger.info("Checking physical layer of sw1 over bond ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond012345',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=True))
        logger.info("Changing the bond mode to  mode4")
        rc, out = genSNNic(nic='bond012345', network=config.VLAN_NETWORKS[0],
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]], mode=4)

        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(positive=True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0]],
                      check_connectivity='true',
                      connectivity_timeout=60, force='false')
        logger.info("Checking layers after bond mode change")
        logger.info("Checking logical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond='bond012345',
                                 bridged=True))
        logger.info("Checking physical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond012345',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3], bridged=True))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]],
                                  data_center=config.DC_NAME):
            raise NetworkException("Cannot create and attach network")


class SanityCase16_275471_bondMaxLength(TestCase):
    """
    Negative: Bond with exceeded name length (more than 15 chars)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
            pass

    @istest
    @tcms(6958, 275471)
    def bondMaxLength(self):
        """
        Create BOND: exceed allowed length (max 15 chars)
        """
        logger.info("Generating bond012345678901 object with 2 NIC")
        net_obj = []
        rc, out = genSNNic(nic='bond012345678901',
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNReauest: bond012345678901")
        self.assertTrue(sendSNRequest(False, host=config.HOSTS[0],
                                      nics=net_obj,
                                      auto_nics=[config.HOST_NICS[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


class SanityCase17_275471_bondPrefix(TestCase):
    """
    Negative:  Try to create bond with wrong prefix
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(6958, 275471)
    def bondPrefix(self):
        """
        Create BOND: use wrong prefix (eg. NET1515)
        """
        logger.info("Generating NET1515 object with 2 NIC bond")
        net_obj = []
        rc, out = genSNNic(nic='NET1515',
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNReauest: NET1515")
        self.assertTrue(sendSNRequest(False, host=config.HOSTS[0],
                                      nics=net_obj,
                                      auto_nics=[config.HOST_NICS[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


class SanityCase18_275471_bondSuffix(TestCase):
    """
    Negative: Try to create bond with wrong suffix
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(6958, 275471)
    def bondSuffix(self):
        """
        Create BOND: use wrong suffix (e.g. bond1!)
        """
        logger.info("Generating bond1! object with 2 NIC bond")
        net_obj = []
        rc, out = genSNNic(nic='bond1!',
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNReauest: bond1!")
        self.assertTrue(sendSNRequest(False, host=config.HOSTS[0],
                                      nics=net_obj,
                                      auto_nics=[config.HOST_NICS[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


class SanityCase19_275471_bondEmpty(TestCase):
    """
    Negative: Try to create bond with empty name
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(6958, 275471)
    def bondEmpty(self):
        """
        Create BOND: leave name field empty
        """
        logger.info("Generating bond object with 2 NIC bond and empty name")
        net_obj = []
        rc, out = genSNNic(nic='',
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNReauest: empty bond name")
        self.assertTrue(sendSNRequest(False, host=config.HOSTS[0],
                                      nics=net_obj,
                                      auto_nics=[config.HOST_NICS[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


class SanityCase20_275813_MoreThen5BONDS(TestCase):
    """
    Negative: Create more then 5 BONDS using dummy interfaces
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create dummy interface for BONDS
        """
        logger.info("Creating 20 dummy interfaces")
        if not createDummyInterface(host=config.HOSTS[0],
                                    username=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    num_dummy=20):
            logger.error("Faild to create dummy interfaces")

    @istest
    @tcms(6957, 275813)
    def dummyBonds(self):
        """
        Create 10 BONDS using dummy interfaces
        """
        logger.info("Generating bond object with 2 dummy interfaces")
        net_obj = []
        idx = 0
        while idx < 20:
            rc, out = genSNNic(nic="bond%s" % idx,
                               slaves=["dummy%s" % idx,
                                       "dummy%s" % (idx + 1)])
            if not rc:
                raise NetworkException("Cannot generate SNNIC object")
            net_obj.append(out['host_nic'])
            idx += 2

        logger.info("Wait for %s to be UP", config.HOSTS[0])
        if not waitForHostsStates(True, config.HOSTS[0], states='up',
                                  timeout=600):
            logger.error("%s is not in UP state", config.HOSTS[0])

        logger.info("sending SNReauest: 10 bonds on dummy interfaces")
        if not sendSNRequest(True, host=config.HOSTS[0],
                             nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT,
                             force='false'):
            logger.error("Failed to SNRequest: bond1")

    @classmethod
    def teardown_class(cls):
        """
        Delete all bonds and dummy interfaces
        """
        if not deleteDummyInterface(host=config.HOSTS[0],
                                    username=config.HOSTS_USER,
                                    password=config.HOSTS_PW):
            logger.error("Failed to delete dummy interfaces")

        logger.info("Wait for %s to be UP", config.HOSTS[0])
        if not waitForHostsStates(True, config.HOSTS[0], states='up',
                                  timeout=600):
            logger.error("%s is not in UP state", config.HOSTS[0])

        if not waitForSPM(config.DC_NAME, 600, 30):
            logger.error("No SPM in %s", config.DC_NAME)
            return False

########################################################################

########################################################################


skipBOND([SanityCase04_CheckingVMNetworks_bond,
          SanityCase08_CheckingRequiredNetwork_bond,
          SanityCase10_CheckingJumboFrames_bond,
          SanityCase13_CheckingLinking_bond,
          SanityCase15_275464,
          SanityCase16_275471_bondMaxLength,
          SanityCase17_275471_bondPrefix,
          SanityCase18_275471_bondSuffix,
          SanityCase19_275471_bondEmpty], config.HOST_NICS)
