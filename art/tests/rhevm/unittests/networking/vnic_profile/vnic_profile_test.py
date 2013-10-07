#! /usr/bin/python

from nose.tools import istest
from unittest import TestCase
import logging
import config

from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException, DataCenterException,\
    VMException
from art.test_handler.settings import opts
from art.test_handler.tools import tcms

from art.rhevm_api.tests_lib.low_level.datacenters import\
    waitForDataCenterState, addDataCenter, removeDataCenter
from art.rhevm_api.tests_lib.low_level.clusters import\
    addCluster, removeCluster
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, removeNetwork
from art.rhevm_api.tests_lib.low_level.networks import updateNetwork,\
    updateVnicProfile, getNetworkVnicProfiles, getVnicProfileObj,\
    addVnicProfile, removeVnicProfile, findVnicProfile, addNetwork
from art.rhevm_api.tests_lib.low_level.hosts import genSNNic,\
    sendSNRequest, deactivateHost, activateHost, updateHost
from art.unittest_lib.network import skipBOND
from art.rhevm_api.tests_lib.low_level.vms import addNic, updateNic, removeNic
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)

MGMT_NETWORK = "rhevm"


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################

class VNIC_Profile_Case1_289787(TestCase):
    """
    Verify that when creating the new DC  - the new VNIC profile
    is created with MGMT network name
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create new DC on the setup
        """
        logger.info("Add DC to setup")
        if not addDataCenter(True, name=config.DC_NAME2,
                             version=config.VERSION,
                             storage_type=config.STORAGE_TYPE):
            raise DataCenterException("Cannot create new DataCenter")

    @istest
    @tcms(10053, 289787)
    def check_mgmt_profile(self):
        """
        Check MGMT VNIC profile is created when creating the new DC
        """
        self.assertTrue(getVnicProfileObj(name=MGMT_NETWORK,
                                          network=MGMT_NETWORK,
                                          data_center=config.DC_NAME2))

    @classmethod
    def teardown_class(cls):
        """
        Remove DC from the setup.
        """
        logger.info("Remove DC from setup")
        if not removeDataCenter(True, datacenter=config.DC_NAME2):
            raise DataCenterException("Cannot remove DC from setup")


