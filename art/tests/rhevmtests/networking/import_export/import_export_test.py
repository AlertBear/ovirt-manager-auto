#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Import/Export feature.
1 DC, 1 Cluster, 1 Hosts, 1 export domain, 1 VM and 1 templates will be
created for testing.
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as import_export_conf
import helper
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import import_vms, import_templates, remove_networks


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(import_vms.__name__)
class TestImportExportCase01(NetworkTest):
    """
    Check that VM could be imported with all the networks
    Check that VM imported more than once keeps all it's network configuration
    """
    __test__ = True
    vms_list = [
        import_export_conf.IE_VM, import_export_conf.IMP_MORE_THAN_ONCE_VM
    ]
    vms_to_import = [None, vms_list[1]]
    net1 = import_export_conf.NETS[0]
    net2 = import_export_conf.NETS[1]

    @polarion("RHEVM3-3760")
    def test_01_imported_vm_vnics(self):
        """
        Check that the VM is imported with all VNIC profiles
        """
        testflow.step("Check that the VM is imported with all VNIC profiles")
        assert helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, vm=self.vms_list[0]
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
        assert helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, vm=self.vms_list[1]
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(import_templates.__name__)
class TestImportExportCase02(NetworkTest):
    """
    Check that Template could be imported with all the networks
    Check that Template imported more than once keeps all it's network
    configuration
    """
    __test__ = True
    template_list = [
        import_export_conf.IMP_MORE_THAN_ONCE_TEMP,
        import_export_conf.IE_TEMPLATE
    ]
    templates_to_import = [None, template_list[0]]
    net1 = import_export_conf.NETS[0]
    net2 = import_export_conf.NETS[1]

    @polarion("RHEVM3-3766")
    def test_01_imported_temp_vnics(self):
        """
        Check that the Template is imported with all VNIC profiles
        """
        testflow.step(
            "Check that the Template is imported with all VNIC profiles"
        )
        assert helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, template=self.template_list[1]
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
        assert helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, template=self.template_list[0]
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_networks.__name__,
    import_templates.__name__,
    import_vms.__name__
)
class TestImportExportCase03(NetworkTest):
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
    vms_list = [import_export_conf.IE_VM, import_export_conf.IE_VM_2]
    templates_to_import = [import_export_conf.IE_TEMPLATE]
    template_list = templates_to_import
    vms_to_import = [vms_list[0]]
    nic_name = import_export_conf.VNICS[3]
    net_list = import_export_conf.NETS
    net1 = net_list[0]
    net2 = net_list[1]

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
        assert helper.check_imported_vm_or_templates(
            net1=None, net2=None, vm=self.vms_list[0]
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
        assert helper.check_imported_vm_or_templates(
            net1=None, net2=None, template=import_export_conf.IE_TEMPLATE
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
        assert ll_vms.startVm(positive=False, vm=self.vms_list[0])
        assert ll_vms.removeNic(
            positive=True, vm=self.vms_list[0], nic=self.nic_name
        )
        testflow.step(
            "Positive - Start VM after removing network that doesn't reside "
            "on any host in the setup"
        )
        assert ll_vms.startVm(
            positive=True, vm=self.vms_list[0], wait_for_status="up"
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
        assert ll_vms.addVm(
            positive=True, name=self.vms_list[1], cluster=net_conf.CL_0,
            template=import_export_conf.IE_TEMPLATE,
            display_type=net_conf.DISPLAY_TYPE
        )
        testflow.step(
            "Negative - Start VM, created from template when one of the "
            "networks, attached to it doesn't reside on any host in the setup"
        )
        assert ll_vms.startVm(positive=False, vm=self.vms_list[1])
        assert ll_vms.removeNic(
            positive=True, vm=self.vms_list[1], nic=self.nic_name
        )
        testflow.step(
            "Positive - Start VM, created from template after removing network"
            "that doesn't reside on any host in the setup"
        )
        assert ll_vms.startVm(
            positive=True, vm=self.vms_list[1], wait_for_status="up"
        )
