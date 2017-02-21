#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for import/export
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as import_export_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as networking_helper
from art.unittest_lib import testflow
from rhevmtests import networking
from rhevmtests.networking.fixtures import NetworkFixtures


class ImportExport(NetworkFixtures):
    """
    Fixtures for import/export
    """
    def __init__(self):
        super(ImportExport, self).__init__()
        self.export_domain = conf.EXPORT_DOMAIN_NAME
        self.ie_vm = import_export_conf.IE_VM_NAME
        self.ie_vm_2 = import_export_conf.IE_VM_2_NAME
        self.ie_template = import_export_conf.IE_TEMPLATE_NAME
        self.more_then_once_vm = import_export_conf.IMP_MORE_THAN_ONCE_VM_NAME
        self.more_then_once_template = (
            import_export_conf.IMP_MORE_THAN_ONCE_TEMP_NAME
        )


@pytest.fixture(scope="module")
def import_export_prepare_setup(request):
    """
    Prepare setup
    """
    import_export = ImportExport()

    @networking.ignore_exception
    def fin4():
        """
        Remove templates
        """
        testflow.teardown("Remove templates")
        networking.remove_unneeded_templates()
    request.addfinalizer(fin4)

    @networking.ignore_exception
    def fin3():
        """
        Finalizer for remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert networking_helper.remove_networks_from_setup(
            hosts=import_export.host_0_name
        )
    request.addfinalizer(fin3)

    @networking.ignore_exception
    def fin2():
        """
        Finalizer for remove template from export domain
        """
        testflow.teardown("Remove template from export domain")
        ll_templates.removeTemplateFromExportDomain(
            positive=True, template=import_export.ie_template,
            export_storagedomain=import_export.export_domain
        )
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Finalizer for remove VM from export domain
        """
        testflow.teardown("Remove VM from export domain")
        ll_vms.remove_vm_from_export_domain(
            positive=True, vm=import_export.ie_vm,
            datacenter=import_export.dc_0,
            export_storagedomain=import_export.export_domain
        )
    request.addfinalizer(fin1)

    import_export_conf.SD_NAME = (
        ll_storagedomains.getStorageDomainNamesForType(
            datacenter_name=import_export.dc_0, storage_type=conf.STORAGE_TYPE
        )[0]
    )

    testflow.setup("Create VM %s", import_export.ie_vm)
    assert ll_vms.createVm(
        positive=True, vmName=import_export.ie_vm, vmDescription="",
        cluster=import_export.cluster_0,
        storageDomainName=import_export_conf.SD_NAME,
        provisioned_size=conf.VM_DISK_SIZE
    )

    sn_dict = {
        "add": {
            "1": {
                "network": import_export_conf.NETS[0],
                "nic": import_export.host_0_nics[1]
            },
            "2": {
                "network": import_export_conf.NETS[1],
                "nic": import_export.host_0_nics[2]
            },
            "3": {
                "network": import_export_conf.NETS[2],
                "nic": import_export.host_0_nics[3]
            }
        }
    }
    testflow.setup(
        "Create and attach networks %s to datacenter %s and clusters %s",
        import_export_conf.LOCAL_DICT, import_export.dc_0,
        import_export.cluster_0
    )
    assert hl_networks.create_and_attach_networks(
        data_center=import_export.dc_0, cluster=import_export.cluster_0,
        network_dict=import_export_conf.LOCAL_DICT
    )
    assert hl_host_network.setup_networks(
        host_name=import_export.host_0_name, **sn_dict
    )
    net_list = (
        [import_export.mgmt_bridge] + import_export_conf.NETS[:3] + [None]
    )
    helper.add_nics_to_vm(net_list=net_list)
    testflow.setup("Create template %s", import_export.ie_template)
    assert ll_templates.createTemplate(
        positive=True, vm=import_export.ie_vm, cluster=import_export.cluster_0,
        name=import_export.ie_template
    )
    testflow.setup("Export template %s", import_export.ie_template)
    assert ll_templates.exportTemplate(
        positive=True, template=import_export.ie_template,
        storagedomain=import_export.export_domain
    )
    testflow.setup(
        "Export VM %s to export storage domain", import_export.ie_vm
    )
    assert ll_vms.exportVm(
        positive=True, vm=import_export.ie_vm,
        storagedomain=import_export.export_domain
    )
    testflow.setup("Remove VM %s", import_export.ie_vm)
    assert ll_vms.removeVm(
        positive=True, vm=import_export.ie_vm, stopVM="true"
    )
    testflow.setup("Remove template %s", import_export.ie_template)
    assert ll_templates.remove_template(
        positive=True, template=import_export.ie_template
    )


@pytest.fixture(scope="class")
def import_vms(request, import_export_prepare_setup):
    """
    Import VMs
    """
    import_export = ImportExport()
    vms_to_import = request.node.cls.vms_to_import
    vms_list = request.node.cls.vms_list

    def fin():
        """
        Remove VMs
        """
        testflow.teardown("Remove VMs %s", vms_list)
        assert ll_vms.safely_remove_vms(vms=vms_list)
    request.addfinalizer(fin)

    for name in vms_to_import:
        testflow.setup("Import VM %s from export domain", name)
        assert ll_vms.importVm(
            positive=True, vm=import_export.ie_vm,
            export_storagedomain=import_export.export_domain,
            import_storagedomain=import_export_conf.SD_NAME,
            cluster=import_export.cluster_0, name=name
        )


@pytest.fixture(scope="class")
def import_templates(request, import_export_prepare_setup):
    """
    Import templates
    """
    import_export = ImportExport()
    templates_to_import = request.node.cls.templates_to_import
    template_list = request.node.cls.template_list

    def fin():
        """
        Remove templates
        """
        testflow.teardown("Remove templates %s", template_list)
        assert ll_templates.waitForTemplatesStates(names=template_list)
        assert ll_templates.remove_templates(
            positive=True, templates=template_list
        )
    request.addfinalizer(fin)

    for name in templates_to_import:
        testflow.setup("Import template %s from export domain", name)
        assert ll_templates.import_template(
            positive=True, template=import_export.ie_template,
            source_storage_domain=import_export.export_domain,
            destination_storage_domain=import_export_conf.SD_NAME,
            cluster=import_export.cluster_0, name=name
        )


@pytest.fixture(scope="class")
def remove_networks(request, import_export_prepare_setup):
    """
    Remove networks from datacenter and host
    """
    import_export = ImportExport()
    net_list = request.node.cls.net_list
    testflow.setup(
        "Remove networks %s from host %s", net_list[:3],
        import_export.host_0_name
    )
    assert hl_host_network.remove_networks_from_host(
        host_name=import_export.host_0_name, networks=net_list[:3]
    )
    testflow.setup("Remove networks %s from datacenter", net_list[:2])
    assert hl_networks.remove_networks(positive=True, networks=net_list[:2])
