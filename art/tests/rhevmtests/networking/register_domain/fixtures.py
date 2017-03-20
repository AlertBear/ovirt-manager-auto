#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for register domain test
"""
import pytest
from utilities import utils

import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storage
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storage
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as register_domain_conf
import helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests import networking
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module", autouse=True)
def prepare_setup(request):
    """
    Add storage domain to setup
    Create 8 VMS
    """
    register_domain = NetworkFixtures()
    storage_name = register_domain_conf.EXTRA_SD_NAME
    storage_address = register_domain_conf.EXTRA_SD_ADDRESS
    storage_path = register_domain_conf.EXTRA_SD_PATH
    dc = register_domain.dc_0
    host = register_domain.host_0_name

    def fin3():
        """
        Remove networks from engine
        """
        testflow.teardown("Remove networks %s", register_domain_conf.NETS_DICT)
        assert network_helper.remove_networks_from_setup(hosts=host)
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
        networking.remove_unneeded_vms()
    request.addfinalizer(fin1)

    testflow.setup("Create networks %s", register_domain_conf.NETS_DICT)
    network_helper.prepare_networks_on_setup(
        networks_dict=register_domain_conf.NETS_DICT, dc=register_domain.dc_0,
        cluster=register_domain.cluster_0
    )
    testflow.setup("Add NFS storage domain %s to DC %s", storage_name, dc)
    assert hl_storage.addNFSDomain(
        host=host, storage=storage_name, data_center=dc,
        address=storage_address, path=storage_path
    )
    helper.create_vms()
    testflow.setup(
        "Remove storage domain %s from DC %s", storage_name, dc
    )
    assert hl_storage.remove_storage_domain(
        name=storage_name, datacenter=dc, host=host, engine=conf.ENGINE
    )

    vms_to_remove = register_domain_conf.VMS_DICT.keys()
    testflow.setup("Remove VMs: %s", vms_to_remove)
    assert ll_vms.safely_remove_vms(vms=vms_to_remove)

    vms_to_recreate = list()
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
    testflow.setup("Remove networks %s from setup", nets_to_remove)
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
    register_domain = NetworkFixtures()
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
        obj=vm_to_import, cluster=register_domain.cluster_0,
        network_mappings=network_mappings, reassign_bad_macs=reassessing_mac
    )


@pytest.fixture(scope="class")
def set_allow_duplicate_mac_pool(request):
    """
    Set allow duplicate flag into the MAC pool
    """
    NetworkFixtures()

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
    NetworkFixtures()
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
    register_domain = NetworkFixtures()
    vm = register_domain.vm_0
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
