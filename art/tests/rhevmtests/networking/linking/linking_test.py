'''
Testing Linking/Plugging feature.
1 DC, 1 Cluster, 1 Hosts and 2 VMs will be created for testing.
Linking/Plugging will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for different states of VNIC on stopped/running VM.
'''

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from rhevmtests.networking import config
from art.test_handler.tools import tcms
from art.rhevm_api.utils.test_utils import get_api

from art.test_handler.settings import opts

from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.exceptions import\
    VMException, NetworkException
from art.rhevm_api.tests_lib.high_level.networks import\
    removeNetwork
from art.rhevm_api.tests_lib.low_level.networks import\
    addNetwork, addNetworkToCluster, addVnicProfile, removeVnicProfile
from art.rhevm_api.tests_lib.low_level.vms import\
    addNic, getVmNicLinked, getVmNicPlugged, removeNic,\
    updateNic, getVmNicNetwork, startVm, waitForVmsStates, stopVm

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################
# If updateNic fails in one of the test, then use waitForFuncStatus function
# This func is supposed to solve async problem between vdsm and libvirt/qemu


@attr(tier=1)
class LinkedCase1(TestCase):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 5 VNICs on VM with different params for plugged/linked
        """
        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [('true', 'true'), ('true', 'false'),
                                ('false', 'true'), ('false', 'false')]
        for i in range(len(plug_link_param_list)):
            if not addNic(True, config.VM_NAME[0], name='nic'+str(i+2),
                          network=config.VLAN_NETWORKS[i],
                          plugged=plug_link_param_list[i][0],
                          linked=plug_link_param_list[i][1]):
                raise VMException("Cannot add VNIC to VM")
        if not addNic(True, config.VM_NAME[0], name='nic6',
                      network=None,
                      plugged='true',
                      linked='true'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 231692)
    def check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info("Checking Linked on nic2, nic4, nic6 is True")
        for nic_name in ('nic2', 'nic4', 'nic6'):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name),
                            "NIC %s is not linked but should be" % nic_name)
        logger.info("Checking Plugged on nic2, nic3, nic6 is True")
        for nic_name in ('nic2', 'nic3', 'nic6'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name),
                            "NIC %s is not plugged but should be" % nic_name)
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name),
                             "NIC %s is linked but shouldn't be" % nic_name)
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name),
                             "NIC %s is plugged but shouldn't be" % nic_name)

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks besides mgmt network to "
                    "unplugged")
        for nic_name in ('nic2', 'nic3', 'nic6'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't unplug NICs")
        logger.info("Removing all the VNICs besides mgmt network")
        for i in range(5):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")


@attr(tier=1)
class LinkedCase2(TestCase):
    """
    Add a new network to VM with default plugged and linked states
    Checked that plugged and linked are True by default
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 VNIC on stopped VM with default plugged/linked states
        """
        logger.info("Creating VNICs with default plugged/linked states")
        if not addNic(True, config.VM_NAME[1], name='nic2',
                      network=config.VLAN_NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 231696)
    def check_default_values(self):
        """
        Check the default values for the Plugged/Linked options on VNIC
        """
        logger.info(" Checking linked state of nic2 to be True")
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic2'),
                        "NIC2 is not linked but should be")
        logger.info("Checking Plugged state on nic2 to be True")
        self.assertTrue(getVmNicPlugged(config.VM_NAME[1], nic='nic2'),
                        "NIC2 is not plugged but should be")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating the network on nic2 to unplugged")
        if not updateNic(True, config.VM_NAME[1], 'nic2', plugged='false'):
            raise NetworkException("Cannot unplug nic2")
        logger.info("Removing the nic2 from the VM ")
        if not removeNic(True, config.VM_NAME[1], "nic2"):
            raise NetworkException("Cannot remove nic from setup")


@attr(tier=1)
class LinkedCase3(TestCase):
    """
    Create permutation for the Plugged/Linked VNIC
    Use e1000 and rtl8139 drivers
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 VNICs on stopped VM with different nic type for plugged/linked
        """
        logger.info("Creating VNICs with different nic types for stopped VM")
        if not addNic(True, config.VM_NAME[1], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      interface=config.NIC_TYPE_RTL8139,
                      plugged='true', linked='true'):
            raise VMException("Cannot add VNIC to VM")
        if not addNic(True, config.VM_NAME[1], name='nic3',
                      interface=config.NIC_TYPE_E1000,
                      network=config.VLAN_NETWORKS[1],
                      plugged='true', linked='false'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 231697)
    def check_ombination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info(" Checking linked state of nic3 is False" +
                    " and Updating its state to True")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic3'),
                         "NIC3 is linked, but shouldn't be")
        if not updateNic(True, config.VM_NAME[1], "nic3", linked='true'):
            raise NetworkException("Couldn't update linked to True")

        logger.info(" Checking linked state on nic2 is True" +
                    " and Updating its state to False")
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic2'),
                        "NIC2 is not linked, but should be")
        if not updateNic(True, config.VM_NAME[1], "nic2", linked='false'):
            raise NetworkException("Couldn't update linked to false")

        logger.info("Checking that linked state on nics was correctly updated")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic2'),
                         "NIC2 is linked, but it shouldn't be")
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic3'),
                        "NIC3 is not linked, but it shold be")

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name, network=None):
                raise NetworkException("Couldn't update NICs with empty net")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[1], nic=nic_name),
                             "Update NIC %s with empty Net failed" % nic_name)

        logger.info("Updating both NICs with its original networks " +
                    "and unplugging them")
        for i in range(2):
            if not updateNic(True, config.VM_NAME[1], "nic%s" % (i + 2),
                             network=config.VLAN_NETWORKS[i],
                             vnic_profile=config.VLAN_NETWORKS[i],
                             plugged='false'):
                raise NetworkException("Couldn't update nic with original " +
                                       "network or couldn't unplug nic")

        logger.info("Testing that update nics with non-empty " +
                    "networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicNetwork(config.VM_NAME[1], nic=nic_name),
                            "Update %s with non-empty Net failed" % nic_name)

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[1], nic=nic_name),
                             "NIC %s is plugged but shouldn't" % nic_name)

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name, network=None):
                raise NetworkException("Couldn't update nic with empty net")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[1], nic=nic_name),
                             "Update %s with empty Net failed" % nic_name)

        logger.info("Updating both NICs with its original networks " +
                    "and plugging them")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name,
                             plugged='true'):
                raise NetworkException("Couldn't update nic with original" +
                                       "network or couldn't plug them")

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[1], nic=nic_name),
                            "NIC %s isn't plugged but should be" % nic_name)

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics besides mgmt network to unplugged")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't update nic to be unplugged")
        logger.info("Removing all the VNICs besides mgmt network")
        for i in range(2):
            if not removeNic(True, config.VM_NAME[1], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")


@attr(tier=1)
class LinkedCase4(TestCase):
    """
    Try to run VM with network attached to Cluster but not to the host
    The test should fail as VM can't run when there is no network on
    at least one host of the Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster and add it to VM
        """
        logger.info("Creating network on DC, Cluster")
        if not addNetwork(True, name=config.NETWORKS[0],
                          data_center=config.DC_NAME[0]):
            raise NetworkException("Cannot add network to DC")
        if not addNetworkToCluster(True, network=config.NETWORKS[0],
                                   cluster=config.CLUSTER_NAME[0],
                                   required='false'):
            raise NetworkException("Cannot add network to Cluster")
        logger.info("Adding network to VM")
        if not addNic(True, config.VM_NAME[1], name='nic6',
                      network=config.NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 231691)
    def check_start_vm(self):
        """
        Try to start VM when there is no network on the host
        """
        logger.info("Try to start VM with network that is not present " +
                    "on the host in the Cluster. NIC: nic6, Network: %s",
                    config.VLAN_NETWORKS[0])
        startVm(positive=None, vm=config.VM_NAME[1])
        query = "name=%s and status=down" % config.VM_NAME[1]
        self.assertTrue(VM_API.waitForQuery(query, timeout=60, sleep=1),
                        "%s is up, should be down" % config.VM_NAME[1])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics besides mgmt network to unplugged")
        if not updateNic(True, config.VM_NAME[1], "nic6", plugged='false'):
            raise NetworkException("Couldn't update nics to be unplugged")
        if not removeNic(True, config.VM_NAME[1], "nic6"):
            raise NetworkException("Cannot remove nic from setup")
        if not (removeNetwork(True, network=config.NETWORKS[0],
                              data_center=config.DC_NAME[0])):
            raise NetworkException("Cannot remove network from DC")


@attr(tier=1)
class LinkedCase5(TestCase):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 plugged/linked VNIC with port mirroring enabled
        on running VM
        """
        if not addVnicProfile(positive=True, name=config.VNIC_PROFILE[0],
                              cluster=config.CLUSTER_NAME[0],
                              network=config.VLAN_NETWORKS[0],
                              port_mirroring=True):
            logger.error("Failed to add %s profile with %s network to %s",
                         config.VNIC_PROFILE[0], config.VLAN_NETWORKS[0],
                         config.CLUSTER_NAME[0])

        logger.info("Creating plugged/linked VNIC with port mirroring on sw1")
        if not addNic(True, vm=config.VM_NAME[0], name='nic2',
                      vnic_profile=config.VNIC_PROFILE[0],
                      network=config.VLAN_NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 239344)
    def check_port_mirroring_network(self):
        """
        Check scenarios for port mirroring network
        """
        logger.info("Try to switch link down ")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  linked='false'), "Unlink NIC2 failed")
        logger.info("Unplug VNIC")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='false'), "Unplug NIC2 failed")
        logger.info("Plugging VNIC back")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='true'), "Plug NIC2 failed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating the nics besides mgmt network to unplugged")
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
            raise NetworkException("Couldn't update nics to be unplugged")
        logger.info("Removing all the VNICs besides mgmt network")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")
        logger.info("Removing vnic profile")
        if not removeVnicProfile(positive=True,
                                 vnic_profile_name=config.VNIC_PROFILE[0],
                                 network=config.VLAN_NETWORKS[0]):
            logger.error("Failed to remove %s profile", config.VNIC_PROFILE[0])


