#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV cases with import/export and templates
"""

import pytest

import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sriov_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    prepare_setup_import_export, clear_hosts_interfaces, init_fixture,
    reset_host_sriov_params
)


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    reset_host_sriov_params.__name__,
    clear_hosts_interfaces.__name__,
    prepare_setup_import_export.__name__,
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovImportExport01(NetworkTest):
    """
    Cases for Import/Export with VM and VFs
    """
    __test__ = True
    vm = "sriov_export_vm"
    vm_nic_1 = conf.NIC_NAME[1]
    vm_nic_2 = conf.NIC_NAME[2]
    net_1 = sriov_conf.IMPORT_EXPORT_NETS[1][0]
    net_2 = sriov_conf.IMPORT_EXPORT_NETS[1][1]
    dc = conf.DC_0
    cluster = conf.CL_0
    net_list = [net_1, net_2]
    vm_nic_list = [vm_nic_1, vm_nic_2]
    export_domain = conf.EXPORT_DOMAIN_NAME
    import_vm_name = "sriov_import_vm"
    export_template_name = "sriov_export_template"
    import_template_name = "sriov_import_template"
    vm_from_template = "sriov_from_template"
    vms_list = [import_vm_name, vm, vm_from_template]
    templates_list = [import_template_name, export_template_name]
    sd_name = ll_storagedomains.getStorageDomainNamesForType(
        datacenter_name=dc, storage_type=conf.STORAGE_TYPE
    )[0]

    @polarion("RHEVM3-10676")
    def test_01_export_vm_with_vf(self):
        """
        Export VM with VF to export domain
        """
        testflow.step("Export VM with VF to export domain")
        assert ll_vms.exportVm(
            positive=True, vm=self.vm, storagedomain=self.export_domain
        )

    @polarion("RHEVM3-14733")
    def test_02_import_vm_with_vf(self):
        """
        Import VM with VF from export domain
        Start VM
        """
        testflow.step("Import VM with VF from export domain")
        assert ll_vms.importVm(
            positive=True, vm=self.vm, export_storagedomain=self.export_domain,
            import_storagedomain=self.sd_name, cluster=self.cluster,
            name=self.import_vm_name
        )
        testflow.step("Start VM")
        assert network_helper.run_vm_once_specific_host(
            vm=self.import_vm_name, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        )

    @polarion("RHEVM3-14734")
    def test_03_export_template_with_vf(self):
        """
        Export template with VF to export domain
        """
        testflow.step("Export template with VF to export domain")
        assert ll_templates.exportTemplate(
            positive=True, template=self.export_template_name,
            storagedomain=self.export_domain
        )

    @polarion("RHEVM3-10409")
    def test_04_import_template_with_vf(self):
        """
        Import template with VF from export domain
        Create VM from template
        Start VM
        """
        testflow.step("Import template with VF from export domain")
        assert ll_templates.import_template(
            positive=True, template=self.export_template_name,
            source_storage_domain=self.export_domain,
            destination_storage_domain=self.sd_name, cluster=self.cluster,
            name=self.import_template_name
        )
        testflow.step("Create VM from template")
        assert ll_vms.createVm(
            positive=True, vmName=self.vm_from_template, vmDescription="",
            cluster=self.cluster, storageDomainName=self.sd_name,
            provisioned_size=conf.VM_DISK_SIZE,
            template=self.import_template_name
        )
        testflow.step("Start VM")
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm_from_template, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        )
