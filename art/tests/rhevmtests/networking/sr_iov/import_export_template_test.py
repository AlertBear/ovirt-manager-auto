#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV cases with import/export and templates
"""

import helper
import logging
import pytest
import config as conf
from art.test_handler.tools import polarion
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains

logger = logging.getLogger("SR_IOV_Import_Export_Template_Cases")


def setup_module():
    """
    Add networks to DC and cluster
    """
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.IMPORT_EXPORT_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_module():
    """
    Removes networks from DC and cluster
    """
    network_helper.remove_networks_from_setup()


@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSriovImportExport01(helper.TestSriovBase):
    """
    Cases for Import/Export with VM and VFs
    """
    __test__ = True
    vm = "sriov_export_vm"
    vm_nic_1 = conf.NIC_NAME[1]
    vm_nic_2 = conf.NIC_NAME[2]
    net_1 = conf.IMPORT_EXPORT_NETS[1][0]
    net_2 = conf.IMPORT_EXPORT_NETS[1][1]
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

    @classmethod
    def setup_class(cls):
        """
        Enable 4 VF on host
        Update networks vNIC profiles to have passthrough
        Create VM
        Add two vNICs profiles to VM with the above networks
        Create template from VM
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )

        if not cls.pf_obj.set_number_of_vf(4):
            raise conf.NET_EXCEPTION()

        for net in cls.net_list:
            if not ll_networks.update_vnic_profile(
                name=net, network=net, data_center=cls.dc, pass_through=True
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.createVm(
            positive=True, vmName=cls.vm, vmDescription="",
            cluster=cls.cluster, storageDomainName=cls.sd_name,
            provisioned_size=conf.VM_DISK_SIZE
        ):
            raise conf.NET_EXCEPTION()

        for net, vm_nic in zip(cls.net_list, cls.vm_nic_list):
            if not ll_vms.addNic(
                positive=True, vm=cls.vm, name=vm_nic, network=net,
                vnic_profile=net, interface=conf.PASSTHROUGH_INTERFACE
            ):
                raise conf.NET_EXCEPTION()

        if not ll_templates.createTemplate(
            positive=True, vm=cls.vm, name=cls.export_template_name
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10676")
    def test_01_export_vm_with_vf(self):
        """
        Export VM with VF to export domain
        """
        if not ll_vms.exportVm(
            positive=True, vm=self.vm, storagedomain=self.export_domain
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14733")
    def test_02_import_vm_with_vf(self):
        """
        Import VM with VF from export domain
        Start VM
        """
        if not ll_vms.importVm(
            positive=True, vm=self.vm, export_storagedomain=self.export_domain,
            import_storagedomain=self.sd_name, cluster=self.cluster,
            name=self.import_vm_name
        ):
            raise conf.NET_EXCEPTION()

        if not network_helper.run_vm_once_specific_host(
            vm=self.import_vm_name, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14734")
    def test_03_export_template_with_vf(self):
        """
        Export template with VF to export domain
        """
        if not ll_templates.exportTemplate(
            positive=True, template=self.export_template_name,
            storagedomain=self.export_domain
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10409")
    def test_04_import_template_with_vf(self):
        """
        Import template with VF from export domain
        Create VM from template
        Start VM
        """
        if not ll_templates.import_template(
            positive=True, template=self.export_template_name,
            source_storage_domain=self.export_domain,
            destination_storage_domain=self.sd_name, cluster=self.cluster,
            name=self.import_template_name
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.createVm(
            positive=True, vmName=self.vm_from_template, vmDescription="",
            cluster=self.cluster, storageDomainName=self.sd_name,
            provisioned_size=conf.VM_DISK_SIZE,
            template=self.import_template_name
        ):
            raise conf.NET_EXCEPTION()

        if not network_helper.run_vm_once_specific_host(
            vm=self.vm_from_template, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Stop all VMs
        Remove all Vms
        Remove exported VM from export domain
        Remove template
        Remove template from export domain
        """
        ll_vms.stop_vms_safely(vms_list=cls.vms_list)
        ll_vms.removeVms(positive=True, vms=cls.vms_list)
        ll_vms.remove_vm_from_export_domain(
            positive=True, vm=cls.vm, datacenter=cls.dc,
            export_storagedomain=cls.export_domain
        )
        for template in cls.templates_list:
            ll_templates.removeTemplate(positive=True, template=template)

        ll_templates.removeTemplateFromExportDomain(
            positive=True, template=cls.export_template_name,
            datacenter=cls.dc, export_storagedomain=cls.export_domain
        )
        super(TestSriovImportExport01, cls).teardown_class()
