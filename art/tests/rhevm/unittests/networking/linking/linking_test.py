#! /usr/bin/python

from nose.tools import istest
from unittest import TestCase
import logging
import config
from art.test_handler.tools import tcms
from art.rhevm_api.utils.test_utils import get_api

from art.test_handler.settings import opts

from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.exceptions import\
    VMException, NetworkException
from art.rhevm_api.tests_lib.high_level.networks import\
    removeNetwork
from art.rhevm_api.tests_lib.low_level.networks import\
    addNetwork, addNetworkToCluster
from art.rhevm_api.tests_lib.low_level.vms import\
    addNic, getVmNicLinked, getVmNicPlugged, removeNic,\
    updateNic, getVmNicNetwork, startVm, getVmNicPortMirroring,\
    waitForVmsStates, stopVm

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################
# If updateNic fails in one of the test, then use waitForFuncStatus function
# This func is supposed to solve async problem between vdsm and libvirt/qemu


class Linked_Case1_231692_236620_231710(TestCase):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 5 VNICs on VM with different params for plugged/linked
        '''
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
    def checkCombinationPluggedLinkedValues(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info("Checking Linked on nic2, nic4, nic6 is True")
        for nic_name in ('nic2', 'nic4', 'nic6'):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic2, nic3, nic6 is True")
        for nic_name in ('nic2', 'nic3', 'nic6'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside rhevm to unplugged")
        for nic_name in ('nic2', 'nic3', 'nic6'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't unplug NICs")
        logger.info("Removing all the VNICs beside rhevm")
        for i in range(5):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")


class Linked_Case2_231696(TestCase):
    """
    Add a new network to VM with default plugged and linked states
    Checked that plugged and linked are True by default
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 1 VNIC on stopped VM with default plugged/linked states
        '''
        logger.info("Creating VNICs with default plugged/linked states")
        if not addNic(True, config.VM_NAME[1], name='nic2',
                      network=config.VLAN_NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 231696)
    def checkDefaultValues(self):
        """
        Check the default values for the Plugged/Linked options on VNIC
        """
        logger.info(" Checking linked state of nic2 to be True")
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic2'))
        logger.info("Checking Plugged state on nic2 to be True")
        self.assertTrue(getVmNicPlugged(config.VM_NAME[1], nic='nic2'))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating the network on nic2 to unplugged")
        if not updateNic(True, config.VM_NAME[1], 'nic2', plugged='false'):
            raise NetworkException("Cannot unplug nic2")
        logger.info("Removing the nic2 from the VM ")
        if not removeNic(True, config.VM_NAME[1], "nic2"):
            raise NetworkException("Cannot remove nic from setup")


class Linked_Case3_231698_231697(TestCase):
    """
    Create permutation for the Plugged/Linked VNIC
    Use e1000 and rtl8139 drivers
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 2 VNICs on stopped VM with different nic type for plugged/linked
        '''
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
    def checkCombinationPluggedLinkedValues(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info(" Checking linked state of nic3 is False" +
                    " and Updating its state to True")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic3'))
        if not updateNic(True, config.VM_NAME[1], "nic3", linked='true'):
            raise NetworkException("Couldn't update linked to True")

        logger.info(" Checking linked state on nic2 is True" +
                    " and Updating its state to False")
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic2'))
        if not updateNic(True, config.VM_NAME[1], "nic2", linked='false'):
            raise NetworkException("Couldn't update linked to false")

        logger.info("Checking that linked state on nics was correctly updated")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic2'))
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic3'))

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name, network=None):
                raise NetworkException("Couldn't update NICs with empty net")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[1], nic=nic_name))

        logger.info("Updating both NICs with its original networks " +
                    "and unplugging them")
        for i in range(2):
            if not updateNic(True, config.VM_NAME[1], "nic"+str(i+2),
                             network=config.VLAN_NETWORKS[i], plugged='false'):
                raise NetworkException("Couldn't update nic with original " +
                                       "network or couldn't unplug nic")

        logger.info("Testing that update nics with non-empty " +
                    "networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicNetwork(config.VM_NAME[1], nic=nic_name))

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[1], nic=nic_name))

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name, network=None):
                raise NetworkException("Couldn't update nic with empty net")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[1], nic=nic_name))

        logger.info("Updating both NICs with its original networks " +
                    "and plugging them")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name,
                             plugged='true'):
                raise NetworkException("Couldn't update nic with original" +
                                       "network or couldn't plug them")

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[1], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics besides with rhevm to unplugged")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[1], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't update nic to be unplugged")
        logger.info("Removing all the VNICs beside rhevm")
        for i in range(2):
            if not removeNic(True, config.VM_NAME[1], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")


class Linked_Case4_231691(TestCase):
    """
    Try to run VM with network attached to Cluster but not to the host
    The test should fail as VM can't run when there is no network on
    at least one host of the Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create network on DC/Cluster and add it to VM
        '''
        logger.info("Creating network on DC, Cluster")
        if not addNetwork(True, name=config.NETWORKS[0],
                          data_center=config.DC_NAME):
            raise NetworkException("Cannot add network to DC")
        if not addNetworkToCluster(True, network=config.NETWORKS[0],
                                   cluster=config.CLUSTER_NAME,
                                   required='false'):
            raise NetworkException("Cannot add network to Cluster")
        logger.info("Adding network to VM")
        if not addNic(True, config.VM_NAME[1], name='nic6',
                      network=config.NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 231691)
    def checkStartVm(self):
        """
        Try to start VM when there is no network on the host
        """
        logger.info("Try to start VM with network that is not present" +
                    "on the host in the Cluster")
        self.assertTrue(startVm(False, config.VM_NAME[1]))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics beside with rhevm to unplugged")
        if not updateNic(True, config.VM_NAME[1], "nic6", plugged='false'):
            raise NetworkException("Couldn't update nics to be unplugged")
        if not removeNic(True, config.VM_NAME[1], "nic6"):
            raise NetworkException("Cannot remove nic from setup")
        if not (removeNetwork(True, network=config.NETWORKS[0],
                              data_center=config.DC_NAME)):
            raise NetworkException("Cannot remove network from DC")


class Linked_Case5_239344(TestCase):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 1 plugged/linked VNIC with port mirroring enabled
        on running VM
        '''
        logger.info("Creating plugged/linked VNIC with port mirroring on sw1")
        if not addNic(True, vm=config.VM_NAME[0], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      port_mirroring=config.VLAN_NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 239344)
    def checkPortMirroringNetwork(self):
        """
        Check scenarios for port mirroring network
        """
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))
        logger.info("Try to switch link down ")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  linked='false'))
        logger.info("Try to switch port mirroring off")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  port_mirroring=None))
        logger.info("Unplug VNIC")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='false'))
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))
        logger.info("Plugging VNIC back")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='true'))
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating the nics beside with rhevm to unplugged")
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
            raise NetworkException("Couldn't update nics to be unplugged")
        logger.info("Removing all the VNICs beside rhevm")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")


