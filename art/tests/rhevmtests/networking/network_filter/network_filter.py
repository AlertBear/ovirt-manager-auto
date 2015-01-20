"""
Testing NetworkFilter feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

from rhevmtests.networking import config
import logging
from art.unittest_lib import NetworkTest as TestCase, attr
from art.rhevm_api.tests_lib.low_level.vms import (
    addNic, getVmMacAddress, stopVm, startVm, removeNic, updateNic,
    hotUnplugNic,
)
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.rhevm_api.utils.test_utils import setNetworkFilterStatus
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.hosts import(
    checkNetworkFilteringDumpxml, checkNetworkFiltering,
    checkNetworkFilteringEbtables
)
from art.rhevm_api.utils.test_utils import checkSpoofingFilterRuleByVer

logger = logging.getLogger("Network_Filter_Cases")

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class TestNetworkFilterCase01(TestCase):
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

    @tcms(6955, 233972)
    def test_check_filter_status_engine(self):
        """
        Check that Network Filter is enabled by default on engine
        """
        logger.info("Check that Network Filter is enabled on engine")
        if not checkSpoofingFilterRuleByVer(
                host=config.VDC_HOST, user=config.VDC_ROOT_USER,
                passwd=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException("Network Filter is disabled on engine")

    @tcms(6955, 198901)
    def test_check_filter_status_vdsm(self):
        """
        Check that Network Filter is enabled by default on VDSM
        """
        logger.info("Check that Network Filter is enabled on VDSM")
        if not checkNetworkFiltering(
                positive=True, host=config.HOSTS_IP[0],
                user=config.HOSTS_USER, passwd=config.HOSTS_PW
        ):
            raise NetworkException("Network Filter is disabled on VDSM")

    @tcms(6955, 198903)
    def test_check_filter_status_dump_xml(self):
        """
        Check that Network Filter is enabled by default via dumpxml
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not checkNetworkFilteringDumpxml(
                positive=True, host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                passwd=config.HOSTS_PW, vm=config.VM_NAME[0], nics="1"
        ):
            raise NetworkException("Network Filter is disabled via dumpxml")

##############################################################################


