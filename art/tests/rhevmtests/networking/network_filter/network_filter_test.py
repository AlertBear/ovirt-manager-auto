"""
Testing NetworkFilter feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import logging
from art.unittest_lib import common
from rhevmtests.networking import config
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.unittest_lib import NetworkTest as TestCase, attr

logger = logging.getLogger("Network_Filter_Cases")

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=2)
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

    @polarion("RHEVM3-3775")
    def test_check_filter_status_engine(self):
        """
        Check that Network Filter is enabled by default on engine
        """
        logger.info("Check that Network Filter is enabled on engine")
        if not test_utils.check_spoofing_filter_rule_by_ver(
            engine_resource=config.ENGINE
        ):
            raise config.NET_EXCEPTION("Network Filter is disabled on engine")

    @polarion("RHEVM3-3777")
    def test_check_filter_status_vdsm(self):
        """
        Check that Network Filter is enabled by default on VDSM
        """
        logger.info("Check that Network Filter is enabled on VDSM")
        if not ll_hosts.check_network_filtering(
                positive=True, vds_resource=config.VDS_HOSTS[0]
        ):
            raise config.NET_EXCEPTION("Network Filter is disabled on VDSM")

    @polarion("RHEVM3-3779")
    def test_check_filter_status_dump_xml(self):
        """
        Check that Network Filter is enabled by default via dumpxml
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=config.VDS_HOSTS[0],
            vm=config.VM_NAME[0], nics="1"
        ):
            raise config.NET_EXCEPTION(
                "Network Filter is disabled via dumpxml"
            )

##############################################################################


