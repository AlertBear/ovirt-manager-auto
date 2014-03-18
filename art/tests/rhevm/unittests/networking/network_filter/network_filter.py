"""
Testing NetworkFilter feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import config
import logging
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level.vms import addNic, getVmMacAddress, \
    stopVm, startVm, removeNic, updateNic, hotUnplugNic, waitForVMState, \
    waitForVmsStates
from art.test_handler.tools import tcms
from art.rhevm_api.utils.test_utils import setNetworkFilterStatus
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.hosts import \
    checkNetworkFilteringDumpxml, checkNetworkFiltering, \
    checkNetworkFilteringEbtables
from art.rhevm_api.utils.test_utils import checkSpoofingFilterRuleByVer

logger = logging.getLogger(__name__)

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class NetworkFilterCase01_CheckFilterIsOn(TestCase):
    """
    Check that Network Filter is enabled by default
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        No need to run setup_class for this test
        """
        logger.info("No need to run setup_class for this test")

    @istest
    @tcms(6955, 233972)
    def checkFilterStatusEngine(self):
        """
        Check that Network Filter is enabled by default on engine
        """
        logger.info("Check that Network Filter is enabled on engine")
        if not checkSpoofingFilterRuleByVer(host=config.VDC,
                                            user=config.HOSTS_USER,
                                            passwd=config.HOSTS_PW):
            raise NetworkException("Network Filter is disabled on engine")

    @istest
    @tcms(6955, 198901)
    def checkFilterStatusVdsm(self):
        """
        Check that Network Filter is enabled by default on VDSM
        """
        logger.info("Check that Network Filter is enabled on VDSM")
        if not checkNetworkFiltering(positive=True,
                                     host=config.HOSTS[0],
                                     user=config.HOSTS_USER,
                                     passwd=config.HOSTS_PW):
            raise NetworkException("Network Filter is disabled on VDSM")

    @istest
    @tcms(6955, 198903)
    def checkFilterStatusDumpXml(self):
        """
        Check that Network Filter is enabled by default via dumpxml
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not checkNetworkFilteringDumpxml(positive=True,
                                            host=config.HOSTS[0],
                                            user=config.HOSTS_USER,
                                            passwd=config.HOSTS_PW,
                                            vm=config.VM_NAME[0],
                                            nics='1'):
            raise NetworkException("Network Filter is disabled via dumpxml")

    @classmethod
    def teardown_class(cls):
        """
        No need to run teardown for this test
        """
        logger.info("No need to run teardown for this test")

##############################################################################


class NetworkFilterCase02_CheckFilterIsOnForNewNic(TestCase):
    """
    Check that network filter is enabled for hot-plug  NIC to on VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Adding nic2 to VM
        """
        logger.info("Adding nic2 to VM")
        if not addNic(positive=True, vm=config.VM_NAME[0], name='nic2',
                      interface=config.NIC_TYPE_RTL8139,
                      network=config.MGMT_BRIDGE):
            raise NetworkException("Failed to add NIC to VM")

    @istest
    @tcms(6955, 198914)
    def checkNetworkFilterOnNic(self):
        """
        Check that the new NIC has network filter
        """
        logger.info("Check that Network Filter is enabled for nic2 via "
                    "dumpxml")
        if not checkNetworkFilteringDumpxml(positive=True,
                                            host=config.HOSTS[0],
                                            user=config.HOSTS_USER,
                                            passwd=config.HOSTS_PW,
                                            vm=config.VM_NAME[0],
                                            nics='2'):
            raise NetworkException("Network Filter is disabled for nic2 via "
                                   "dumpxml")

    @classmethod
    def teardown_class(cls):
        """
        Un-plug and remove nic2 from VM
        """
        logger.info("un-plug nic2")
        if not hotUnplugNic(positive=True, vm=config.VM_NAME[0], nic="nic2"):
            logger.error("Failed to remove nic2 from VM")

        logger.info("Removing nic2 from VM")
        if not removeNic(positive=True, vm=config.VM_NAME[0], nic="nic2"):
            raise NetworkException("Failed to remove nic2")

##############################################################################


