#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV cases with import/export and templates
"""

import pytest

from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    vms as ll_vms
)
import config as sriov_conf
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    prepare_setup_import_export, init_fixture, reset_host_sriov_params
)
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import clean_host_interfaces


@attr(tier=2)
@pytest.mark.usefixtures(
    init_fixture.__name__,
    reset_host_sriov_params.__name__,
    clean_host_interfaces.__name__,
    prepare_setup_import_export.__name__,
    start_vm.__name__
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovImportExport01(NetworkTest):
    """
    Cases for Import/Export with VM and VFs
    """

    # General
    vm_nic_1 = sriov_conf.TEMPLATE_TEST_VNICS[1][0]
    vm_nic_2 = sriov_conf.TEMPLATE_TEST_VNICS[1][1]
    net_1 = sriov_conf.IMPORT_EXPORT_NETS[1][0]
    net_2 = sriov_conf.IMPORT_EXPORT_NETS[1][1]
    import_vm_name = "sriov_import_vm"
    import_template_name = "sriov_import_template"
    vm_from_template = "sriov_from_template"

    # prepare_setup_import_export
    net_list = [net_1, net_2]
    dc = conf.DC_0
    vm = "sriov_export_vm"
    cluster = conf.CL_0
    vm_nic_list = [vm_nic_1, vm_nic_2]
    export_template_name = "sriov_export_template"
    templates_list = [import_template_name, export_template_name]
    export_domain = conf.EXPORT_DOMAIN_NAME
    vms_list = [import_vm_name, vm, vm_from_template]

    # clean_host_interfaces
    hosts_nets_nic_dict = {
        0: {}
    }

    # stop VM
    vms_to_stop = vms_list

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
            import_storagedomain=sriov_conf.SD_NAME, cluster=self.cluster,
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
            destination_storage_domain=sriov_conf.SD_NAME,
            cluster=self.cluster, name=self.import_template_name
        )
        testflow.step("Create VM from template")
        assert ll_vms.createVm(
            positive=True, vmName=self.vm_from_template, vmDescription="",
            cluster=self.cluster, storageDomainName=sriov_conf.SD_NAME,
            provisioned_size=conf.VM_DISK_SIZE,
            template=self.import_template_name
        )
        testflow.step("Start VM")
        assert network_helper.run_vm_once_specific_host(
            vm=self.vm_from_template, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        )
