#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for register domain test
"""
import pytest
from utilities import utils

from art.rhevm_api.tests_lib.high_level import (
    mac_pool as hl_mac_pool,
    networks as hl_networks,
    storagedomains as hl_storage
)
from art.rhevm_api.tests_lib.low_level import (
    mac_pool as ll_mac_pool,
    storagedomains as ll_storage,
    vms as ll_vms,
    templates as ll_templates
)
import config as register_domain_conf
import helper
from art.unittest_lib import testflow
from rhevmtests.networking import helper as network_helper, config as conf


@pytest.fixture(scope="module", autouse=True)
def prepare_setup(request):
    """
    Add storage domain to setup
    Create 8 VMS
    """
    storage_name = register_domain_conf.EXTRA_SD_NAME
    storage_address = conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]
    storage_path = conf.UNUSED_DATA_DOMAIN_PATHS[0]
    dc = conf.DC_0
    host = conf.HOST_0_NAME

    def fin3():
        """
        Remove networks from engine
        """
        assert hl_networks.remove_net_from_setup(
            host=[host], all_net=True,
            data_center=dc
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove storage domain from setup
        """
        testflow.teardown(
            "Remove storage domain %s from DC %s", storage_name, dc
        )
        assert hl_storage.remove_storage_domain(
            name=storage_name, datacenter=dc, host=host, format_disk=True,
            engine=conf.ENGINE
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove all created VMs from engine
        """
        testflow.teardown("Remove all VMs from engine")
        network_helper.remove_unneeded_vms()
    request.addfinalizer(fin1)

    assert hl_networks.create_and_attach_networks(
        data_center=dc, clusters=[conf.CL_0],
        networks=register_domain_conf.NETS_DICT
    )

    testflow.setup("Add NFS storage domain %s to DC %s", storage_name, dc)
    assert hl_storage.addNFSDomain(
        host=host, storage=storage_name, data_center=dc,
        address=storage_address, path=storage_path
    )
    helper.create_vms()
    helper.create_templates()
    testflow.setup(
        "Remove storage domain %s from DC %s", storage_name, dc
    )
    assert hl_storage.remove_storage_domain(
        name=storage_name, datacenter=dc, host=host, engine=conf.ENGINE
    )

    vms_to_remove = register_domain_conf.VMS_DICT.keys()
    templates_to_remove = register_domain_conf.TEMPLATES_DICT.keys()
    testflow.setup("Remove VMs: %s", vms_to_remove)
    assert ll_vms.safely_remove_vms(vms=vms_to_remove)
    testflow.setup("Remove templates: %s", templates_to_remove)
    assert ll_templates.remove_templates(
        positive=True, templates=templates_to_remove
    )

    vms_to_recreate = []
    for i in range(4, 7):
        vm_to_recreate_index = register_domain_conf.VMS_DICT.keys().index(
            register_domain_conf.VM_NAMES[i][0]
        )
        vms_to_recreate.append(
            register_domain_conf.VMS_DICT.keys()[vm_to_recreate_index]
        )

    helper.create_vms(vms_to_recreate=vms_to_recreate)
    nets_to_remove = [
        register_domain_conf.NETS[2][0], register_domain_conf.NETS[3][0]
    ]
    assert hl_networks.remove_networks(positive=True, networks=nets_to_remove)

    testflow.setup("Import storage domain %s into DC %s", storage_name, dc)
    assert ll_storage.importStorageDomain(
        positive=True, type=conf.ENUMS['storage_dom_type_data'],
        storage_type=conf.STORAGE_TYPE_NFS, address=storage_address,
        path=storage_path, host=host
    )
    assert ll_storage.attachStorageDomain(
        positive=True, datacenter=dc, storagedomain=storage_name
    )


@pytest.fixture(scope="class")
def import_vm_from_data_domain(request):
    """
    Import VM from data domain
    """
    data_domain_name = request.node.cls.data_domain_name
    vm = request.node.cls.vm
    reassessing_mac = getattr(request.node.cls, "reassessing_mac", True)
    network_mappings = getattr(request.node.cls, "network_mappings", list())
    unregistered_vms = ll_storage.get_unregistered_vms(
        storage_domain=data_domain_name
    )
    vm_to_import = [i for i in unregistered_vms if i.name == vm]
    assert vm_to_import

    def fin():
        """
        Remove imported VM
        """
        testflow.teardown("Remove VM %s", vm_to_import.name)
        assert ll_vms.safely_remove_vms(vms=[vm_to_import.name])
    request.addfinalizer(fin)

    vm_to_import = vm_to_import[0]
    testflow.setup(
        "Import VM %s from data domain %s with: reassessing_mac=%s, "
        "network_mapping=%s",
        vm, data_domain_name, reassessing_mac, network_mappings
    )
    assert ll_storage.register_object(
        obj=vm_to_import, cluster=conf.CL_0,
        network_mappings=network_mappings, reassign_bad_macs=reassessing_mac
    )


@pytest.fixture()
def import_templates_from_data_domain(request):
    """
    Import template from data domain
    """
    data_domain_name = request.node.cls.data_domain_name
    network_mappings = request.getfixturevalue("mappings")
    template = request.getfixturevalue("template")
    unregistered_templates = ll_storage.get_unregistered_templates(
        storage_domain=data_domain_name
    )
    template_object = [
        temp for temp in unregistered_templates if temp.name == template
    ]
    assert template_object
    template_object = template_object[0]

    def fin():
        """
        Remove imported templates
        """
        testflow.teardown("Remove template %s", template)
        assert ll_templates.remove_template(positive=True, template=template)
    request.addfinalizer(fin)

    testflow.setup(
        "Import template %s from data domain %s with: network_mapping=%s",
        template, data_domain_name, network_mappings or "N/A"
    )
    assert ll_storage.register_object(
        obj=template_object, cluster=conf.CL_0,
        network_mappings=network_mappings
    )


@pytest.fixture(scope="class")
def set_allow_duplicate_mac_pool(request):
    """
    Set allow duplicate flag into the MAC pool
    """
    def fin():
        """
        Disable allow duplicate flag into the MAC pool
        """
        testflow.teardown("Set allow_duplicates=False on MAC pool %s")
        ll_mac_pool.update_mac_pool(
            mac_pool_name="Default", allow_duplicates=False
        )
    request.addfinalizer(fin)

    testflow.setup("Set allow_duplicates=True on MAC pool %s")
    ll_mac_pool.update_mac_pool(mac_pool_name="Default", allow_duplicates=True)


@pytest.fixture(scope="class")
def manage_mac_pool_range(request):
    """
    Resize MAC pool range
    """
    mac_pool_name = "Default"

    def fin():
        """
        Restore default MAC pool ranges
        """
        testflow.teardown("Restore default MAC pool range")
        assert hl_mac_pool.update_default_mac_pool()
    request.addfinalizer(fin)

    mac_pool = ll_mac_pool.get_mac_pool(mac_pool_name)
    orig_start_range, orig_end_range = ll_mac_pool.get_mac_range_values(
        mac_pool
    )[0]
    end_range = orig_end_range.replace(
        orig_end_range.split(":")[-1], orig_start_range.split(":")[-1]
    )
    low_mac = utils.MAC(orig_start_range)
    high_mac = utils.MAC(end_range)
    testflow.setup("Resize Default MAC pool to have 2 MACs")
    assert hl_mac_pool.update_ranges_on_mac_pool(
        mac_pool_name=mac_pool_name, range_dict={
            (orig_start_range, orig_end_range): (low_mac, high_mac)
        }
    )


@pytest.fixture(scope="class")
def make_sure_no_mac_in_pool(request):
    """
    Create vNICs until all MACs in pool are used
    """
    vm = conf.VM_0
    vnics = ["register_domain_network_vnic_%d" % i for i in range(11)]
    vnics_to_remove = list()

    def fin():
        """
        Remove vNICs from VM
        """
        for vnic in vnics_to_remove:
            testflow.teardown("Remove vNIC %s from VM %s", vnic, vm)
            ll_vms.removeNic(positive=True, vm=vm, nic=vnic)
    request.addfinalizer(fin)

    for vnic in vnics:
        testflow.setup("Add vNIC %s to VM %s", vnic, vm)
        if ll_vms.addNic(positive=False, vm=vm, name=vnic):
            break
        vnics_to_remove.append(vnic)