@attr(tier=1)
class LinkedCase6(TestCase):
    """
    Create VNICs with linked/unlinked states on running VM.
    Change network parameters for both VNICs:
    Change nic names, link/plugged states
    Assign and unassign empty network to the NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 VNICs on running VM with different linked states for VNICs
        """
        logger.info("Creating VNICs with different link states on running VM")
        link_param_list = ['true', 'false']
        for i in range(len(link_param_list)):
            if not addNic(True, config.VM_NAME[0], name='nic'+str(i+2),
                          network=config.VLAN_NETWORKS[0],
                          plugged='true', linked=link_param_list[i]):
                raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 239348)
    def change_net_param_values(self):
        """
        Check network parameters changes for VNICS
        Change NIC names, update linked/plugged states
        Remove and return network from the VNIC
        """
        link_param_list = ['false', 'true']
        logger.info("Checking linked state of nic2/nic3 to be True/False")
        self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic='nic2'),
                        "NIC2  isn't linked but should be")
        self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic='nic3'),
                         "NIC3 is linked but shouldn't be")
        logger.info("Changing the NICs names and Updating opposite link state")
        for i in range(2):
            if not updateNic(True, config.VM_NAME[0], "nic%s" % (i + 2),
                             name="vnic%s" % (i + 2)):
                logger.error("Couldn't update the NICs name")
        for i in range(2):
            sample = TimeoutingSampler(timeout=60, sleep=1,
                                       func=updateNic, positive=True,
                                       vm=config.VM_NAME[0],
                                       nic="vnic%s" % (i + 2),
                                       network=config.VLAN_NETWORKS[0],
                                       vnic_profile=config.VLAN_NETWORKS[0],
                                       linked=link_param_list[i])
            if not sample.waitForFuncStatus(result=True):
                raise NetworkException("Couldn't update correct linked state")

        logger.info(" Checking linked state on vnic2/vnic3 to be False/True")
        self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic='vnic3'),
                        "VNIC3 isn't linked but should be")
        self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic='vnic2'),
                         "VNIC2 is linked but shouldn't be")

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('vnic3', 'vnic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name, network=None):
                logger.error("Couldn't update NIC with empty network")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('vnic3', 'vnic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[0], nic=nic_name),
                             "Update %s with empty Net failed" % nic_name)
        logger.info("Updating both NICs with its original networks " +
                    "and unplugging them")
        if not (updateNic(True, config.VM_NAME[0], "vnic3",
                          network=config.VLAN_NETWORKS[1],
                          vnic_profile=config.VLAN_NETWORKS[1],
                          plugged='false') and
                updateNic(True, config.VM_NAME[0], "vnic2",
                          network=config.VLAN_NETWORKS[0],
                          vnic_profile=config.VLAN_NETWORKS[0],
                          plugged='false')):
            logger.error("Couldn't update NICs with original network" +
                         "and couldn't unplug them")

        logger.info("Testing that update nics with non-empty " +
                    "networks succeeded")
        for nic_name in ('vnic3', 'vnic2'):
            self.assertTrue(getVmNicNetwork(config.VM_NAME[0], nic=nic_name),
                            "Update %s with non-empty Net failed" % nic_name)

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('vnic3', 'vnic2'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name),
                             "%s is plugged, but shouldn't be" % nic_name)

        logger.info(" Changing the NICs names to the original ones")
        if not (updateNic(True, config.VM_NAME[0], "vnic3", name='nic3') and
                updateNic(True, config.VM_NAME[0], "vnic2", name='nic2')):
            raise NetworkException("Couldn't update NICs with original names")

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name, network=None):
                raise NetworkException("Couldn't update NICs to empty nets")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[0], nic=nic_name),
                             "Update %s with empty Net failed" % nic_name)

        logger.info("Updating both NICs to be plugged")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='true'):
                raise NetworkException("Couldn't update NIC to be plugged")

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name),
                            "%s is not plugged, but should be" % nic_name)

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks besides mgmt network to "
                    "unplugged")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't unplugg nic2/nic3 networks ")
        logger.info("Removing all the VNICs besides mgmt network")
        for index in range(2):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(index+2)):
                raise NetworkException("Cannot remove nic from setup")


