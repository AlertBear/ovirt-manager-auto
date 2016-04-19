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
import config as im_ex_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as networking_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class ImportExport(NetworkFixtures):
    """
    Fixtures for import/export
    """
    def __init__(self):
        super(ImportExport, self).__init__()
        im_ex_conf.SD_NAME = ll_storagedomains.getStorageDomainNamesForType(
            datacenter_name=self.dc_0, storage_type=conf.STORAGE_TYPE
        )[0]
        self.ie_vm = conf.IE_VM
        self.ie_template = conf.IE_TEMPLATE
        self.export_domain = conf.EXPORT_DOMAIN_NAME
        self.more_then_once_vm = conf.IMP_MORE_THAN_ONCE_VM
        self.more_then_once_template = conf.IMP_MORE_THAN_ONCE_TEMP


@pytest.fixture(scope="module")
def import_export_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    ieex = ImportExport()

    def fin3():
        """
        Finalizer for remove networks from setup
        """
        ieex.remove_networks_from_setup(hosts=ieex.host_0_name)

    def fin2():
        """
        Finalizer for remove template from export domain
        """
        ll_templates.removeTemplateFromExportDomain(
            positive=True, template=ieex.ie_template, datacenter=ieex.dc_0,
            export_storagedomain=ieex.export_domain
        )

    def fin1():
        """
        Finalizer for remove VM from export domain
        """
        ll_vms.remove_vm_from_export_domain(
            positive=True, vm=ieex.ie_vm, datacenter=ieex.dc_0,
            export_storagedomain=ieex.export_domain
        )

    assert ll_vms.createVm(
        positive=True, vmName=ieex.ie_vm, vmDescription="",
        cluster=ieex.cluster_0, storageDomainName=im_ex_conf.SD_NAME,
        size=conf.VM_DISK_SIZE
    )

    assert hl_networks.createAndAttachNetworkSN(
        data_center=ieex.dc_0, cluster=ieex.cluster_0,
        host=ieex.vds_0_host, network_dict=im_ex_conf.LOCAL_DICT,
        auto_nics=[0, 3]
    )

    net_list = [ieex.mgmt_bridge] + im_ex_conf.NETS[:3] + [None]
    helper.add_nics_to_vm(net_list=net_list)

    assert ll_templates.createTemplate(
        positive=True, vm=ieex.ie_vm, cluster=ieex.cluster_0,
        name=ieex.ie_template
    )
    assert ll_templates.exportTemplate(
        positive=True, template=ieex.ie_template,
        storagedomain=ieex.export_domain
    )

    assert ll_vms.exportVm(
        positive=True, vm=ieex.ie_vm, storagedomain=ieex.export_domain
    )
    assert ll_vms.removeVm(positive=True, vm=ieex.ie_vm, stopVM="true")

    assert ll_templates.removeTemplate(
        positive=True, template=ieex.ie_template
    )


@pytest.fixture(scope="class")
def fixture_case_01(request, import_export_prepare_setup):
    """
    Fixture for case01
    """
    ieex = ImportExport()
    vms_list = [ieex.ie_vm, ieex.more_then_once_vm]
    net1 = im_ex_conf.NETS[0]
    net2 = im_ex_conf.NETS[1]

    def fin():
        """
        Finalizer for remove VMs
        """
        ll_vms.safely_remove_vms(vms=vms_list)
    request.addfinalizer(fin)

    for name in (None, vms_list[1]):
        assert ll_vms.importVm(
            positive=True, vm=ieex.ie_vm,
            export_storagedomain=ieex.export_domain,
            import_storagedomain=im_ex_conf.SD_NAME, cluster=ieex.cluster_0,
            name=name
        )


@pytest.fixture(scope="class")
def fixture_case_02(request, import_export_prepare_setup):
    """
    Fixture for case02
    """
    ieex = ImportExport()
    template_list = [ieex.more_then_once_template, ieex.ie_template]

    def fin():
        """
        Finalizer for remove templates
        """
        ll_templates.removeTemplates(positive=True, templates=template_list)
    request.addfinalizer(fin)

    for name in (None, template_list[0]):
        assert ll_templates.import_template(
            positive=True, template=ieex.ie_template,
            source_storage_domain=ieex.export_domain,
            destination_storage_domain=im_ex_conf.SD_NAME,
            cluster=ieex.cluster_0, name=name
        )


@pytest.fixture(scope="class")
def fixture_case_03(request, import_export_prepare_setup):
    """
    Fixture for case03
    """
    ieex = ImportExport()
    vms_list = [ieex.ie_vm, "IE_VM_2"]
    net_list = im_ex_conf.NETS
    net1 = im_ex_conf.NETS[0]
    net2 = im_ex_conf.NETS[1]

    def fin():
        """
        Finalizer for remove VMs, template and remove networks
        """
        dc_dict1 = {
            net1: {
                "nic": 1,
                "required": "false"
            },
            net2: {
                "mtu": conf.MTU[0],
                "nic": 2,
                "required": "false"
            }
        }

        ll_vms.safely_remove_vms(vms=vms_list)
        ll_templates.removeTemplate(positive=True, template=ieex.ie_template)
        networking_helper.prepare_networks_on_setup(
            networks_dict=dc_dict1, dc=ieex.dc_0,
            cluster=ieex.cluster_0
        )

        hl_networks.createAndAttachNetworkSN(
            host=ieex.vds_0_host, network_dict=im_ex_conf.LOCAL_DICT,
            auto_nics=[0, 3]
        )
    request.addfinalizer(fin)

    assert hl_host_network.remove_networks_from_host(
        host_name=ieex.host_0_name, networks=net_list[:3]
    )
    assert hl_networks.remove_networks(
        positive=True, networks=net_list[:2]
    )
    assert ll_templates.import_template(
        positive=True, template=ieex.ie_template,
        source_storage_domain=ieex.export_domain,
        destination_storage_domain=im_ex_conf.SD_NAME,
        cluster=ieex.cluster_0
    )
    assert ll_vms.importVm(
        positive=True, vm=vms_list[0],
        export_storagedomain=ieex.export_domain,
        import_storagedomain=im_ex_conf.SD_NAME, cluster=ieex.cluster_0
    )
