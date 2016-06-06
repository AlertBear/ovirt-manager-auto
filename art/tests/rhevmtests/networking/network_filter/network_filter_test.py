"""
Testing NetworkFilter feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import (
    case_01_fixture, case_02_fixture, case_04_fixture,
    network_filter_prepare_setup
)


logger = logging.getLogger("Network_Filter_Cases")

# TODO: All tests are set to __test__ = False since this feature changed in
# 4.0 and we don't have API for it yet


@attr(tier=2)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(case_01_fixture.__name__)
class TestNetworkFilterCase01(NetworkTest):
    """
    Check that network filter is enabled for hot-plug  NIC to on VM
    """
    __test__ = False

    @polarion("RHEVM3-3780")
    def test_check_network_filter_on_nic(self):
        """
        Check that the new NIC has network filter
        """
        testflow.step(
            "Check that Network Filter is enabled for %s via dumpxml",
            conf.NIC_NAME[1]
        )
        self.assertTrue(
            ll_hosts.check_network_filtering_dumpxml(
                positive=True, vds_resource=conf.VDS_0_HOST,
                vm=conf.VM_NAME[0], nics="2"
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_02_fixture.__name__)
class TestNetworkFilterCase02(NetworkTest):
    """
    Check that Network Filter is enabled via ebtables on running VM and
    disabled on stopped VM
    """
    __test__ = False

    @polarion("RHEVM3-3783")
    def test_check_network_filter_via_ebtables(self):
        """
        Check that VM NIC has network filter via ebtables
        """
        vm_macs = hl_vms.get_vm_macs(
            vm=conf.VM_NAME[0], nics=[conf.NIC_NAME[0]]
        )

        testflow.step("Check ebtables rules for running VM")
        self.assertTrue(
            ll_hosts.check_network_filtering_ebtables(
                host_obj=conf.VDS_0_HOST, vm_macs=vm_macs
            )
        )

        testflow.step("Stopping the VM %s", conf.VM_NAME[0])
        self.assertTrue(ll_vms.stopVm(positive=True, vm=conf.VM_NAME[0]))

        testflow.step(
            "Check ebtables rules for stopped VM %s", conf.VM_NAME[0]
        )
        self.assertFalse(
            ll_hosts.check_network_filtering_ebtables(
                host_obj=conf.VDS_0_HOST, vm_macs=vm_macs
            )
        )


@attr(tier=2)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(network_filter_prepare_setup.__name__)
class TestNetworkFilterCase03(NetworkTest):
    """
    Check that Network Filter is disabled via ebtables on after VNIC hot-plug
    and still active after hot-unplug for remaining NICs
    """
    __test__ = False

    @polarion("RHEVM3-3784")
    def test_check_network_filter_via_ebtables(self):
        """
        Check that VM NICs has network filter via ebtables
        """
        vm_nic1_mac = hl_vms.get_vm_macs(
            vm=conf.VM_NAME[0], nics=[conf.NIC_NAME[0]]
        )

        testflow.step("Check ebtables rules for %s", conf.NIC_NAME[0])
        self.assertTrue(
            ll_hosts.check_network_filtering_ebtables(
                host_obj=conf.VDS_0_HOST, vm_macs=vm_nic1_mac
            )
        )

        testflow.step(
            "Adding new NIC %s to VM %s", conf.NIC_NAME[1], conf.VM_NAME[0]
        )
        self.assertTrue(
            ll_vms.addNic(
                positive=True, vm=conf.VM_NAME[0], name=conf.NIC_NAME[1],
                interface=conf.NIC_TYPE_RTL8139, network=conf.MGMT_BRIDGE
            )
        )

        vm_nic2_mac = hl_vms.get_vm_macs(
            vm=conf.VM_NAME[0],  nics=[conf.NIC_NAME[1]]
        )

        testflow.step("Check ebtables rules for %s", conf.NIC_NAME[1])
        self.assertTrue(
            ll_hosts.check_network_filtering_ebtables(
                host_obj=conf.VDS_0_HOST, vm_macs=vm_nic2_mac
            )
        )

        testflow.step(
            "hot-unplug %s from the VM %s", conf.NIC_NAME[1], conf.VM_NAME[0]
        )
        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=conf.VM_NAME[0], nic=conf.NIC_NAME[1],
                plugged="false"
            )
        )

        self.assertTrue(
            ll_vms.removeNic(
                positive=True, vm=conf.VM_NAME[0], nic=conf.NIC_NAME[1]
            )
        )

        vm_nic1_1_mac = hl_vms.get_vm_macs(
            vm=conf.VM_NAME[0], nics=[conf.NIC_NAME[0]]
        )

        testflow.step("Check ebtables rules for %s", conf.NIC_NAME[0])
        self.assertTrue(
            ll_hosts.check_network_filtering_ebtables(
                host_obj=conf.VDS_0_HOST, vm_macs=vm_nic1_1_mac
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_04_fixture.__name__)
class TestNetworkFilterCase04(NetworkTest):
    """
    Disabling network filter then check that VM run without network filter.
    """
    __test__ = False

    @polarion("RHEVM3-3785")
    def test_check_network_filter_on_nic(self):
        """
        Check that VM run without network filter.
        """
        testflow.step("Check that Network Filter is enabled via dumpxml")
        self.assertTrue(
            ll_hosts.check_network_filtering_dumpxml(
                positive=False, vds_resource=conf.VDS_0_HOST,
                vm=conf.VM_NAME[0], nics="1"
            )
        )

        vm_nic1_mac = hl_vms.get_vm_macs(
            vm=conf.VM_NAME[0], nics=[conf.NIC_NAME[0]]
        )
        testflow.step("Check ebtables rules for %s", conf.NIC_NAME[0])
        self.assertFalse(
            ll_hosts.check_network_filtering_ebtables(
                host_obj=conf.VDS_0_HOST, vm_macs=vm_nic1_mac
            )
        )