class NetworkFilterCase03_CheckEbtables(TestCase):
    """
    Check that Network Filter is enabled via ebtables on running VM and
    disabled on stopped VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        No need to run setup_class for this test
        """
        logger.info("No need to run setup_class for this test")

    @istest
    @tcms(6955, 198920)
    def checkNetworkFilterViaEbtables(self):
        """
        Check that VM NIC has network filter via ebtables
        """
        vm_macs = getVmMacs(vm=config.VM_NAME[0], nics=["nic1"])
        logger.info("Check ebtables rules for running VM")
        if not checkNetworkFilteringEbtables(positive=True,
                                             host=config.HOSTS[0],
                                             user=config.VMS_LINUX_USER,
                                             passwd=config.VMS_LINUX_PW,
                                             nics='1',
                                             vm_macs=vm_macs):
            raise NetworkException("Network filter is not enabled via "
                                   "ebtables on the VM NICs ")

        logger.info("Stopping the VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("fail to stop the VM")

        logger.info("Check ebtables rules for stopped VM")
        if not checkNetworkFilteringEbtables(positive=False,
                                             host=config.HOSTS[0],
                                             user=config.VMS_LINUX_USER,
                                             passwd=config.VMS_LINUX_PW,
                                             nics='1',
                                             vm_macs=vm_macs):
            raise NetworkException("Network filter is enabled via ebtables on "
                                   "the VM NICs ")

    @classmethod
    def teardown_class(cls):
        """
        Start the VM
        """
        logger.info("Starting the VM and wait for status up")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("failed to start the VM")

        if not waitForVmsStates(positive=True, names=config.VM_NAME[0],
                                timeout=120):
            raise NetworkException("VM state is not up")

##############################################################################


class NetworkFilterCase04_CheckEbtablesHotplug(TestCase):
    """
    Check that Network Filter is disabled via ebtables on after VNIC hot-plug
    and still active after hot-unplug for remaining NICs
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        No need to run setup_class for this test
        """
        logger.info("No need to run setup_class for this test")

    @istest
    @tcms(6955, 198966)
    def checkNetworkFilterViaEbtables(self):
        """
        Check that VM NICs has network filter via ebtables
        """
        vm_nic1_mac = getVmMacs(vm=config.VM_NAME[0], nics=["nic1"])
        logger.info("Check ebtables rules for nic1")
        if not checkNetworkFilteringEbtables(positive=True,
                                             host=config.HOSTS[0],
                                             user=config.VMS_LINUX_USER,
                                             passwd=config.VMS_LINUX_PW,
                                             nics='1',
                                             vm_macs=vm_nic1_mac):
            raise NetworkException("Network filter is not enabled via "
                                   "ebtables for nic1 ")

        logger.info("Adding new NIC to VM")
        if not addNic(positive=True, vm=config.VM_NAME[0], name='nic2',
                      interface=config.NIC_TYPE_RTL8139,
                      network=config.MGMT_BRIDGE):
            raise NetworkException("Failed to add NIC to VM")

        vm_nic2_mac = getVmMacs(vm=config.VM_NAME[0], nics=["nic2"])
        logger.info("Check ebtables rules for nic2")
        if not checkNetworkFilteringEbtables(positive=True,
                                             host=config.HOSTS[0],
                                             user=config.VMS_LINUX_USER,
                                             passwd=config.VMS_LINUX_PW,
                                             nics='1',
                                             vm_macs=vm_nic2_mac):
            raise NetworkException("Network filter is not enabled via "
                                   "ebtables for nic2 ")

        logger.info("hot-unplug nic2 from the VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic2",
                         plugged="false"):
            raise NetworkException("Failed to update nic2 to un-plugged")

        if not removeNic(positive=True, vm=config.VM_NAME[0], nic="nic2"):
            raise NetworkException("Failed to remove nic2")

        vm_nic1_1_mac = getVmMacs(vm=config.VM_NAME[0], nics=["nic1"])
        logger.info("Check ebtables rules for nic1")
        if not checkNetworkFilteringEbtables(positive=True,
                                             host=config.HOSTS[0],
                                             user=config.VMS_LINUX_USER,
                                             passwd=config.VMS_LINUX_PW,
                                             nics='1',
                                             vm_macs=vm_nic1_1_mac):
            raise NetworkException("Network filter is not enabled via "
                                   "ebtables for nic1 ")

    @classmethod
    def teardown_class(cls):
        """
        No need to run teardown for this test
        """
        logger.info("No need to run teardown for this test")

##############################################################################


class NetworkFilterCase05_CheckFilterIsOn(TestCase):
    """
    Disabling network filter then check that VM run without network filter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Disabling network filter on engine and start the VM
        """
        logger.info("Stopping the VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("fail to stop the VM")

        logger.info("Disabling network filter on engine")
        if not setNetworkFilterStatus(enable=False, host=config.VDC,
                                      user=config.VDC_USER,
                                      passwd=config.VDC_PASSWORD):
            raise NetworkException("Failed to disable network filter")

        logger.info("Starting the VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("failed to start the VM")

    @istest
    @tcms(6955, 203261)
    def checkNetworkFilterOnNic(self):
        """
        Check that VM run without network filter.
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not checkNetworkFilteringDumpxml(positive=False,
                                            host=config.HOSTS[0],
                                            user=config.HOSTS_USER,
                                            passwd=config.HOSTS_PW,
                                            vm=config.VM_NAME[0],
                                            nics='1'):
            raise NetworkException("Network Filter is enabled via dumpxml")

        vm_nic1_mac = getVmMacs(vm=config.VM_NAME[0], nics=["nic1"])
        logger.info("Check ebtables rules for nic1")
        if not checkNetworkFilteringEbtables(positive=False,
                                             host=config.HOSTS[0],
                                             user=config.VMS_LINUX_USER,
                                             passwd=config.VMS_LINUX_PW,
                                             nics='1',
                                             vm_macs=vm_nic1_mac):
            raise NetworkException("Network filter is enabled via "
                                   "ebtables for nic1 ")

    @classmethod
    def teardown_class(cls):
        """
        Enabling network filter on engine
        """
        logger.info("Enabling network filter on engine")
        if not setNetworkFilterStatus(enable=True, host=config.VDC,
                                      user=config.VDC_USER,
                                      passwd=config.VDC_PASSWORD):
            raise NetworkException("Failed to enable network filter")

##############################################################################


def getVmMacs(vm, nics):
    """
    Description: Get MACs from VM
    **Author**: myakove
    **Parameters**:
       * *vm* - VM name.
       * *nics* - List of NICs to get the MACs for
    """
    vm_macs = []
    logger.info("Get MAC address for VM NICs")
    for nic in nics:
        vm_mac = getVmMacAddress(positive=True, vm=vm, nic=nic)
        vm_macs.append(vm_mac[1]['macAddress'])

    if len(vm_macs) != len(nics):
        logging.error("Fail to get MAC from VM")
        return False
    return vm_macs
