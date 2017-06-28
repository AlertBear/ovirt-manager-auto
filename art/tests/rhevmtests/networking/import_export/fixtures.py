#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for import/export
"""

import pytest

import config as import_export_conf
import helper
import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_network,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_storagedomains,
    templates as ll_templates,
    vms as ll_vms
)
from art.unittest_lib import testflow
from rhevmtests import networking


@pytest.fixture(scope="module")
def import_export_prepare_setup(request):
    """
    Prepare setup
    """

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
        assert hl_networks.remove_net_from_setup(
            host=[conf.HOST_0_NAME], all_net=True,
            data_center=conf.DC_0
        )
    request.addfinalizer(fin3)

    @networking.ignore_exception
    def fin2():
        """
        Finalizer for remove template from export domain
        """
        testflow.teardown("Remove template from export domain")
        ll_templates.removeTemplateFromExportDomain(
            positive=True, template=import_export_conf.IE_TEMPLATE_NAME,
            export_storagedomain=conf.EXPORT_DOMAIN_NAME
        )
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Finalizer for remove VM from export domain
        """
        testflow.teardown("Remove VM from export domain")
        ll_vms.remove_vm_from_export_domain(
            positive=True, vm=import_export_conf.IE_VM_NAME,
            datacenter=conf.DC_0,
            export_storagedomain=conf.EXPORT_DOMAIN_NAME
        )
    request.addfinalizer(fin1)

    import_export_conf.SD_NAME = (
        ll_storagedomains.getStorageDomainNamesForType(
            datacenter_name=conf.DC_0, storage_type=conf.STORAGE_TYPE
        )[0]
    )

    testflow.setup("Create VM %s", import_export_conf.IE_VM_NAME)
    assert ll_vms.createVm(
        positive=True, vmName=import_export_conf.IE_VM_NAME, vmDescription="",
        cluster=conf.CL_0,
        storageDomainName=import_export_conf.SD_NAME,
        provisioned_size=conf.VM_DISK_SIZE
    )

    sn_dict = {
        "add": {
            "1": {
                "network": import_export_conf.NETS[0],
                "nic": conf.HOST_0_NICS[1]
            },
            "2": {
                "network": import_export_conf.NETS[1],
                "nic": conf.HOST_0_NICS[2]
            },
            "3": {
                "network": import_export_conf.NETS[2],
                "nic": conf.HOST_0_NICS[3]
            }
        }
    }

    assert hl_networks.create_and_attach_networks(
        data_center=conf.DC_0, cluster=conf.CL_0,
        network_dict=import_export_conf.LOCAL_DICT
    )
    assert hl_host_network.setup_networks(
        host_name=conf.HOST_0_NAME, **sn_dict
    )
    net_list = (
        [conf.MGMT_BRIDGE] + import_export_conf.NETS[:3] + [None]
    )
    helper.add_nics_to_vm(net_list=net_list)
    testflow.setup("Create template %s", import_export_conf.IE_TEMPLATE_NAME)
    assert ll_templates.createTemplate(
        positive=True, vm=import_export_conf.IE_VM_NAME, cluster=conf.CL_0,
        name=import_export_conf.IE_TEMPLATE_NAME
    )
    testflow.setup("Export template %s", import_export_conf.IE_TEMPLATE_NAME)
    assert ll_templates.exportTemplate(
        positive=True, template=import_export_conf.IE_TEMPLATE_NAME,
        storagedomain=conf.EXPORT_DOMAIN_NAME
    )
    testflow.setup(
        "Export VM %s to export storage domain", import_export_conf.IE_VM_NAME
    )
    assert ll_vms.exportVm(
        positive=True, vm=import_export_conf.IE_VM_NAME,
        storagedomain=conf.EXPORT_DOMAIN_NAME
    )
    testflow.setup("Remove VM %s", import_export_conf.IE_VM_NAME)
    assert ll_vms.removeVm(
        positive=True, vm=import_export_conf.IE_VM_NAME, stopVM="true"
    )
    testflow.setup("Remove template %s", import_export_conf.IE_TEMPLATE_NAME)
    assert ll_templates.remove_template(
        positive=True, template=import_export_conf.IE_TEMPLATE_NAME
    )


@pytest.fixture(scope="class")
def import_vms(request, import_export_prepare_setup):
    """
    Import VMs
    """
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
            positive=True, vm=import_export_conf.IE_VM_NAME,
            export_storagedomain=conf.EXPORT_DOMAIN_NAME,
            import_storagedomain=import_export_conf.SD_NAME,
            cluster=conf.CL_0, name=name
        )


@pytest.fixture(scope="class")
def import_templates(request, import_export_prepare_setup):
    """
    Import templates
    """
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
            positive=True, template=import_export_conf.IE_TEMPLATE_NAME,
            source_storage_domain=conf.EXPORT_DOMAIN_NAME,
            destination_storage_domain=import_export_conf.SD_NAME,
            cluster=conf.CL_0, name=name
        )


@pytest.fixture(scope="class")
def remove_networks(request, import_export_prepare_setup):
    """
    Remove networks from datacenter and host
    """
    net_list = request.node.cls.net_list
    testflow.setup(
        "Remove networks %s from host %s", net_list[:3], conf.HOST_0_NAME
    )
    assert hl_host_network.remove_networks_from_host(
        host_name=conf.HOST_0_NAME, networks=net_list[:3]
    )
    testflow.setup("Remove networks %s from datacenter", net_list[:2])
    assert hl_networks.remove_networks(positive=True, networks=net_list[:2])
