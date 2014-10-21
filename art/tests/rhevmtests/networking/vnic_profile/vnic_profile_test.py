#! /usr/bin/python

import logging
from rhevmtests.networking import config
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase


from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import(
    NetworkException, DataCenterException, VMException
)
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level.datacenters import(
    addDataCenter, removeDataCenter
)
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup, removeNetwork
)
from art.rhevm_api.tests_lib.low_level.networks import(
    updateNetwork, updateVnicProfile, getNetworkVnicProfiles,
    getVnicProfileObj, addVnicProfile, removeVnicProfile, findVnicProfile,
    getVnicProfileAttr
)
from art.rhevm_api.tests_lib.low_level.vms import(
    addNic, updateNic, removeNic, createVm, checkVmNicProfile, removeVm
)
from art.rhevm_api.tests_lib.low_level.templates import(
    addTemplateNic, removeTemplateNic
)

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
logger = logging.getLogger(__name__)


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################

@attr(tier=1)
class VNICProfileCase01(TestCase):
    """
    Verify that when creating the new DC  - the new VNIC profile
    is created with MGMT network name
    """
    __test__ = True
    dc_name2 = "new_DC_35_case01"

    @classmethod
    def setup_class(cls):
        """
        Create new DC on the setup
        """
        logger.info("Add DC to setup")
        if not addDataCenter(True, name=cls.dc_name2,
                             version=config.COMP_VERSION,
                             storage_type=config.STORAGE_TYPE):
            raise DataCenterException("Cannot create new DataCenter")

    @istest
    @tcms(10053, 289787)
    def check_mgmt_profile(self):
        """
        Check MGMT VNIC profile is created when creating the new DC
        """
        self.assertTrue(getVnicProfileObj(name=config.MGMT_BRIDGE,
                                          network=config.MGMT_BRIDGE,
                                          data_center=self.dc_name2))

    @classmethod
    def teardown_class(cls):
        """
        Remove DC from the setup.
        """
        logger.info("Remove DC from setup")
        if not removeDataCenter(True, datacenter=cls.dc_name2):
            raise DataCenterException("Cannot remove DC from setup")