class Linked_Case6_239348(TestCase):
    """
    Create VNICs with linked/unlinked states on running VM.
    Change network parameters for both VNICs:
    Change nic names, link/plugged states
    Assign and unassign empty network to the NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 2 VNICs on running VM with different linked states for VNICs
        '''
        logger.info("Creating VNICs with different link states on running VM")
        link_param_list = ['true', 'false']
        for i in range(len(link_param_list)):
            if not addNic(True, config.VM_NAME[0], name='nic'+str(i+2),
                          network=config.VLAN_NETWORKS[0],
                          plugged='true', linked=link_param_list[i]):
                raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 239348)
    def changeNetParamValues(self):
        """
        Check network parameters changes for VNICS
        Change NIC names, update linked/plugged states
        Remove and return network from the VNIC
        """
        link_param_list = ['false', 'true']
        logger.info("Checking linked state of nic2/nic3 to be True/False")
        self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic='nic2'))
        self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic='nic3'))
        logger.info("Changing the NICs names and Updating opposite link state")
        for i in range(2):
            if not updateNic(True, config.VM_NAME[0], "nic"+str(i+2),
                             name='vnic'+str(i+2)):
                logger.error("Couldn't update the NICs name")
        for i in range(2):
            sample = TimeoutingSampler(timeout=60, sleep=1,
                                       func=updateNic, positive=True,
                                       vm=config.VM_NAME[0],
                                       nic="vnic"+str(i+2),
                                       network=config.VLAN_NETWORKS[0],
                                       linked=link_param_list[i])
            if not sample.waitForFuncStatus(result=True):
                raise NetworkException("Couldn't update correct linked state")

        logger.info(" Checking linked state on vnic2/vnic3 to be False/True")
        self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic='vnic3'))
        self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic='vnic2'))

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('vnic3', 'vnic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name, network=None):
                logger.error("Couldn't update NIC with empty network")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('vnic3', 'vnic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[0], nic=nic_name))
        logger.info("Updating both NICs with its original networks " +
                    "and unplugging them")
        if not (updateNic(True, config.VM_NAME[0], "vnic3",
                          network=config.VLAN_NETWORKS[1], plugged='false') and
                updateNic(True, config.VM_NAME[0], "vnic2",
                          network=config.VLAN_NETWORKS[0], plugged='false')):
            logger.error("Couldn't update NICs with original network" +
                         "and couldn't unplug them")

        logger.info("Testing that update nics with non-empty " +
                    "networks succeeded")
        for nic_name in ('vnic3', 'vnic2'):
            self.assertTrue(getVmNicNetwork(config.VM_NAME[0], nic=nic_name))

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('vnic3', 'vnic2'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

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
            self.assertFalse(getVmNicNetwork(config.VM_NAME[0], nic=nic_name))

        logger.info("Updating both NICs to be plugged")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='true'):
                raise NetworkException("Couldn't update NIC to be plugged")

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside rhevm to unplugged")
        for nic_name in ('nic3', 'nic2'):
            if not updateNic(True, config.VM_NAME[0], nic_name,
                             plugged='false'):
                raise NetworkException("Couldn't unplugg nic2/nic3 networks ")
        logger.info("Removing all the VNICs beside rhevm")
        for index in range(2):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(index+2)):
                raise NetworkException("Cannot remove nic from setup")


class Linked_Case7_239346(TestCase):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 1 unplugged/linked VNIC with port mirroring enabled
        on running VM
        '''
        logger.info("Creating unplugged/linked VNIC with port mirroring")
        if not addNic(True, vm=config.VM_NAME[0], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      port_mirroring=config.VLAN_NETWORKS[0],
                      plugged='false'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 239346)
    def checkPortMirroringNetwork(self):
        """
        Check scenarios for port mirroring network
        """
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))

        logger.info("Try to update  NIC with empty network")
        self.assertTrue(updateNic(False, config.VM_NAME[0], 'nic2',
                                  network=None,
                                  port_mirroring=config.VLAN_NETWORKS[0]))
        logger.info("Changing the NIC type parameter")
        if not updateNic(True, config.VM_NAME[0], "nic2",
                         interface=config.NIC_TYPE_E1000, plugged='false'):
            raise NetworkException("Couldn't change the NIC type parameter")

        logger.info("Switch port mirroring off")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  port_mirroring=None))
        logger.info("Check port mirroring is disabled")
        self.assertTrue(getVmNicPortMirroring(False, config.VM_NAME[0],
                                              'nic2'))
        logger.info("Switch port mirroring on")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  network=config.VLAN_NETWORKS[0],
                                  port_mirroring=config.VLAN_NETWORKS[0]))

        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))
        logger.info("Plugging VNIC ")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged='true'))
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating the nics beside with rhevm to unplugged")
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
            raise NetworkException("Couldn't update nics to be unplugged")
        logger.info("Removing all the VNICs beside rhevm")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")


class Linked_Case8_239368(TestCase):
    """
    Changing several network parameters at once on non-running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 1 VNIC on non-running VM
        '''
        logger.info("Creating VNICs on non-running VM")
        if not addNic(True, config.VM_NAME[1], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      plugged='true', linked='true'):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8046, 239368)
    def changeNetParamValues(self):
        """
        Change plugged, network and name at once on VNIC of VM
        """
        logger.info("Changing nic2 plugged, network and name params")

        if not updateNic(True, config.VM_NAME[1], "nic2", name='vnic2',
                         network=config.VLAN_NETWORKS[1], plugged='false'):
            raise NetworkException("Couldn't update nic with  " +
                                   "plugged, network and name params")
        logger.info(" Checking plugged state on nic2 to be False")
        self.assertFalse(getVmNicPlugged(config.VM_NAME[1], nic='vnic2'))
        print "Add here check for network name"
        logger.info("Changing nic2 linked, network and name params")
        if not updateNic(True, config.VM_NAME[1], "vnic2", name='nic2',
                         network=config.VLAN_NETWORKS[0], linked='false'):
            raise NetworkException("Couldn't update nic with " +
                                   "linked, network and name params")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic2'))

        if not startVm(True, vm=config.VM_NAME[1]):
            raise VMException("Can't start VM")
        if not waitForVmsStates(True, names=config.VM_NAME[1], timeout=120,
                                states='up'):
            raise VMException("VM status is not up in the predefined timeout")
        logger.info("Changing linked and plugged to True ")
        logger.info("Changing network and turning on port mirroring")
        if not updateNic(True, config.VM_NAME[1], "nic2",
                         network=config.VLAN_NETWORKS[1], linked='true',
                         plugged='true',
                         port_mirroring=config.VLAN_NETWORKS[1]):
            raise NetworkException("Cannot change net and turn pm on")
        logger.info("Try updating nic with new mac and interface type:")
        logger.info("Test should fail updating")
        self.assertTrue(updateNic(False, config.VM_NAME[1], "nic2",
                                  interface=config.NIC_TYPE_RTL8139,
                                  mac_address='11:22:33:44:55:66'))
        if not updateNic(True, config.VM_NAME[1], "nic2",
                         network=config.VLAN_NETWORKS[1], linked='false',
                         plugged='false'):
            raise NetworkException("Cannot update linked state")
        logger.info("Updating nic with new mac and interface type")
        self.assertTrue(updateNic(True, config.VM_NAME[1], "nic2",
                                  interface=config.NIC_TYPE_RTL8139,
                                  mac_address='11:22:33:44:55:66'))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics beside with rhevm to unplugged")
        if not updateNic(True, config.VM_NAME[1], 'nic2', plugged='false'):
            logger.info("Updating nics to be unplugged")
        logger.info("Removing all the VNICs beside rhevm")
        if not removeNic(True, config.VM_NAME[1], "nic2"):
            raise NetworkException("Cannot remove nic from setup")
        if not stopVm(True, vm=config.VM_NAME[1]):
            raise VMException("Cannot stop VM")