@attr(tier=1)
class TestNetworkFilterCase02(TestCase):
    """
    Check that network filter is enabled for hot-plug  NIC to on VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Adding nic2 to VM
        """
        logger.info("Adding %s to VM", config.NIC_NAME[1])
        if not addNic(
                positive=True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
                interface=config.NIC_TYPE_RTL8139, network=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Failed to add NIC %s to VM" % config.NIC_NAME[1]
            )

    @tcms(6955, 198914)
    def test_check_network_filter_on_nic(self):
        """
        Check that the new NIC has network filter
        """
        logger.info(
            "Check that Network Filter is enabled for %s via dumpxml",
            config.NIC_NAME[1]
        )
        if not checkNetworkFilteringDumpxml(
                positive=True, host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                passwd=config.HOSTS_PW, vm=config.VM_NAME[0], nics="2"
        ):
            raise NetworkException(
                "Network Filter is disabled for %s via dumpxml" %
                config.NIC_NAME[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Un-plug and remove nic2 from VM
        """
        logger.info("un-plug %s", config.NIC_NAME[1])
        if not hotUnplugNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        ):
            logger.error("Failed to unplug %s from VM", config.NIC_NAME[1])

        logger.info("Removing %s from VM", config.NIC_NAME[1])
        if not removeNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        ):
            logger.error("Failed to remove %s", config.NIC_NAME[1])

##############################################################################


@attr(tier=1)
class TestNetworkFilterCase03(TestCase):
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

    @tcms(6955, 198920)
    def test_check_network_filter_via_ebtables(self):
        """
        Check that VM NIC has network filter via ebtables
        """
        vm_macs = get_vm_macs(vm=config.VM_NAME[0],
                              nics=[config.NIC_NAME[0]])
        logger.info("Check ebtables rules for running VM")
        if not checkNetworkFilteringEbtables(
                positive=True, host=config.HOSTS_IP[0],
                user=config.VMS_LINUX_USER, passwd=config.VMS_LINUX_PW,
                nics="1", vm_macs=vm_macs
        ):
            raise NetworkException(
                "Network filter is not enabled via ebtables on the VM NICs"
            )

        logger.info("Stopping the VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("fail to stop the VM")

        logger.info("Check ebtables rules for stopped VM")
        if not checkNetworkFilteringEbtables(
                positive=False, host=config.HOSTS_IP[0],
                user=config.VMS_LINUX_USER, passwd=config.VMS_LINUX_PW,
                nics="1", vm_macs=vm_macs
        ):
            raise NetworkException(
                "Network filter is enabled via ebtables on the VM NICs "
            )

    @classmethod
    def teardown_class(cls):
        """
        Start the VM
        """
        logger.info("Starting the VM and wait for status up")
        if not startVm(
                positive=True, vm=config.VM_NAME[0], wait_for_status="up"
        ):
            logger.error("failed to start the VM %s", config.VM_NAME[0])

##############################################################################


@attr(tier=1)
class TestNetworkFilterCase04(TestCase):
    """
    Check that Network Filter is disabled via ebtables on after VNIC hot-plug
    and still active after hot-unplug for remaining NICs
    """
    __test__ = True

    @tcms(6955, 198966)
    def test_check_network_filter_via_ebtables(self):
        """
        Check that VM NICs has network filter via ebtables
        """
        vm_nic1_mac = get_vm_macs(vm=config.VM_NAME[0],
                                  nics=[config.NIC_NAME[0]])
        logger.info("Check ebtables rules for %s", config.NIC_NAME[0])
        if not checkNetworkFilteringEbtables(
                positive=True, host=config.HOSTS_IP[0],
                user=config.VMS_LINUX_USER, passwd=config.VMS_LINUX_PW,
                nics="1", vm_macs=vm_nic1_mac
        ):
            raise NetworkException(
                "Network filter is not enabled via ebtables for %s" %
                config.NIC_NAME[0]
            )

        logger.info("Adding new NIC to VM")
        if not addNic(
                positive=True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
                interface=config.NIC_TYPE_RTL8139, network=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Failed to add NIC %s to VM" % config.NIC_NAME[1])

        vm_nic2_mac = get_vm_macs(vm=config.VM_NAME[0],
                                  nics=[config.NIC_NAME[1]])
        logger.info("Check ebtables rules for %s", config.NIC_NAME[1])
        if not checkNetworkFilteringEbtables(
                positive=True, host=config.HOSTS_IP[0],
                user=config.VMS_LINUX_USER, passwd=config.VMS_LINUX_PW,
                nics="1", vm_macs=vm_nic2_mac
        ):
            raise NetworkException(
                "Network filter is not enabled via ebtables for %s" %
                config.NIC_NAME[1]
            )

        logger.info("hot-unplug %s from the VM", config.NIC_NAME[1])
        if not updateNic(
                positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1],
                plugged="false"
        ):
            raise NetworkException(
                "Failed to update %s to un-plugged" % config.NIC_NAME[1]
            )

        if not removeNic(positive=True, vm=config.VM_NAME[0],
                         nic=config.NIC_NAME[1]):
            raise NetworkException("Failed to remove %s" % config.NIC_NAME[1])

        vm_nic1_1_mac = get_vm_macs(vm=config.VM_NAME[0],
                                    nics=[config.NIC_NAME[0]])
        logger.info("Check ebtables rules for %s", config.NIC_NAME[0])
        if not checkNetworkFilteringEbtables(
                positive=True, host=config.HOSTS_IP[0],
                user=config.VMS_LINUX_USER, passwd=config.VMS_LINUX_PW,
                nics="1", vm_macs=vm_nic1_1_mac
        ):
            raise NetworkException(
                "Network filter is not enabled via ebtables for %s",
                config.NIC_NAME[0]
            )

##############################################################################


@attr(tier=1)
class TestNetworkFilterCase05(TestCase):
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
        if not setNetworkFilterStatus(
                enable=False, host=config.VDC_HOST, user=config.VDC_ROOT_USER,
                passwd=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException("Failed to disable network filter")

        logger.info("Starting the VM")
        if not startVm(
                positive=True, vm=config.VM_NAME[0], wait_for_status="up"
        ):
            raise NetworkException("failed to start the VM")

    @tcms(6955, 203261)
    def test_check_network_filter_on_nic(self):
        """
        Check that VM run without network filter.
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not checkNetworkFilteringDumpxml(
                positive=False, host=config.HOSTS_IP[0],
                user=config.HOSTS_USER, passwd=config.HOSTS_PW,
                vm=config.VM_NAME[0], nics="1"
        ):
            raise NetworkException("Network Filter is enabled via dumpxml")

        vm_nic1_mac = get_vm_macs(vm=config.VM_NAME[0],
                                  nics=[config.NIC_NAME[0]])
        logger.info("Check ebtables rules for %s", config.NIC_NAME[0])
        if not checkNetworkFilteringEbtables(
                positive=False, host=config.HOSTS_IP[0],
                user=config.VMS_LINUX_USER, passwd=config.VMS_LINUX_PW,
                nics="1", vm_macs=vm_nic1_mac
        ):
            raise NetworkException(
                "Network filter is enabled via ebtables for %s" %
                config.NIC_NAME[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Enabling network filter on engine
        """
        logger.info("Enabling network filter on engine")
        if not setNetworkFilterStatus(
                enable=True, host=config.VDC_HOST, user=config.VDC_ROOT_USER,
                passwd=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Failed to enable network filter")

##############################################################################


def get_vm_macs(vm, nics):
    """
    Description: Get MACs from VM
    :param vm: VM name.
    :param nics: List of NICs to get the MACs for
    :return List of VM MACs
    """
    vm_macs = []
    logger.info("Get MAC address for VM NICs")
    for nic in nics:
        vm_mac = getVmMacAddress(positive=True, vm=vm, nic=nic)
        vm_macs.append(vm_mac[1]["macAddress"])

    if len(vm_macs) != len(nics):
        logging.error("Fail to get MAC from VM")
        return False
    return vm_macs