class VNIC_Profile_Case2_293514(TestCase):
    """
    Verify uniqueness of VNIC profile
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'},
                      config.NETWORKS[1]: {'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 293514)
    def create_new_profiles(self):
        """
        Check you can create a profile for sw2 with the same name as sw1
        Check you can't create profile with the same name for the same network
        """
        logger.info("Creating profile %s for network %s", config.NETWORKS[0],
                    config.NETWORKS[1])
        self.assertTrue(addVnicProfile(positive=True, name=config.NETWORKS[0],
                                       data_center=config.DC_NAME,
                                       network=config.NETWORKS[1]))
        logger.info("Creating the same profile for the same network as before."
                    " Expected result is Fail")
        self.assertTrue(addVnicProfile(positive=False, name=config.NETWORKS[0],
                                       data_center=config.DC_NAME,
                                       network=config.NETWORKS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from DC")
        for i in range(2):
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME):
                raise NetworkException("Couldn't remove network from DC")


class VNIC_Profile_Case3_289764(TestCase):
    """
    Verify that changing the VM network to non-VM makes all it''s VNIC
    profiles disappear
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        """

        local_dict = {config.NETWORKS[0]: {'required': 'false'}}
        logger.info("Creating network %s with default vnic profile %s",
                    config.NETWORKS[0], config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

        logger.info("Creating additional profile %s for network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not (addVnicProfile(positive=True, name=config.NETWORKS[1],
                               data_center=config.DC_NAME,
                               network=config.NETWORKS[0])):
            raise NetworkException("Couldn't create second VNIC profile")

    @istest
    @tcms(10053, 289764)
    def update_to_non_vm(self):
        """
        Update VM network to non-VM network
        Check that both VNIC profiles of the network were removed as a
        result of changing the state of the network to non-VM
        """
        logger.info("Updating network %s to be non-VM", config.NETWORKS[0])
        if not updateNetwork(True, config.NETWORKS[0], usages=''):
            raise NetworkException("Couldn't change network %s to be non-VM",
                                   config.NETWORKS[0])
        logger.info("Check no VNIC profile exist for non-VM network")
        if getNetworkVnicProfiles(config.NETWORKS[0],
                                  data_center=config.DC_NAME):
            raise NetworkException("VNIC profiles exist under non-VM network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME):
            raise NetworkException("Couldn't remove networks from DC")


class VNIC_Profile_Case4_289778(TestCase):
    """
    Verify that removing network from setup makes all it's all VNIC
    profiles disappear as well
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster with 2 profiles for the network
        1) the default one, 2) created for the network
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'}}
        logger.info("Creating network %s with default vnic profile %s",
                    config.NETWORKS[0], config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

        logger.info("Creating additional profile %s for network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not (addVnicProfile(positive=True, name=config.NETWORKS[1],
                               data_center=config.DC_NAME,
                               network=config.NETWORKS[0])):
            raise NetworkException("Couldn't create second VNIC profile")

    @istest
    @tcms(10053, 289778)
    def remove_network(self):
        """
        Remove VM network
        Check that both VNIC profiles of the network were removed as a
        result of network removal
        """
        logger.info("Checking VNIC profiles exist after creating network %s",
                    config.NETWORKS[0])
        for i in range(2):
            if not findVnicProfile(vnic_profile_name=config.NETWORKS[i]):
                logger.error("VNIC profile %s doesn't exist ",
                             config.NETWORKS[i])
        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME):
            raise NetworkException("Couldn't remove networks from DC")
        logger.info("Checking no VNIC profile exists for removed network %s",
                    config.NETWORKS[0])
        for i in range(2):
            if findVnicProfile(vnic_profile_name=config.NETWORKS[i]):
                logger.error("VNIC profile %s exists after network removal",
                             config.NETWORKS[i])

    @classmethod
    def teardown_class(cls):
        pass


