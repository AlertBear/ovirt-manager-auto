'''
Testing Sanity for the network features.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
Sanity will test untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
'''
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
import logging
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException, VMException
from art.test_handler.settings import opts

from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, createDummyInterface,\
    deleteDummyInterface
from art.rhevm_api.tests_lib.low_level.hosts import \
    checkNetworkFilteringDumpxml, genSNNic, sendSNRequest, waitForHostsStates,\
    waitForSPM, getHostCluster, getHostDC
from art.rhevm_api.tests_lib.low_level.vms import addNic,\
    removeNic, getVmNicLinked, getVmNicPlugged, updateNic, get_vms_from_cluster
from art.rhevm_api.tests_lib.low_level.networks import \
    updateClusterNetwork, isVMNetwork, isNetworkRequired,\
    updateNetwork, addVnicProfile, removeVnicProfile, removeNetwork
from art.rhevm_api.utils.test_utils import checkMTU,\
    checkSpoofingFilterRuleByVer

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
TIMEOUT = 60
logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=0)
class SanityCase01(TestCase):
    """
    Validate that MANAGEMENT is Required by default
    """
    __test__ = True

    @istest
    def validate_mgmt(self):
        """
        Check that MGMT is required
        """
        logger.info("Checking that mgmt network is required by "
                    "default")
        self.assertTrue(isNetworkRequired(network=config.MGMT_BRIDGE,
                                          cluster=config.CLUSTER_NAME[0]),
                        "mgmt network is not required by default")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase02(TestCase):
    """
    Check static ip:
    Creating network (sw162) with static ip, Attaching it to eth1,
    and finally, remove the network.
    """
    __test__ = True
    host = config.NETWORK_HOSTS[0]
    vlan = config.VLAN_NETWORKS[0]

    @istest
    def check_static_ip(self):
        """
        Create vlan sw162 with static ip (1.1.1.1) on eth1
        """
        logger.info("Create network and attach it to the host")

        local_dict = {self.vlan: {'vlan_id': config.VLAN_ID[0],
                                  'nic': self.host.nics[1],
                                  'required': 'false',
                                  'bootproto': 'static',
                                  'address': ['1.1.1.1'],
                                  'netmask': ['255.255.255.0']}}

        if not createAndAttachNetworkSN(data_center=getHostDC(self.host.name),
                                        cluster=getHostCluster(self.host.name),
                                        host=self.host.name,
                                        network_dict=local_dict,
                                        auto_nics=self.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network sw162 from the setup
        """
        logger.info("Starting the teardown_class")

        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase03(TestCase):
    """
    Check VM network & NON_VM network (vlan test):
    Creating two networks (sw162 & sw163) on eth1 while one is VM network
    and the other is NON_VM network. Then, Check that the creation of the
    networks created a proper networks (VM & NON_VM).
    Finally, removing the networks.
    """
    __test__ = True
    host = config.NETWORK_HOSTS[0]
    vlan1 = config.VLAN_NETWORKS[0]
    vlan2 = config.VLAN_NETWORKS[1]

    @classmethod
    def setup_class(cls):
        """
        Create vm network sw162 & non-vm network sw163
        Attach to the host as multi-networks with vlan (eth1)
        """

        logger.info("Create networks and attach them to the host")
        local_dict = {cls.vlan1: {'vlan_id': config.VLAN_ID[0],
                                  'nic': cls.host.nics[1],
                                  'required': 'false'},
                      cls.vlan2: {'vlan_id': config.VLAN_ID[1],
                                  'usages': '',
                                  'nic': cls.host.nics[1],
                                  'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=getHostDC(cls.host.name),
                                        cluster=getHostCluster(cls.host.name),
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_networks_usages(self):
        """
        Checking that sw162 is a vm network & sw163 is a non-vm network
        """
        logger.info("Checking bridged network %s", self.vlan1)
        self.assertTrue(isVMNetwork(network=self.vlan1,
                                    cluster=getHostCluster(self.host.name)),
                        "%s is not VM Network" % self.vlan1)

        logger.info("Checking bridged network %s", self.vlan2)
        self.assertFalse(isVMNetwork(network=self.vlan2,
                                     cluster=getHostCluster(self.host.name)),
                         "%s is not NON_VM network" % self.vlan2)

    @classmethod
    def teardown_class(cls):
        """
        Removing networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan1, cls.vlan2])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase04(TestCase):
    """
    Check VM network & NON_VM network:
    1. Check that the creation of the network created a proper network (VM).
    2. Update sw164 to be NON_VM
    3. Check that the update of the network is proper (NON_VM).
    Finally, removing the networks.
    """
    __test__ = True
    vlan = config.VLAN_NETWORKS[2]
    host = config.NETWORK_HOSTS[0]

    @classmethod
    def setup_class(cls):
        """
        Create vm network sw164
        """
        logger.info("Create network and attach it to the host")
        local_dict = {cls.vlan: {'vlan_id': config.VLAN_ID[2],
                                 'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=getHostDC(cls.host.name),
                                        cluster=getHostCluster(cls.host.name),
                                        network_dict=local_dict):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_networks_usages(self):
        """
        Checking that sw164 is a vm network, Changing it to non_vm network
        and checking that it is not non_vm
        """
        cluster = getHostCluster(self.host.name)
        logger.info("Checking bridged network %s", self.vlan)
        self.assertTrue(isVMNetwork(network=self.vlan,
                                    cluster=getHostCluster(self.host.name)),
                        "%s is NON_VM network but it should be VM" % self.vlan)

        logger.info("Updating %s to be NON_VM network", self.vlan)
        if not updateNetwork(positive=True, network=self.vlan, usages='',
                             cluster=cluster):
            logger.error("Failed to update %s to be NON_VM network", self.vlan)
            return False

        logger.info("Checking bridged network %s", self.vlan)

        self.assertFalse(
            isVMNetwork(network=self.vlan, cluster=cluster),
            "%s is VM network when it should be NON_VM" % self.vlan)

    @classmethod
    def teardown_class(cls):
        """
        Removing sw164 network from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetwork(True, cls.vlan):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase05(TestCase):
    """
    Checking Port Mirroring (vlan test):
    Creating vnic profile with network sw162 and port mirroring enabled,
    attaching it to eth1.
    Finally, remove nic and network
    """
    __test__ = True
    vlan = config.VLAN_NETWORKS[0]
    host = config.NETWORK_HOSTS[0]
    cluster = getHostCluster(host.name)
    vm = get_vms_from_cluster(cluster)[0]
    nic = "nic2"
    vnic_profile = config.VNIC_PROFILE[0]

    @classmethod
    def setup_class(cls):
        """
        Creating sw162, adding to the to host and adding nic2 with this network
        """
        logger.info("Create profile with network sw162 and port mirroring"
                    "enabled and attach it to the host")
        local_dict = {cls.vlan: {'vlan_id': config.VLAN_ID[0],
                                 'nic': cls.host.nics[1],
                                 'required': 'false'}}
        cluster = getHostCluster(cls.host.name)

        if not createAndAttachNetworkSN(data_center=getHostDC(cls.host.name),
                                        cluster=cluster, host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create profile with %s network and port mirroring"
                    "enabled", cls.vlan)
        if not addVnicProfile(positive=True, name=cls.vnic_profile,
                              cluster=cluster, network=cls.vlan,
                              port_mirroring=True):
            logger.error("Failed to add %s profile with %s network to %s",
                         config.VNIC_PROFILE[0], cls.vlan, cluster)

    @istest
    def attach_vnic_to_vm(self):
        """
        Attaching vnic to VM
        """
        if not addNic(positive=True, vm=self.vm, name=self.nic,
                      network=self.vlan):
            logger.error("Adding nic2 failed")
            raise NetworkException("Adding nic2 failed")

    @classmethod
    def teardown_class(cls):
        """
        Remove nic and network from the setup
        """
        logger.info("Starting the teardown_class")
        if not updateNic(positive=True, vm=cls.vm, nic=cls.nic, plugged=False):
            logger.error("Unplug nic2 failed")
            return False

        if not removeNic(positive=True, vm=cls.vm, nic=cls.nic):
            logger.error("Removing nic2 failed")
            return False

        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan])):
            raise NetworkException("Cannot remove network from setup")

        if not removeVnicProfile(positive=True,
                                 vnic_profile_name=cls.vnic_profile,
                                 network=cls.vlan):
            logger.error("Failed to remove %s profile", cls.vnic_profile)

########################################################################

########################################################################


@attr(tier=0)
class SanityCase06(TestCase):
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
    vlan = config.VLAN_NETWORKS[0]
    host = config.NETWORK_HOSTS[0]
    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    @classmethod
    def setup_class(cls):
        """
        Creating network sw162 as required and attaching it to the host
        """
        logger.info("Create network and attach it to the host")
        local_dict = {cls.vlan: {'vlan_id': config.VLAN_ID[0],
                                 'nic': cls.host.nics[1],
                                 'required': 'true'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_required(self):
        """
        Verifying that the network is required,
        updating network to be not required and checking
        that the network is non-required
        """
        logger.info("network = %s, cluster = %s", self.vlan, self.cluster)
        self.assertTrue(
            isNetworkRequired(network=self.vlan, cluster=self.cluster),
            "Network %s is non-required, Should be required" % self.vlan)

        if not updateClusterNetwork(positive=True, cluster=self.cluster,
                                    network=self.vlan, required=False):
            logger.error("Updating %s to non-required failed", self.vlan)
            return False

        logger.info("network = %s, cluster = %s", self.vlan, self.cluster)
        self.assertFalse(
            isNetworkRequired(network=self.vlan, cluster=self.cluster),
            "Network %s is required, Should be non-required" % self.vlan)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan])):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################


@attr(tier=0)
class SanityCase07(TestCase):
    """
    Checking required network (bond test):
    Creating network sw163 as required and attaching it to the host
    (eth2 & eth3), then:
    1. Verifying that the network is required
    2. Updating network to be not required
    3. Checking that the network is non-required
    Finally, removing the network from the setup.
    """
    host = config.NETWORK_HOSTS[0]
    __test__ = len(host.nics) > 3
    bond = config.BOND[0]
    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)
    vlan = config.VLAN_NETWORKS[1]

    @classmethod
    def setup_class(cls):
        logger.info("Create network and attach it to the host")
        local_dict = {None: {'nic': cls.bond,
                             'mode': 1,
                             'slaves': [cls.host.nics[2],
                                        cls.host.nics[3]]},
                      config.VLAN_NETWORKS[1]: {'nic': cls.bond,
                                                'vlan_id': config.VLAN_ID[1],
                                                'required': 'true'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=[cls.host.nics[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_required(self):
        """
        Verifying that the network is required, updating network to be
        not required and then checking that the network is non-required
        """
        logger.info("network = %s, cluster = %s", self.vlan, self.cluster)
        self.assertTrue(
            isNetworkRequired(network=self.vlan, cluster=self.cluster),
            "Network %s is non-required, Should be required" % self.vlan)

        if not updateClusterNetwork(positive=True, cluster=self.cluster,
                                    network=self.vlan, required=False):
            logger.error("Updating %s to non-required failed", self.vlan)
            return False

        logger.info("network = %s, cluster = %s", self.vlan, self.cluster)
        self.assertFalse(
            isNetworkRequired(network=self.vlan, cluster=self.cluster),
            "Network %s is required, Should be non-required" % self.vlan)

    @classmethod
    def teardown_class(cls):
        """
        Removing the network from the setup.
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan])):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################