@attr(tier=1)
class LinkedCase7(TestCase):
    """
    Changing several network parameters at once on non-running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 VNIC on non-running VM
        """
        logger.info("Creating VNICs on non-running VM")
        if not addNic(True, config.VM_NAME[1], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      plugged='true', linked='true'):
            raise VMException("Cannot add VNIC to VM")

        if not addVnicProfile(positive=True, name=config.VNIC_PROFILE[0],
                              cluster=config.CLUSTER_NAME[0],
                              network=config.VLAN_NETWORKS[1],
                              port_mirroring=True):
            raise NetworkException("Failed to add %s profile with %s network"
                                   "to %s" % (config.VNIC_PROFILE[0],
                                              config.VLAN_NETWORKS[1],
                                              config.CLUSTER_NAME[0]))

    @istest
    @tcms(8046, 239368)
    def change_net_param_values(self):
        """
        Change plugged, network and name at once on VNIC of VM
        """
        logger.info("Changing nic2 plugged, network and name params")

        if not updateNic(True, config.VM_NAME[1], "nic2", name='vnic2',
                         network=config.VLAN_NETWORKS[1],
                         vnic_profile=config.VLAN_NETWORKS[1],
                         plugged='false'):
            raise NetworkException("Couldn't update nic with plugged, network "
                                   "and name params")
        logger.info("Checking plugged state on nic2 to be False")
        self.assertFalse(getVmNicPlugged(config.VM_NAME[1], nic='vnic2'),
                         "VNIC2 is plugged, but shouldn't be")
        print "Add here check for network name"
        logger.info("Changing nic2 linked, network and name params")
        if not updateNic(True, config.VM_NAME[1], "vnic2", name='nic2',
                         network=config.VLAN_NETWORKS[0],
                         vnic_profile=config.VLAN_NETWORKS[0],
                         linked='false'):
            raise NetworkException("Couldn't update nic with linked, network "
                                   "and name params")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic2'),
                         "NIC2 is linked, but shouldn't be")

        if not startVm(True, vm=config.VM_NAME[1]):
            raise VMException("Can't start VM")
        if not waitForVmsStates(True, names=config.VM_NAME[1], timeout=120,
                                states='up'):
            raise VMException("VM status is not up in the predefined timeout")
        logger.info("Changing linked and plugged to True ")
        logger.info("Changing network and turning on port mirroring")
        if not updateNic(True, config.VM_NAME[1], "nic2",
                         linked='true', plugged='true',
                         network=config.VLAN_NETWORKS[1],
                         vnic_profile=config.VNIC_PROFILE[0]):
            raise NetworkException("Cannot change net and turn pm on")
        logger.info("Try updating nic with new mac and interface type:")
        logger.info("Test should fail updating")
        self.assertTrue(updateNic(False, config.VM_NAME[1], "nic2",
                                  interface=config.NIC_TYPE_RTL8139,
                                  mac_address='11:22:33:44:55:66'),
                        "Updating NIC with new MAC and int type succeded")
        if not updateNic(True, config.VM_NAME[1], "nic2",
                         network=config.VLAN_NETWORKS[1],
                         vnic_profile=config.VLAN_NETWORKS[1],
                         linked='false', plugged='false'):
            raise NetworkException("Cannot update linked state")
        logger.info("Updating nic with new mac and interface type")
        self.assertTrue(updateNic(True, config.VM_NAME[1], "nic2",
                                  interface=config.NIC_TYPE_RTL8139,
                                  mac_address='00:22:33:44:55:66'),
                        "Updating NIC2 with new MAC and int type failed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics besides mgmt network to unplugged")

        if not updateNic(True, config.VM_NAME[1], 'nic2', plugged='false'):
            logger.info("Updating nics to be unplugged")
        logger.info("Removing all the VNICs besides mgmt network")

        if not removeNic(True, config.VM_NAME[1], "nic2"):
            raise NetworkException("Cannot remove nic from setup")

        if not removeVnicProfile(positive=True,
                                 vnic_profile_name=config.VNIC_PROFILE[0],
                                 network=config.VLAN_NETWORKS[1]):
            raise NetworkException("Cannot remove VNIC profile.")

        if not stopVm(True, vm=config.VM_NAME[1]):
            raise VMException("Cannot stop VM")