class VNIC_Profile_Case5_293513(TestCase):
    """
    Verify that creating the non-VM network doesn't create default VNIC
    profile and doesn't allow you to create non-default VNIC profiles
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-VM network on DC/Cluster
        """

        local_dict = {config.NETWORKS[0]: {'required': 'false',
                                           'usages': ''}}
        logger.info("Creating network %s with default vnic profile %s",
                    config.NETWORKS[0], config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 293513)
    def check_non_vm(self):
        """
        Check no VNIC profile exists for non-VM network
        Check you can't create VNIC profile for non-VM network
        """
        logger.info("Check no VNIC profile exist for non-VM network")
        if getNetworkVnicProfiles(config.NETWORKS[0],
                                  data_center=config.DC_NAME):
            raise NetworkException("VNIC profiles exist under non-VM network")
        logger.info("Trying to create profile %s for non-VM network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not addVnicProfile(positive=False, name=config.NETWORKS[1],
                              data_center=config.DC_NAME,
                              network=config.NETWORKS[0]):
            raise NetworkException("Created VNIC profile for non_VM network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME):
            raise NetworkException("Couldn't remove network from DC")


class VNIC_Profile_Case6_293519(TestCase):
    """
    Check that default VNIC profile is created when a new network is added
    to setup . No VNIC profile is added when creating non-VM network and when
    creating new network with profile_required flag set to false
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 3 logical networks on DC/Cluster.
        1) VM, 2) with profile_required flag set to false, 3) non-VM
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'},
                      config.NETWORKS[1]: {'required': 'false',
                                           'profile_required': 'false'},
                      config.NETWORKS[2]: {'required': 'false',
                                           'usages': ''}}
        logger.info("Creating network %s with default vnic profile %s",
                    config.NETWORKS[0], config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 293519)
    def check_profile(self):
        """"
        1) Check that VNIC profile exists for VM network
        2) Check that VNIC profile doesn't exist for non-VM network'
        3) Check that VNIC profile doesn't exist for network with the flag
        profile_required set to false
        """
        logger.info("Check VNIC profile exists for VM network")
        if not getNetworkVnicProfiles(config.NETWORKS[0],
                                      data_center=config.DC_NAME):
            raise NetworkException("VNIC profiles doesn't 'exist for"
                                   " VM network")
        logger.info("Check no VNIC profile exist for non-VM network")
        if getNetworkVnicProfiles(config.NETWORKS[2],
                                  data_center=config.DC_NAME):
            raise NetworkException("VNIC profiles exist for non-VM network")
        logger.info("Check no VNIC profile exist for network with "
                    "flag profile_required set to false")
        if getNetworkVnicProfiles(config.NETWORKS[1],
                                  data_center=config.DC_NAME):
            raise NetworkException("VNIC profiles exist for profile_required"
                                   " flag set to false")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        for i in range(3):
            logger.info("Remove network %s from DC", config.NETWORKS[i])
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME):
                raise NetworkException("Couldn't remove network %s from DC",
                                       config.NETWORKS[i])


class VNIC_Profile_Case7_321137(TestCase):
    """
    Check that attach profile to VM when the network for that profile
    doesn't exist on host fails
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 logical networks on DC/Cluster.
        1) VM network
        2) with profile_required flag set to false
        3) non-VM
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'}}
        logger.info("Creating network %s with default vnic profile %s",
                    config.NETWORKS[0], config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 321137)
    def check_profile(self):
        """"
        1) Check that VNIC profile exists for VM network
        2) Check that you can't add VNIC profile to VM if its network is
           not attached to the host
        """
        logger.info("Check VNIC profile exists for VM network")
        if not getNetworkVnicProfiles(config.NETWORKS[0],
                                      data_center=config.DC_NAME):
            raise NetworkException("VNIC profiles doesn't 'exist for"
                                   " VM network")
        self.assertTrue(addNic(False, config.VM_NAME[0], name='nic2',
                               network=config.NETWORKS[0],
                               vnic_profile=config.NETWORKS[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME):
            raise NetworkException("Couldn't remove network %s from DC",
                                   config.NETWORKS[0])


class VNIC_Profile_Case8_300692(TestCase):
    """
    Verify different scenarios of changing VNIC profiles on
    the unplugged VNIC of the VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 logical vm networks on DC/Cluster with
           2 default VNIC profiles
        2) Add to the second network 2 additional VNIC profiles
        3) Put on the unplugged nic2 vnic profile sw1 of network sw1

        """
        local_dict = {config.NETWORKS[0]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[0],
                                           'nic': config.HOST_NICS[1]},
                      config.NETWORKS[1]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[1],
                                           'nic': config.HOST_NICS[1]}}
        logger.info("Creating networks with default vnic profile")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Creating additional profiles for network %s",
                    config.NETWORKS[1])

        if not (addVnicProfile(positive=True,
                               name='_'.join([config.NETWORKS[1], '1']),
                               data_center=config.DC_NAME,
                               network=config.NETWORKS[1])):
            raise NetworkException("Couldn't create %s VNIC profile" % name)
        if not (addVnicProfile(positive=True,
                               name='_'.join([config.NETWORKS[1], '2']),
                               data_center=config.DC_NAME,
                               network=config.NETWORKS[1],
                               port_mirroring=True)):
            raise NetworkException("Couldn't create %s VNIC profile" % name)
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0],
                      plugged='false'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(10053, 300692)
    def update_network(self):
        """
        1) Update VNIC profile on nic2 with profile from different network
        2) Update VNIC profile on nic2 with profile from the same network
        3) Update VNIC profile on nic2 with profile from the same network
        but with port mirroring enabled
        """
        logger.info("Changing VNIC to have VNIC profile from another network")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile=config.NETWORKS[1]))
        logger.info("Changing VNIC to have VNIC profile from the same network")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile='_'.join([config.NETWORKS[1],
                                                         '1'])))
        logger.info("Changing VNIC to have VNIC profile from the same network"
                    "but with port_mirroring enabled")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile='_'.join([config.NETWORKS[1],
                                                         '2'])))

        logger.info("Changing VNIC to have VNIC profile from another network"
                    "but from with port_mirroring enabled to disable one")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                        network=config.NETWORKS[0],
                        vnic_profile=config.NETWORKS[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")
        for i in range(2):
            logger.info("Remove network %s from DC", config.NETWORKS[i])
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME):
                raise NetworkException("Couldn't remove network %s from DC",
                                       config.NETWORKS[i])