@attr(tier=0)
class SanityCase08(TestCase):
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
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_2 = config.VLAN_NETWORKS[1]
    host = config.NETWORK_HOSTS[0]
    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)
    vlan_id_1 = config.VLAN_ID[0]
    vlan_id_2 = config.VLAN_ID[1]
    nic = host.nics[1]

    @classmethod
    def setup_class(cls):
        """
        Creating and adding sw162 (MTU 9000) & sw163 (MTU 3500)to the host
        on eth1
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {cls.vlan_1: {'vlan_id': cls.vlan_id_1,
                                   'nic': cls.nic,
                                   'required': 'false',
                                   'mtu': 9000},
                      cls.vlan_2: {'vlan_id': cls.vlan_id_2,
                                   'nic': cls.nic,
                                   'required': 'false',
                                   'mtu': 3500}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_mtu(self):
        """
        Check that MTU on sw162 and sw163 is really 9000 & 1500
        """
        self.assertTrue(checkMTU(host=self.host.ip,
                                 user=self.host.user,
                                 password=self.host.password,
                                 mtu=9000, physical_layer=False,
                                 network=self.vlan_1, nic=self.nic,
                                 vlan=self.vlan_id_1),
                        "%s is not configured with MTU 9000" % self.vlan_1)

        self.assertTrue(checkMTU(host=self.host.ip, user=self.host.user,
                                 password=self.host.password, mtu=9000,
                                 nic=self.nic))

        self.assertTrue(updateNetwork(positive=True, network=self.vlan_1,
                                      mtu=1500),
                        "%s was not updated" % self.vlan_1)

        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=checkMTU, host=self.host.ip,
                                   user=self.host.user,
                                   password=self.host.password,
                                   mtu=1500, physical_layer=False,
                                   network=self.vlan_1,
                                   nic=self.nic,
                                   vlan=self.vlan_id_1)

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU")

        self.assertTrue(checkMTU(host=self.host.ip, user=self.host.user,
                                 password=self.host.password, mtu=3500,
                                 nic=self.nic))

    @classmethod
    def teardown_class(cls):
        """
        Removing sw162 & sw163 from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan_1, cls.vlan_2])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase09(TestCase):
    """
    Checking Jumbo Frame (vlan test):
    Creating and adding sw162 (MTU 7000) to the host
    on eth2 & eth3, then checking that MTU on sw162 is really 7000
    Finally, removing sw162 from the setup
    """
    host = config.NETWORK_HOSTS[0]
    __test__ = len(host.nics) > 3
    bond = config.BOND[0]
    vlan = config.VLAN_NETWORKS[0]
    vlan_id = config.VLAN_ID[0]
    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    @classmethod
    def setup_class(cls):
        """
        Creating and adding sw162 (MTU 7000) to the host on eth2 & eth3
        """
        logger.info("Create network and attach it to the host")
        local_dict = {None: {'nic': cls.bond,
                             'mode': 1,
                             'slaves': cls.host.nics[2:4]},
                      config.VLAN_NETWORKS[0]: {'nic': cls.bond,
                                                'vlan_id': cls.vlan_id,
                                                'mtu': 7000,
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=[cls.host.nics[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_mtu(self):
        """
        Check that MTU on sw162 is really 7000
        """
        logger.info("Checking that %s was created with mtu = 7000", self.vlan)
        self.assertTrue(checkMTU(host=self.host.ip, user=self.host.user,
                                 password=self.host.password, mtu=7000,
                                 physical_layer=False, network=self.vlan,
                                 nic=self.bond, vlan=self.vlan_id),
                        "%s is not configured with mtu = 7000" % self.vlan)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase10(TestCase):
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
    host = config.NETWORK_HOSTS[0]
    vlan = config.VLAN_NETWORKS[0]
    vlan_id = config.VLAN_ID[0]
    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)
    vm = get_vms_from_cluster(cluster)[0]
    vm_nic = 'nic2'

    @classmethod
    def setup_class(cls):
        """
        Creating network sw162 and adding it to the host on eth1
        """
        logger.info("Create network and attach it to the host")
        local_dict = {cls.vlan: {'vlan_id': cls.vlan_id,
                                 'nic': cls.host.nics[1],
                                 'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def check_nwfilter_on_rhevm(self):
        """
        Checking that network spoofing filter is enabled according to
        the rhevm's version.
        """
        logger.info("Checking that spoofing filter is enabled")
        self.assertTrue(
            checkSpoofingFilterRuleByVer(
                host=config.VDC_HOST,
                user=config.VDC_ROOT_USER,
                passwd=config.VDC_ROOT_PASSWORD),
            "Spoofing filter is not enabled")

    @istest
    def check_nwfilter_on_vm(self):
        """
        Checking that network spoofing filter is enabled on the vm
        """
        logger.info("Checking that spoofing filter is enabled via dumpxml")
        self.assertTrue(
            checkNetworkFilteringDumpxml(
                positive=True,
                host=self.host.ip,
                user=self.host.user,
                passwd=self.host.password,
                vm=self.vm,
                nics='1'),
            "DumpXML for 1 nic return wrong output")

        # Add nic is part of the test.
        if not addNic(positive=True, vm=self.vm, name=self.vm_nic,
                      network=self.vlan):
            logger.error("Adding nic2 failed")
            return False

        self.assertTrue(
            checkNetworkFilteringDumpxml(
                positive=True,
                host=self.host.ip,
                user=self.host.user,
                passwd=self.host.password,
                vm=self.vm,
                nics='2'),
            "DumpXML for 2 nics return wrong output")

    @classmethod
    def teardown_class(cls):
        """
        Remove nic2 and sw162 from the setup
        """
        logger.info("Starting the teardown_class")
        if not updateNic(positive=True, vm=cls.vm, nic=cls.vm_nic,
                         plugged=False):
            logger.error("Unplug nic2 failed")
            return False

        if not removeNic(positive=True, vm=cls.vm, nic=cls.vm_nic):
            logger.error("Removing nic2 failed")
            return False

        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase11(TestCase):
    """
    Checking Linking Nic (vlan test):
    Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
    the host. Then creating vnics (with all permutations of plugged & linked)
    and attaching them to the vm, then:
    1. Checking that all the permutations of plugged & linked are correct
    Finally, Removing the nics and networks.
    """
    __test__ = True
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_2 = config.VLAN_NETWORKS[1]
    vlan_3 = config.VLAN_NETWORKS[2]
    vlan_4 = config.VLAN_NETWORKS[3]
    vlan_id_1 = config.VLAN_ID[0]
    vlan_id_2 = config.VLAN_ID[1]
    vlan_id_3 = config.VLAN_ID[2]
    vlan_id_4 = config.VLAN_ID[3]
    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)
    vm = get_vms_from_cluster(cluster)[0]

    @classmethod
    def setup_class(cls):
        """
        Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
        the host. Then creating vnics (with all permutations of
        plugged & linked) and attaching them to the vm
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {cls.vlan_1: {'vlan_id': cls.vlan_id_1,
                                   'nic': cls.host.nics[1],
                                   'required': 'false'},
                      cls.vlan_2: {'vlan_id': cls.vlan_id_2,
                                   'nic': cls.host.nics[1],
                                   'required': 'false'},
                      cls.vlan_3: {'vlan_id': cls.vlan_id_3,
                                   'nic': cls.host.nics[1],
                                   'required': 'false'},
                      cls.vlan_4: {'vlan_id': cls.vlan_id_4,
                                   'nic': cls.host.nics[1],
                                   'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [('true', 'true'), ('true', 'false'),
                                ('false', 'true'), ('false', 'false')]
        for i in range(len(plug_link_param_list)):
            if not addNic(True, cls.vm, name='nic' + str(i + 2),
                          network=config.VLAN_NETWORKS[i],
                          plugged=plug_link_param_list[i][0],
                          linked=plug_link_param_list[i][1]):
                raise VMException("Cannot add nic%s to VM" % (i + 2))

    @istest
    def check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info("Checking Linked on nic2, nic4 is True")
        for nic_name in ('nic2', 'nic4'):
            self.assertTrue(getVmNicLinked(self.vm, nic=nic_name))
        logger.info("Checking Plugged on nic2, nic3 is True")
        for nic_name in ('nic2', 'nic3'):
            self.assertTrue(getVmNicPlugged(self.vm, nic=nic_name))
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(self.vm, nic=nic_name))
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(self.vm, nic=nic_name))

    @classmethod
    def teardown_class(cls):
        """
        Removing the nics and networks.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside mgmt network to "
                    "unplugged")
        for nic_name in ('nic2', 'nic3'):
            updateNic(True, cls.vm, nic_name, plugged=False)
        logger.info("Removing all the VNICs besides mgmt network")
        for i in range(4):
            if not removeNic(True, cls.vm, "nic" + str(i + 2)):
                raise NetworkException("Cannot remove nic from setup")
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan_1, cls.vlan_2,
                                            cls.vlan_3, cls.vlan_4])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase12(TestCase):
    """
    Checking Linking Nic (bond test):
    Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
    the host. Then creating vnics (with all permutations of plugged & linked)
    and attaching them to the vm, then:
    1. Checking that all the permutations of plugged & linked are correct
    Finally, Removing the nics and networks.
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_2 = config.VLAN_NETWORKS[1]
    vlan_3 = config.VLAN_NETWORKS[2]
    vlan_4 = config.VLAN_NETWORKS[3]
    vlan_id_1 = config.VLAN_ID[0]
    vlan_id_2 = config.VLAN_ID[1]
    vlan_id_3 = config.VLAN_ID[2]
    vlan_id_4 = config.VLAN_ID[3]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)
    vm = get_vms_from_cluster(cluster)[0]
    vm_nic = 'nic2'
    bond = config.BOND[0]

    __test__ = len(host.nics) > 3

    @classmethod
    def setup_class(cls):
        """
        Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
        the host. Then creating vnics (with all permutations of plugged
        & linked) and attaching them to the vm
        """
        logger.info("Create network and attach it to the host")
        local_dict = {None: {'nic': cls.bond,
                             'mode': 1,
                             'slaves': cls.host.nics[2:4]},
                      cls.vlan_1: {'nic': cls.bond,
                                   'vlan_id': cls.vlan_id_1,
                                   'required': 'false'},
                      cls.vlan_2: {'nic': cls.bond,
                                   'vlan_id': cls.vlan_id_2,
                                   'required': 'false'},
                      cls.vlan_3: {'nic': cls.bond,
                                   'vlan_id': cls.vlan_id_3,
                                   'required': 'false'},
                      cls.vlan_4: {'nic': cls.bond,
                                   'vlan_id': cls.vlan_id_4,
                                   'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=cls.host.nics[:2]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [('true', 'true'), ('true', 'false'),
                                ('false', 'true'), ('false', 'false')]
        for i in range(len(plug_link_param_list)):
            if not addNic(True, cls.vm, name='nic' + str(i + 2),
                          network=config.VLAN_NETWORKS[i],
                          plugged=plug_link_param_list[i][0],
                          linked=plug_link_param_list[i][1]):
                raise VMException("Cannot add nic%s to VM" % (i + 2))

    @istest
    def check_combination_plugged_linked_values(self):
        """
        Checking that all the permutations of plugged & linked are correct
        """
        logger.info("Checking Linked on nic2, nic4 is True")
        for nic_name in ('nic2', 'nic4'):
            self.assertTrue(getVmNicLinked(self.vm, nic=nic_name))
        logger.info("Checking Plugged on nic2, nic3 is True")
        for nic_name in ('nic2', 'nic3'):
            self.assertTrue(getVmNicPlugged(self.vm, nic=nic_name))
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(self.vm, nic=nic_name))
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(self.vm, nic=nic_name))

    @classmethod
    def teardown_class(cls):
        """
        Removing the nics and networks
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks besides mgmt network to "
                    "unplugged")
        for nic_name in ('nic2', 'nic3'):
            updateNic(True, cls.vm, nic_name, plugged=False)
        logger.info("Removing all the VNICs beside mgmt network")
        for i in range(4):
            if not removeNic(True, cls.vm, "nic" + str(i + 2)):
                raise NetworkException("Cannot remove nic from setup")
        logger.info("Starting the teardown_class")
        if not (removeNetFromSetup(host=cls.host.name,
                                   auto_nics=[cls.host.nics[0]],
                                   network=[cls.vlan_1, cls.vlan_2,
                                            cls.vlan_3, cls.vlan_4])):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class SanityCase13(TestCase):
    """
    Positive: Creates bridged network over bond on Host with custom name
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]

    vlan_id_1 = config.VLAN_ID[0]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    __test__ = len(host.nics) > 3

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks on DC/Cluster/Hosts over bond with custom name
        """

        local_dict = {None: {'nic': 'bond012345', 'mode': 1,
                             'slaves': cls.host.nics[2:4]},
                      cls.vlan_1: {'nic': 'bond012345',
                                   'mtu': 5000,
                                   'vlan_id': cls.vlan_id_1,
                                   'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=cls.dc,
                                        cluster=cls.cluster,
                                        host=cls.host.name,
                                        network_dict=local_dict,
                                        auto_nics=[cls.host.nics[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(14449, 275464)
    def bond_mode_change(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers for Jumbo bond ")
        logger.info("Checking logical layer of sw1 over bond")
        self.assertTrue(checkMTU(host=self.host.ip,
                                 user=self.host.user,
                                 password=self.host.password, mtu=5000,
                                 physical_layer=False,
                                 network=self.vlan_1,
                                 bond='bond012345',
                                 bridged=True))
        logger.info("Checking physical layer of sw1 over bond ")
        self.assertTrue(checkMTU(host=self.host.ip,
                                 user=self.host.user,
                                 password=self.host.password, mtu=5000,
                                 bond='bond012345',
                                 bond_nic1=self.host.nics[2],
                                 bond_nic2=self.host.nics[3],
                                 bridged=True))
        logger.info("Changing the bond mode to  mode4")
        rc, out = genSNNic(nic='bond012345', network=self.vlan_1,
                           slaves=self.host.nics[2:4], mode=4)

        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(positive=True, host=self.host.name,
                      nics=[out['host_nic']],
                      auto_nics=[self.host.nics[0]],
                      check_connectivity='true',
                      connectivity_timeout=60, force='false')
        logger.info("Checking layers after bond mode change")
        logger.info("Checking logical layer after bond mode change")
        self.assertTrue(checkMTU(host=self.host.ip,
                                 user=self.host.user,
                                 password=self.host.password, mtu=5000,
                                 physical_layer=False,
                                 network=self.vlan_1,
                                 bond='bond012345',
                                 bridged=True))
        logger.info("Checking physical layer after bond mode change")
        self.assertTrue(checkMTU(host=self.host.ip,
                                 user=self.host.user,
                                 password=self.host.password, mtu=5000,
                                 bond='bond012345',
                                 bond_nic1=self.host.nics[2],
                                 bond_nic2=self.host.nics[3], bridged=True))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=cls.host.name,
                                  auto_nics=[cls.host.nics[0]],
                                  network=[cls.vlan_1],
                                  data_center=cls.dc):
            raise NetworkException("Cannot create and attach network")


@attr(tier=0)
class SanityCase14(TestCase):
    """
    Negative: Bond with exceeded name length (more than 15 chars)
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]

    vlan_id_1 = config.VLAN_ID[0]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
            pass

    @istest
    @tcms(14449, 275471)
    def bond_max_length(self):
        """
        Create BOND: exceed allowed length (max 15 chars)
        """
        logger.info("Generating bond012345678901 object with 2 NIC")
        net_obj = []
        rc, out = genSNNic(nic='bond012345678901',
                           slaves=self.host.nics[2:4])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNRequest: bond012345678901")
        self.assertTrue(sendSNRequest(False, host=self.host.name,
                                      nics=net_obj,
                                      auto_nics=[self.host.nics[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


@attr(tier=0)
class SanityCase15(TestCase):
    """
    Negative:  Try to create bond with wrong prefix
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]

    vlan_id_1 = config.VLAN_ID[0]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(14449, 275471)
    def bond_prefix(self):
        """
        Create BOND: use wrong prefix (eg. NET1515)
        """
        logger.info("Generating NET1515 object with 2 NIC bond")
        net_obj = []
        rc, out = genSNNic(nic='NET1515',
                           slaves=self.host.nics[2:4])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNRequest: NET1515")
        self.assertTrue(sendSNRequest(False, host=self.host.name,
                                      nics=net_obj,
                                      auto_nics=[self.host.nics[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


@attr(tier=0)
class SanityCase16(TestCase):
    """
    Negative: Try to create bond with wrong suffix
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]

    vlan_id_1 = config.VLAN_ID[0]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(14449, 275471)
    def bond_suffix(self):
        """
        Create BOND: use wrong suffix (e.g. bond1!)
        """
        logger.info("Generating bond1! object with 2 NIC bond")
        net_obj = []
        rc, out = genSNNic(nic='bond1!',
                           slaves=self.host.nics[2:4])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNRequest: bond1!")
        self.assertTrue(sendSNRequest(False, host=self.host.name,
                                      nics=net_obj,
                                      auto_nics=[self.host.nics[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


@attr(tier=0)
class SanityCase17(TestCase):
    """
    Negative: Try to create bond with empty name
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]

    vlan_id_1 = config.VLAN_ID[0]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(14449, 275471)
    def bond_empty(self):
        """
        Create BOND: leave name field empty
        """
        logger.info("Generating bond object with 2 NIC bond and empty name")
        net_obj = []
        rc, out = genSNNic(nic='',
                           slaves=self.host.nics[2:4])
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])

        logger.info("sending SNRequest: empty bond name")
        self.assertTrue(sendSNRequest(False, host=self.host.name,
                                      nics=net_obj,
                                      auto_nics=[self.host.nics[0]],
                                      check_connectivity='true',
                                      connectivity_timeout=TIMEOUT,
                                      force='false'))

    @classmethod
    def teardown_class(cls):
        pass


@attr(tier=0)
class SanityCase18(TestCase):
    """
    Negative: Create more then 5 BONDS using dummy interfaces
    """
    host = config.NETWORK_HOSTS[0]
    vlan_1 = config.VLAN_NETWORKS[0]

    vlan_id_1 = config.VLAN_ID[0]

    cluster = getHostCluster(host.name)
    dc = getHostDC(host.name)

    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create dummy interface for BONDS
        """
        logger.info("Creating 20 dummy interfaces")
        if not createDummyInterface(host=cls.host.ip,
                                    username=cls.host.user,
                                    password=cls.host.password,
                                    num_dummy=20):
            logger.error("Faild to create dummy interfaces")

    @istest
    @tcms(14449, 275813)
    def dummy_bonds(self):
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

        logger.info("Wait for %s to be UP", self.host.name)
        if not waitForHostsStates(True, self.host.name, states='up',
                                  timeout=600):
            logger.error("%s is not in UP state", self.host.name)

        logger.info("sending SNRequest: 10 bonds on dummy interfaces")
        if not sendSNRequest(True, host=self.host.name,
                             nics=net_obj,
                             auto_nics=[self.host.nics[0]],
                             check_connectivity='true',
                             connectivity_timeout=TIMEOUT,
                             force='false'):
            logger.error("Failed to SNRequest: bond1")

    @classmethod
    def teardown_class(cls):
        """
        Delete all bonds and dummy interfaces
        """
        if not deleteDummyInterface(host=cls.host.ip,
                                    username=cls.host.user,
                                    password=cls.host.password):
            logger.error("Failed to delete dummy interfaces")

        logger.info("Wait for %s to be UP", cls.host.name)
        if not waitForHostsStates(True, cls.host.name, states='up',
                                  timeout=600):
            logger.error("%s is not in UP state", cls.host.name)

        if not waitForSPM(cls.dc, 600, 30):
            logger.error("No SPM in %s", cls.dc)
            return False

########################################################################

########################################################################