@attr(tier=1)
class VNICProfileCase02(TestCase):
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

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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
                                       data_center=config.DC_NAME[0],
                                       network=config.NETWORKS[1]))
        logger.info("Creating the same profile for the same network as before."
                    " Expected result is Fail")
        self.assertTrue(addVnicProfile(positive=False, name=config.NETWORKS[0],
                                       data_center=config.DC_NAME[0],
                                       network=config.NETWORKS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from DC")
        for i in range(2):
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME[0]):
                raise NetworkException("Couldn't remove network from DC")


@attr(tier=1)
class VNICProfileCase03(TestCase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

        logger.info("Creating additional profile %s for network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not (addVnicProfile(positive=True, name=config.NETWORKS[1],
                               data_center=config.DC_NAME[0],
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
                                  data_center=config.DC_NAME[0]):
            raise NetworkException("VNIC profiles exist under non-VM network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Couldn't remove networks from DC")


@attr(tier=1)
class VNICProfileCase04(TestCase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

        logger.info("Creating additional profile %s for network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not (addVnicProfile(positive=True, name=config.NETWORKS[1],
                               data_center=config.DC_NAME[0],
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
                             data_center=config.DC_NAME[0]):
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


@attr(tier=1)
class VNICProfileCase05(TestCase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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
                                  data_center=config.DC_NAME[0]):
            raise NetworkException("VNIC profiles exist under non-VM network")
        logger.info("Trying to create profile %s for non-VM network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not addVnicProfile(positive=False, name=config.NETWORKS[1],
                              data_center=config.DC_NAME[0],
                              network=config.NETWORKS[0]):
            raise NetworkException("Created VNIC profile for non_VM network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Couldn't remove network from DC")


@attr(tier=1)
class VNICProfileCase06(TestCase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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
                                      data_center=config.DC_NAME[0]):
            raise NetworkException("VNIC profiles doesn't 'exist for"
                                   " VM network")
        logger.info("Check no VNIC profile exist for non-VM network")
        if getNetworkVnicProfiles(config.NETWORKS[2],
                                  data_center=config.DC_NAME[0]):
            raise NetworkException("VNIC profiles exist for non-VM network")
        logger.info("Check no VNIC profile exist for network with "
                    "flag profile_required set to false")
        if getNetworkVnicProfiles(config.NETWORKS[1],
                                  data_center=config.DC_NAME[0]):
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
                                 data_center=config.DC_NAME[0]):
                raise NetworkException("Couldn't remove network %s from DC",
                                       config.NETWORKS[i])


@attr(tier=1)
class VNICProfileCase07(TestCase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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
                                      data_center=config.DC_NAME[0]):
            raise NetworkException("VNIC profiles doesn't 'exist for"
                                   " VM network")
        logger.info("Try to add VNIC that doesn't exist on Host")
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
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Couldn't remove network %s from DC" %
                                   config.NETWORKS[0])


@attr(tier=1)
class VNICProfileCase08(TestCase):
    """
    Verify different scenarios of changing VNIC profiles on
    the unplugged VNIC of the running VM
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
                                           'nic': 1},
                      config.NETWORKS[1]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[1],
                                           'nic': 1}}
        logger.info("Creating networks with default vnic profile")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0, 1]):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Creating additional profiles for network %s",
                    config.NETWORKS[1])
        name_net1 = '_'.join([config.NETWORKS[1], '1'])
        name_net2 = '_'.join([config.NETWORKS[1], '2'])
        if not (addVnicProfile(positive=True,
                               name=name_net1,
                               data_center=config.DC_NAME[0],
                               network=config.NETWORKS[1])):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net1
            )
        if not (addVnicProfile(positive=True,
                               name=name_net2,
                               data_center=config.DC_NAME[0],
                               network=config.NETWORKS[1],
                               port_mirroring=True)):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net2
            )
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0],
                      plugged='false'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(10053, 300692)
    def update_network_unplugged_nic(self):
        """
        1) Update VNIC profile on nic2 with profile from different network
        2) Update VNIC profile on nic2 with profile from the same network
        3) Update VNIC profile on nic2 with profile from the same network
        but with port mirroring enabled
        4) Update VNIC profile on nic2 with profile having port mirroring
        enabled to different network with port mirroring disabled
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
            logger.info("Remove network %s from setup", config.NETWORKS[i])
            if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                         auto_nics=[0],
                                         network=[config.NETWORKS[i]]):
                raise NetworkException("Cannot remove network %s from setup"
                                       % config.NETWORKS[i])


