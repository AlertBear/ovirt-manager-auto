#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Import/Export feature.
1 DC, 1 Cluster, 1 Hosts, 1 export domain, 1 VM and 1 templates will be
created for testing.
"""
import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helper
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import fixture_case_01, fixture_case_02, fixture_case_03

logger = logging.getLogger("Import_Export_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_01.__name__)
class TestIECase01(NetworkTest):
    """
    Check that VM could be imported with all the networks
    Check that VM imported more than once keeps all it's network configuration
    """
    __test__ = True
    vms_list = [net_conf.IE_VM, net_conf.IMP_MORE_THAN_ONCE_VM]
    net1 = conf.NETS[0]
    net2 = conf.NETS[1]

    @polarion("RHEVM3-3760")
    def test_01_imported_vm_vnics(self):
        """
        Check that the VM is imported with all VNIC profiles
        """
        testflow.step("Check that the VM is imported with all VNIC profiles")
        self.assertTrue(
            helper.check_imported_vm_or_templates(
                net1=self.net1, net2=self.net2, vm=self.vms_list[0]
            )
        )

    @polarion("RHEVM3-3769")
    def test_02_import_vm_more_than_once(self):
        """
        Check that VM imported more than once keeps all it's VNIC profiles
        """
        testflow.step(
            "Check that VM imported more than once keeps all it's VNIC "
            "profiles"
        )
        self.assertTrue(
            helper.check_imported_vm_or_templates(
                net1=self.net1, net2=self.net2, vm=self.vms_list[1]
            )
        )


@attr(tier=2)
@bz({"1339686": {}})
@pytest.mark.usefixtures(fixture_case_02.__name__)
class TestIECase02(NetworkTest):
    """
    Check that Template could be imported with all the networks
    Check that Template imported more than once keeps all it's network
    configuration
    """
    __test__ = True
    template_list = [net_conf.IMP_MORE_THAN_ONCE_TEMP, net_conf.IE_TEMPLATE]
    net1 = conf.NETS[0]
    net2 = conf.NETS[1]

    @polarion("RHEVM3-3766")
    def test_01_imported_temp_vnics(self):
        """
        Check that the Template is imported with all VNIC profiles
        """
        testflow.step(
            "Check that the Template is imported with all VNIC profiles"
        )
        self.assertTrue(
            helper.check_imported_vm_or_templates(
                net1=self.net1, net2=self.net2, template=self.template_list[1]
            )
        )

    @polarion("RHEVM3-3764")
    def test_02_import_more_than_once(self):
        """
        Check that Template imported more than once keeps all its VNIC
        profiles
        """
        testflow.step(
            "Check that Template imported more than once keeps all its VNIC"
            "profiles"
        )
        self.assertTrue(
            helper.check_imported_vm_or_templates(
                net1=self.net1, net2=self.net2, template=self.template_list[0]
            )
        )


@attr(tier=2)
@bz({"1339686": {}})
@pytest.mark.usefixtures(fixture_case_03.__name__)
class TestIECase03(NetworkTest):
    """
    Check for the VM and template:
    1) Check that the VNIC that had net1 and net2 on VM before import
       action, has an empty VNIC for that VNIC profiles after import completed
    2) Check that the Template that had net1 and net2 on VM before import
       action, has an empty VNIC for that VNIC profiles after import completed
    3) Start VM should fail when one of the networks attached to it doesn't
       reside on any host in the setup.
       Start VM after removing network that doesn't reside on any host
       in the setup should succeed.
    4) Create VM from imported template should succeed,
       Start VM should fail if nic4 with net3 exist on VM,
       Start VM should succeed after remove of nic 4 from VM.
    """
    __test__ = True
    vms_list = [net_conf.IE_VM, "IE_VM_2"]
    nic_name = net_conf.NIC_NAME[3]
    net1 = conf.NETS[0]
    net2 = conf.NETS[1]
    net_list = conf.NETS

    @polarion("RHEVM3-3771")
    def test_01_import_vm_vnic_profiles(self):
        """
        Check that the VNIC that had net1 and net2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        testflow.step(
            "Check that the VNIC that had net1 and net2 on VM before import"
            "action, has an empty VNIC for that VNIC profiles after import "
            "completed"
        )
        self.assertTrue(
            helper.check_imported_vm_or_templates(
                net1=None, net2=None, vm=self.vms_list[0]
            )
        )

    @polarion("RHEVM3-3765")
    def test_02_import_temp_vnic_profiles(self):
        """
        Check that the Template that had net1 and net2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        testflow.step(
            "Check that the Template that had net1 and net2 on VM before "
            "import action, has an empty VNIC for that VNIC profiles after "
            "import completed"
        )
        self.assertTrue(
            helper.check_imported_vm_or_templates(
                net1=None, net2=None, template=net_conf.IE_TEMPLATE
            )
        )

    @polarion("RHEVM3-3761")
    def test_03_start_vm(self):
        """
        1) Negative - Start VM when one of the networks attached to it doesn't
        reside on any host in the setup
        2) Positive - Start VM after removing network that doesn't reside on
        any host in the setup
        """
        testflow.step(
            "Negative - Start VM when one of the networks attached to it "
            "doesn't reside on any host in the setup"
        )
        self.assertTrue(ll_vms.startVm(positive=False, vm=self.vms_list[0]))
        self.assertTrue(
            ll_vms.removeNic(
                positive=True, vm=self.vms_list[0], nic=self.nic_name
            )
        )
        testflow.step(
            "Positive - Start VM after removing network that doesn't reside "
            "on any host in the setup"
        )
        self.assertTrue(
            ll_vms.startVm(
                positive=True, vm=self.vms_list[0], wait_for_status="up"
            )
        )

    @polarion("RHEVM3-3772")
    def test_04_start_vm_from_template(self):
        """
        1) Create VM from imported template
        2) Negative - Start VM, created from template when one of the
        networks, attached to it doesn't reside on any host in the setup
        3) Positive - Start VM, created from template after removing network
        that doesn't reside on any host in the setup
        """
        self.assertTrue(
            ll_vms.addVm(
                positive=True, name=self.vms_list[1], cluster=net_conf.CL_0,
                template=net_conf.IE_TEMPLATE,
                display_type=net_conf.DISPLAY_TYPE
            )
        )
        testflow.step(
            "Negative - Start VM, created from template when one of the "
            "networks, attached to it doesn't reside on any host in the setup"
        )
        self.assertTrue(ll_vms.startVm(positive=False, vm=self.vms_list[1]))
        self.assertTrue(
            ll_vms.removeNic(
                positive=True, vm=self.vms_list[1], nic=self.nic_name
            )
        )
        testflow.step(
            "Positive - Start VM, created from template after removing network"
            "that doesn't reside on any host in the setup"
        )
        self.assertTrue(
            ll_vms.startVm(
                positive=True, vm=self.vms_list[1], wait_for_status="up"
            )
        )