class VNIC_Profile_Case9_293516(TestCase):
    """
    Try to edit network for VNIC profile
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 293514)
    def create_new_profiles(self):
        """
        Check you can create a profile for sw2 with the same name as sw1
        Check you can't create profile with the same name for the same network
        """
        logger.info("Creating profile %s for network %s", config.NETWORKS[0],
                    config.NETWORKS[1])
        self.assertTrue(addVnicProfile(positive=True, name=config.NETWORKS[0],
                                       data_center=config.DC_NAME,
                                       network=config.NETWORKS[1]))
        logger.info("Creating the same profile for the same network as before."
                    " Expected result is Fail")
        self.assertTrue(addVnicProfile(positive=False, name=config.NETWORKS[0],
                                       data_center=config.DC_NAME,
                                       network=config.NETWORKS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from DC")
        for i in range(2):
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME):
                raise NetworkException("Couldn't remove network from DC")


class VNIC_Profile_Case10_293517(TestCase):
    """
    Verify it's impossible to change VNIC profile without port mirroring to
    VNIC profile with port mirroring and vice versa on running VM
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 logical vm networks on DC/Cluster with
           2 default VNIC profiles
        2) Add to the second network additional VNIC profile with PM
        3) Put on the nic2 VNIC profile sw1 of network sw1 without PM
        4) Put on the nic3 VNIC profile sw2_1 of network sw2 with PM

        """
        local_dict = {config.NETWORKS[0]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[0],
                                           'nic': config.HOST_NICS[1]},
                      config.NETWORKS[1]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[1],
                                           'nic': config.HOST_NICS[1]}}
        logger.info("Creating networks with default vnic profile")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Creating additional profile with PM for network %s",
                    config.NETWORKS[1])

        if not (addVnicProfile(positive=True,
                               name='_'.join([config.NETWORKS[1], '1']),
                               data_center=config.DC_NAME,
                               network=config.NETWORKS[1],
                               port_mirroring=True)):
            raise NetworkException("Couldn't create %s VNIC profile" % name)
        for i in range(2):
            if not addNic(True, config.VM_NAME[0],
                          name=''.join(['nic', str(i+2)]),
                          network=config.NETWORKS[i]):
                raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(10053, 293517)
    def update_vnicProfile(self):
        """
        1) Try to update VNIC profile on nic2 to have port mirroring enabled
        2) Try to update VNIC profile on nic3 to have port mirroring disabled
        """
        import pdb
        pdb.set_trace()
        logger.info("Trying to change VNIC profile attached to VM on nic2 to "
                    "have port mirroring enabled")
        if updateVnicProfile(name=config.NETWORKS[0],
                             network=config.NETWORKS[0], port_mirroring=True):
            raise VMException("Was able to update PM on running VM")
        logger.info("Trying to change VNIC profile attached to VM on nic3 to "
                    "have port mirroring disabled")
        if updateVnicProfile(name='_'.join([config.NETWORKS[1], '1']),
                             network=config.NETWORKS[1], port_mirroring=False):
            raise VMException("Was able to update PM on running VM")

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        logger.info("Updating nic2 and nic3 to be unplugged")
        for nic_name in ('nic2', 'nic3'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't unplug NICs")
            if not removeNic(True, config.VM_NAME[0], nic_name):
                raise NetworkException("Cannot remove nic from setup")
        for i in range(2):
            logger.info("Remove network %s from DC", config.NETWORKS[i])
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME):
                raise NetworkException("Couldn't remove network %s from DC",
                                       config.NETWORKS[i])