@attr(tier=1)
class VNICProfileCase09(TestCase):
    """
    VNIC Profile on template
    """
    __test__ = True
    vm_name2 = "new_VM_case09"

    @classmethod
    def setup_class(cls):
        """
        Create logical network on DC/Cluster
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 289896)
    def create_new_profiles_template(self):
        """
        1) Check that you can create non-empty VNIC profile on Template
        2) Check that you can create empty VNIC profile on Template
        3) Create VM from the template with empty and non-empty profiles
        4) Make sure this VM has empty and non-empty profiles on it's NICs
        """

        logger.info("Creating new profile %s for network %s on template %s",
                    config.NETWORKS[0], config.NETWORKS[0],
                    config.TEMPLATE_NAME[0])
        self.assertTrue(addTemplateNic(positive=True,
                                       template=config.TEMPLATE_NAME[0],
                                       name='nic2',
                                       data_center=config.DC_NAME[0],
                                       network=config.NETWORKS[0]))
        logger.info("Creating the same profile for the same network as before."
                    " Expected result is Fail")
        self.assertTrue(addTemplateNic(positive=True,
                                       template=config.TEMPLATE_NAME[0],
                                       name='nic3',
                                       data_center=config.DC_NAME[0],
                                       network=None))

        if not createVm(positive=True, vmName=self.vm_name2,
                        vmDescription='',
                        cluster=config.CLUSTER_NAME[0],
                        template=config.TEMPLATE_NAME[0],
                        network=config.MGMT_BRIDGE):
            raise VMException("Couldn't create VM from template")

        if not checkVmNicProfile(vm=self.vm_name2,
                                 vnic_profile_name=config.NETWORKS[0],
                                 nic='nic2'):
            raise VMException("Couldn't get correct VNIC profile on VM ")
        if not checkVmNicProfile(vm=self.vm_name2,
                                 vnic_profile_name=None,
                                 nic='nic3'):
            raise VMException("Couldn't get empty VNIC profile on VM ")

    @istest
    @tcms(10053, 293518)
    def remove_new_profiles_template(self):
        """
        1) Remove VM created from the previous test
        2) Try to remove network when template is using it's VNIC profile.
           This test is the negative one
        3) Remove VNIC profile from the template
        4) Remove VNIC profile from the setup
        """
        logger.info("Remove created VM from setup")
        if not removeVm(positive=True, vm=self.vm_name2):
            raise VMException("Couldn't remove VM from setup")

        logger.info("Try to remove network from setup and fail doing so "
                    "as network resides on the template")
        if removeNetwork(positive=True, network=config.NETWORKS[0],
                         data_center=config.DC_NAME[0]):
            raise NetworkException("Could remove network from DC when "
                                   "template is using it")

        if not removeTemplateNic(True, template=config.TEMPLATE_NAME[0],
                                 nic='nic2'):
            raise NetworkException("Couldn't remove NIC from template")

        if not removeVnicProfile(positive=True,
                                 vnic_profile_name=config.NETWORKS[0],
                                 network=config.NETWORKS[0]):
            raise NetworkException("Couldn't remove VNIC profile")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove NIC from template")
        if not removeTemplateNic(positive=True,
                                 template=config.TEMPLATE_NAME[0],
                                 nic='nic3'):
            raise NetworkException("Couldn't remove NIC from template")

        logger.info("Remove network from setup")
        if not removeNetwork(positive=True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Couldn't remove network from DC")


@attr(tier=1)
class VNICProfileCase10(TestCase):
    """
    Verify it's impossible to change VNIC profile without port mirroring to
    VNIC profile with port mirroring and vice versa on running VM
    """
    __test__ = True

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
                                           'nic': 1},
                      config.NETWORKS[1]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[1],
                                           'nic': 1}}
        logger.info("Creating networks with default vnic profiles")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0, 1]):
            raise NetworkException("Cannot create and attach networks")
        logger.info("Change VNIC profile attached to VM on nic3 to "
                    "have port mirroring enabled")
        if not updateVnicProfile(name=config.NETWORKS[1],
                                 network=config.NETWORKS[1],
                                 port_mirroring=True):
            raise VMException("Couldn't to update profile to have PM enabled")

        for i in range(2):
            if not addNic(True, config.VM_NAME[0],
                          name=''.join(['nic', str(i+2)]),
                          network=config.NETWORKS[i]):
                raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(10053, 293517)
    def update_vnic_profile(self):
        """
        1) Try to update VNIC profile on nic2 to have port mirroring enabled
        2) Try to update VNIC profile on nic3 to have port mirroring disabled
        """

        logger.info("Trying to change VNIC profile attached to VM on nic2 to "
                    "have port mirroring enabled")
        if updateVnicProfile(name=config.NETWORKS[0],
                             network=config.NETWORKS[0], port_mirroring=True):
            raise VMException("Was able to update PM on running VM")
        logger.info("Trying to change VNIC profile attached to VM on nic3 to "
                    "have port mirroring disabled")
        if updateVnicProfile(name=config.NETWORKS[1],
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
            logger.info("Remove network %s from setup", config.NETWORKS[i])
            if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                         auto_nics=[0],
                                         network=[config.NETWORKS[i]]):
                raise NetworkException("Cannot remove network %s from setup"
                                       % config.NETWORKS[i])


@attr(tier=1)
class VNICProfileCase11(TestCase):
    """
    Verify different scenarios of changing VNIC profiles on
    plugged VNIC of the running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 logical vm networks on DC/Cluster with
           2 default VNIC profiles
        2) Add to the second network 2 additional VNIC profiles
        3) Plug nic2 vnic and attach to it profile sw1 of network sw1

        """
        local_dict = {config.NETWORKS[0]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[0],
                                           'nic': 1},
                      config.NETWORKS[1]: {'required': 'false',
                                           'vlan_id': config.VLAN_ID[1],
                                           'nic': 1}}
        logger.info("Creating networks with default vnic profile")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0, 1]):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Creating additional profiles for network %s",
                    config.NETWORKS[1])
        name_net1 = '_'.join([config.NETWORKS[1], '1'])
        name_net2 = '_'.join([config.NETWORKS[1], '2'])
        if not (addVnicProfile(positive=True,
                               name=name_net1,
                               data_center=config.DC_NAME[0],
                               network=config.NETWORKS[1])):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net1
            )
        if not (addVnicProfile(positive=True,
                               name=name_net2,
                               data_center=config.DC_NAME[0],
                               network=config.NETWORKS[1],
                               port_mirroring=True)):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net2
            )
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0],
                      plugged='true'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(10053, 289729)
    def update_network_plugged_nic(self):
        """
        1) Update VNIC profile on nic2 with profile from different network
        2) Update VNIC profile on nic2 with profile from the same network
        3) Try to update VNIC profile on nic2 with profile from the same
        network but with port mirroring enabled (negative case)
        4) Update VNIC profile on nic2 with empty profile
        5) Update VNIC profile on nic2 with profile having port mirroring
        enabled (first unplug and after the action plug nic2)
        6) Try to update VNIC profile on nic2 with profile from the same
        network but with port mirroring disabled (negative case)
        """
        logger.info("Changing VNIC to have VNIC profile from another network")
        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=updateNic, positive=True,
                                   vm=config.VM_NAME[0],
                                   nic="nic2",
                                   network=config.NETWORKS[1],
                                   vnic_profile=config.NETWORKS[1])
        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't change VNIC profile to profile "
                                   "with different network")
        logger.info("Changing VNIC to have VNIC profile from the same network")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile='_'.join([config.NETWORKS[1],
                                                         '1'])))
        logger.info("Try changing VNIC to have VNIC profile from the same "
                    "network but with port_mirroring enabled (negative case)")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile='_'.join([config.NETWORKS[1],
                                                         '2'])))
        logger.info("Changing VNIC to have empty VNIC profile ")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=None))
        logger.info("Updating nic2 to be unplugged to put there VNIC profile "
                    "with port mirroring enabled")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='false'))
        logger.info("Changing VNIC to have VNIC profile with "
                    "port_mirroring enabled ")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile='_'.join([config.NETWORKS[1],
                                                         '2'])))
        logger.info("Updating nic2 to be plugged to test the case of changing"
                    " VNIC profile with port mirroring to VNIC profile "
                    "without port mirroring")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='true'))

        logger.info("Try changing VNIC to have VNIC profile from the same "
                    "network but with port mirroring disabled (negative case)")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  network=config.NETWORKS[1],
                                  vnic_profile='_'.join([config.NETWORKS[1],
                                                         '1'])))

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
            raise NetworkException("Cannot unplug nic")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")
        for i in range(2):
            logger.info("Remove network %s from setup", config.NETWORKS[i])
            if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                         auto_nics=[0],
                                         network=[config.NETWORKS[i]]):
                raise NetworkException("Cannot remove network %s from setup"
                                       % config.NETWORKS[i])


@attr(tier=1)
class VNICProfileCase12(TestCase):
    """
    Verify uniqueness of VNIC profile
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm networks on DC/Cluster
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'},
                      config.NETWORKS[1]: {'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(10053, 293516)
    def create_new_profiles(self):
        """
        Negative case: Try to update network for existing profile
        """
        logger.info("Try updating profile %s with  another network %s  ",
                    config.NETWORKS[0], config.NETWORKS[1])
        if updateVnicProfile(name=config.NETWORKS[0],
                             network=config.NETWORKS[0],
                             cluster=config.CLUSTER_NAME[0],
                             new_network=config.NETWORKS[1]):
            logger.error("Could update VNIC profile with another network "
                         "while the update should fail")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from DC")
        for i in range(2):
            if not removeNetwork(positive=True, network=config.NETWORKS[i],
                                 data_center=config.DC_NAME[0]):
                raise NetworkException("Couldn't remove network %s from setup",
                                       config.NETWORKS[i])


@attr(tier=1)
class VNICProfileCase13(TestCase):
    """
    Verify hotplug, link/unlink works on the running VM
    Try to remove VNIC profile when VM is using it (negative case)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 1 logical vm networks on DC/Cluster/Host/VM with
        default VNIC profile
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false',
                                           'nic': 1}}
        logger.info("Creating network with default vnic profile")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach networks")

    @istest
    @tcms(10053, 289730)
    def hotplug_link_unlink(self):
        """
        1) Hotplug VNIC profile to the VM's nic2
        2) Unlink nic2
        3) Link nic2
        """

        logger.info("Hotplug %s profile to VM on nic2", config.NETWORKS[0])
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0],
                      plugged='true'):
            raise VMException("Cannot add VNIC to VM")

        logger.info("Changing VNIC to unlink")
        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=updateNic, positive=True,
                                   vm=config.VM_NAME[0],
                                   nic="nic2",
                                   linked='false')
        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't update correct linked state")

        logger.info("Changing VNIC to linked")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  linked='true'))

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
            raise NetworkException("Cannot unplug nic")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")

        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup"
                                   % config.NETWORKS[0])


@attr(tier=1)
class VNICProfileCase14(TestCase):
    """
    Try to remove VNIC profile when VM is using it (negative case)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 1 logical vm networks on DC/Cluster/Host/VM with
        default VNIC profile
        2) Add NIC2 to VM
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false',
                                           'nic': 1}}
        logger.info("Creating network with default vnic profile")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Hotplug %s profile to VM on nic2", config.NETWORKS[0])
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0],
                      plugged='true'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(10053, 289728)
    def remove_used_profile(self):
        """
        Try to remove VNIC profile while VM is using it (negative case)
        """
        logger.info("Try to remove %s profile when VM is using it",
                    config.NETWORKS[0])
        if not removeVnicProfile(positive=False,
                                 vnic_profile_name=config.NETWORKS[0],
                                 network=config.NETWORKS[0]):
            raise VMException("Could remove VNIC profile although VM is "
                              "using it")

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
            raise NetworkException("Cannot unplug nic")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")

        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup"
                                   % config.NETWORKS[0])