@attr(tier=2)
@common.skip_class_if(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
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
        if not ll_vms.addNic(
                positive=True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
                interface=config.NIC_TYPE_RTL8139, network=config.MGMT_BRIDGE
        ):
            raise config.NET_EXCEPTION(
                "Failed to add NIC %s to VM" % config.NIC_NAME[1]
            )

    @polarion("RHEVM3-3780")
    def test_check_network_filter_on_nic(self):
        """
        Check that the new NIC has network filter
        """
        logger.info(
            "Check that Network Filter is enabled for %s via dumpxml",
            config.NIC_NAME[1]
        )
        if not ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=config.VDS_HOSTS[0],
            vm=config.VM_NAME[0], nics="2"
        ):
            raise config.NET_EXCEPTION(
                "Network Filter is disabled for %s via dumpxml" %
                config.NIC_NAME[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Un-plug and remove nic2 from VM
        """
        logger.info("un-plug %s", config.NIC_NAME[1])
        if not ll_vms.hotUnplugNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        ):
            logger.error("Failed to unplug %s from VM", config.NIC_NAME[1])

        logger.info("Removing %s from VM", config.NIC_NAME[1])
        if not ll_vms.removeNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        ):
            logger.error("Failed to remove %s", config.NIC_NAME[1])

##############################################################################


@attr(tier=2)
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

    @polarion("RHEVM3-3783")
    def test_check_network_filter_via_ebtables(self):
        """
        Check that VM NIC has network filter via ebtables
        """
        vm_macs = get_vm_macs(vm=config.VM_NAME[0], nics=[config.NIC_NAME[0]])
        logger.info("Check ebtables rules for running VM")
        if not ll_hosts.check_network_filtering_ebtables(
            host_obj=config.VDS_HOSTS[0], vm_macs=vm_macs
        ):
            raise config.NET_EXCEPTION(
                "Network filter is not enabled via ebtables on the VM NICs"
            )

        logger.info("Stopping the VM")
        if not ll_vms.stopVm(positive=True, vm=config.VM_NAME[0]):
            raise config.NET_EXCEPTION("fail to stop the VM")

        logger.info("Check ebtables rules for stopped VM")
        if ll_hosts.check_network_filtering_ebtables(
            host_obj=config.VDS_HOSTS[0], vm_macs=vm_macs
        ):
            raise config.NET_EXCEPTION(
                "Network filter is enabled via ebtables on the VM NICs "
            )

    @classmethod
    def teardown_class(cls):
        """
        Start the VM
        """
        logger.info("Starting the VM and wait till it's up")
        if not net_help.run_vm_once_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0], wait_for_up_status=True
        ):
            logger.error(
                "Cannot start VM %s on host %s",
                config.VM_NAME[0], config.HOSTS[0]
            )

##############################################################################


@attr(tier=2)
@common.skip_class_if(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
class TestNetworkFilterCase04(TestCase):
    """
    Check that Network Filter is disabled via ebtables on after VNIC hot-plug
    and still active after hot-unplug for remaining NICs
    """
    __test__ = True

    @polarion("RHEVM3-3784")
    def test_check_network_filter_via_ebtables(self):
        """
        Check that VM NICs has network filter via ebtables
        """
        vm_nic1_mac = get_vm_macs(
            vm=config.VM_NAME[0], nics=[config.NIC_NAME[0]]
        )

        logger.info("Check ebtables rules for %s", config.NIC_NAME[0])
        if not ll_hosts.check_network_filtering_ebtables(
            host_obj=config.VDS_HOSTS[0], vm_macs=vm_nic1_mac
        ):
            raise config.NET_EXCEPTION(
                "Network filter is not enabled via ebtables for %s" %
                config.NIC_NAME[0]
            )

        logger.info("Adding new NIC to VM")
        if not ll_vms.addNic(
                positive=True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
                interface=config.NIC_TYPE_RTL8139, network=config.MGMT_BRIDGE
        ):
            raise config.NET_EXCEPTION(
                "Failed to add NIC %s to VM" % config.NIC_NAME[1]
            )

        vm_nic2_mac = get_vm_macs(
            vm=config.VM_NAME[0],  nics=[config.NIC_NAME[1]]
        )
        logger.info("Check ebtables rules for %s", config.NIC_NAME[1])
        if not ll_hosts.check_network_filtering_ebtables(
            host_obj=config.VDS_HOSTS[0], vm_macs=vm_nic2_mac
        ):
            raise config.NET_EXCEPTION(
                "Network filter is not enabled via ebtables for %s" %
                config.NIC_NAME[1]
            )

        logger.info("hot-unplug %s from the VM", config.NIC_NAME[1])
        if not ll_vms.updateNic(
                positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1],
                plugged="false"
        ):
            raise config.NET_EXCEPTION(
                "Failed to update %s to un-plugged" % config.NIC_NAME[1]
            )

        if not ll_vms.removeNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        ):
            raise config.NET_EXCEPTION(
                "Failed to remove %s" % config.NIC_NAME[1]
            )

        vm_nic1_1_mac = get_vm_macs(
            vm=config.VM_NAME[0], nics=[config.NIC_NAME[0]]
        )
        logger.info("Check ebtables rules for %s", config.NIC_NAME[0])
        if not ll_hosts.check_network_filtering_ebtables(
            host_obj=config.VDS_HOSTS[0], vm_macs=vm_nic1_1_mac
        ):
            raise config.NET_EXCEPTION(
                "Network filter is not enabled via ebtables for %s",
                config.NIC_NAME[0]
            )

##############################################################################


@attr(tier=2)
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
        if not ll_vms.stopVm(positive=True, vm=config.VM_NAME[0]):
            raise config.NET_EXCEPTION("fail to stop the VM")

        logger.info("Disabling network filter on engine")
        if not test_utils.set_network_filter_status(
                enable=False, engine_resource=config.ENGINE
        ):
            raise config.NET_EXCEPTION("Failed to disable network filter")

        logger.info("Starting the VM")
        if not ll_vms.startVm(
                positive=True, vm=config.VM_NAME[0], wait_for_status="up"
        ):
            raise config.NET_EXCEPTION("failed to start the VM")

    @polarion("RHEVM3-3785")
    def test_check_network_filter_on_nic(self):
        """
        Check that VM run without network filter.
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not ll_hosts.check_network_filtering_dumpxml(
            positive=False, vds_resource=config.VDS_HOSTS[0],
            vm=config.VM_NAME[0], nics="1"
        ):
            raise config.NET_EXCEPTION("Network Filter is enabled via dumpxml")

        vm_nic1_mac = get_vm_macs(
            vm=config.VM_NAME[0], nics=[config.NIC_NAME[0]]
        )
        logger.info("Check ebtables rules for %s", config.NIC_NAME[0])
        if ll_hosts.check_network_filtering_ebtables(
            host_obj=config.VDS_HOSTS[0], vm_macs=vm_nic1_mac
        ):
            raise config.NET_EXCEPTION(
                "Network filter is enabled via ebtables for %s" %
                config.NIC_NAME[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Enabling network filter on engine
        """
        logger.info("Enabling network filter on engine")
        if not test_utils.set_network_filter_status(
                enable=True, engine_resource=config.ENGINE
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
        vm_mac = ll_vms.getVmMacAddress(positive=True, vm=vm, nic=nic)
        vm_macs.append(vm_mac[1]["macAddress"])

    if len(vm_macs) != len(nics):
        logging.error("Fail to get MAC from VM")
        return False
    return vm_macs