@attr(tier=1)
class VNICProfileCase15(TestCase):
    """
    Create new VNIC profile and make sure all its parameters exist in API
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        Create additional VNIC profile with Description, Port mirroring
        """
        local_dict = {config.NETWORKS[0]: {'required': 'false'}}
        logger.info("Creating network %s with default vnic profile %s",
                    config.NETWORKS[0], config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict,):
            raise NetworkException("Cannot create and attach network")

        logger.info("Creating additional profile %s for network %s",
                    config.NETWORKS[1], config.NETWORKS[0])
        if not (addVnicProfile(positive=True, name=config.NETWORKS[1],
                               data_center=config.DC_NAME[0],
                               network=config.NETWORKS[0],
                               port_mirroring=True,
                               description="vnic_p_desc")):
            raise NetworkException("Couldn't create second VNIC profile")

    @istest
    @tcms(10053, 289724)
    def check_attr(self):
        """
        Check VNIC profile created with parameters has these parameters
        """
        attr_dict = getVnicProfileAttr(name=config.NETWORKS[1],
                                       network=config.NETWORKS[0],
                                       attr_list=["description",
                                                  "port_mirroring",
                                                  "name"])
        if (attr_dict.get('description') != "vnic_p_desc" or
           attr_dict.get("port_mirroring") is not True or
           attr_dict.get("name") != config.NETWORKS[1]):
            logger.error("Attributes are not equal to what was set")
            return False

    @classmethod
    def teardown_class(cls):
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(host=config.VDS_HOSTS[0],
                                     auto_nics=[0],
                                     network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network %s from setup"
                                   % config.NETWORKS[0])
