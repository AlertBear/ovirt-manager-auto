#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MAC pool per DC test cases
"""
import pytest

import art.rhevm_api.resources.storage as storage_rsc
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as mac_pool_conf
import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests import networking
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def mac_pool_per_dc_prepare_setup(request):
    """
    Prepare environment for MAC pool per DC tests:

    1.  Create extra DC, extra cluster and custom MAC pool
    2.  Move host_1 to the new cluster
    3.  Add NFS storage to DC
    4.  Create a new VM on the new DC which attached to the new cluster
    5.  Create VM template with the custom MAC pool
    """
    mac_pool = NetworkFixtures()

    def fin8():
        """
        Clean NFS mount points from host
        """
        testflow.teardown("Clean host: %s mount points", mac_pool.host_1_name)
        assert storage_rsc.clean_mount_point(
            host=mac_pool.host_1_name,
            src_ip=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0],
            src_path=conf.UNUSED_DATA_DOMAIN_PATHS[0],
            opts=global_helper.NFS_MNT_OPTS
        )
    request.addfinalizer(fin8)

    @networking.ignore_exception
    def fin7():
        """
        Remove storage domain
        """
        testflow.teardown(
            "Removing host: %s storage domain", mac_pool.host_1_name
        )
        ll_storagedomains.removeStorageDomain(
            positive=True, storagedomain=mac_pool_conf.MP_STORAGE,
            host=mac_pool.host_1_name, force=True
        )
    request.addfinalizer(fin7)

    def fin6():
        """
        Remove non-default MAC pools
        """
        testflow.teardown("Removing unneeded MAC pools")
        networking.remove_unneeded_mac_pools()
    request.addfinalizer(fin6)

    def fin5():
        """
        Set default MAC pools for DCs
        """
        testflow.teardown("Setting default MAC pools for DCs")
        curr_mac_pool_values = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_mac_pool(pool_name=mac_pool_conf.DEFAULT_MAC_POOL)
        )
        if not curr_mac_pool_values == mac_pool_conf.DEFAULT_MAC_POOL_VALUES:
            assert hl_mac_pool.update_default_mac_pool()
    request.addfinalizer(fin5)

    def fin4():
        """
        Remove cluster
        """
        testflow.teardown("Removing cluster: %s", mac_pool_conf.MAC_POOL_CL)
        assert ll_clusters.removeCluster(
            positive=True, cluster=mac_pool_conf.MAC_POOL_CL
        )
    request.addfinalizer(fin4)

    def fin3():
        """
        Remove Data-Center (removes storage also)
        """
        testflow.teardown("Removing DC: %s", mac_pool_conf.EXT_DC_0)
        assert ll_dc.remove_datacenter(
            positive=True, datacenter=mac_pool_conf.EXT_DC_0, force=True
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Move host to original cluster
        """
        testflow.teardown(
            "Moving host: %s to cluster: %s", mac_pool.host_1_name, conf.CL_0
        )
        assert hl_hosts.move_host_to_another_cluster(
            host=mac_pool.host_1_name, cluster=conf.CL_0
        )
    request.addfinalizer(fin2)

    @global_helper.wait_for_jobs_deco(["Removing VM"])
    def fin1():
        """
        Remove VM
        """
        testflow.teardown("Removing VM: %s", mac_pool_conf.MP_VM_0)
        assert ll_vms.removeVm(positive=True, vm=mac_pool_conf.MP_VM_0)
    request.addfinalizer(fin1)

    testflow.setup("Creating basic setup")
    assert hl_networks.create_basic_setup(
        datacenter=mac_pool_conf.EXT_DC_0, version=conf.COMP_VERSION,
        cluster=mac_pool_conf.MAC_POOL_CL, cpu=conf.CPU_NAME
    )
    testflow.setup(
        "Moving host: %s to cluster: %s", mac_pool.host_1_name,
        mac_pool_conf.MAC_POOL_CL
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=conf.HOST_1_NAME, cluster=mac_pool_conf.MAC_POOL_CL
    )
    testflow.setup(
        "Add NFS storage domain: %s to host: %s", mac_pool_conf.MP_STORAGE,
        mac_pool.host_1_name
    )
    assert hl_storagedomains.addNFSDomain(
        host=mac_pool.host_1_name, storage=mac_pool_conf.MP_STORAGE,
        data_center=mac_pool_conf.EXT_DC_0,
        path=conf.UNUSED_DATA_DOMAIN_PATHS[0],
        address=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]
    )
    testflow.setup("Create new VM: %s", mac_pool_conf.MP_VM_0)
    assert ll_vms.createVm(
        positive=True, vmName=mac_pool_conf.MP_VM_0,
        cluster=mac_pool_conf.MAC_POOL_CL, provisioned_size=conf.VM_DISK_SIZE,
        storageDomainName=mac_pool_conf.MP_STORAGE
    )
    testflow.setup("Create new template: %s", mac_pool_conf.MP_TEMPLATE)
    assert ll_templates.createTemplate(
        positive=True, vm=mac_pool_conf.MP_VM_0,
        cluster=mac_pool_conf.MAC_POOL_CL, name=mac_pool_conf.MP_TEMPLATE
    )


@pytest.fixture(scope="class")
def create_mac_pools(request):
    """
    Create MAC pool(s)
    """
    pools = getattr(request.cls, "create_mac_pools_params", dict())

    def fin():
        """
        Remove MAC pool(s)
        """
        for pool_name in pools.keys():
            testflow.teardown("Removing MAC pool: %s", pool_name)
            ll_mac_pool.remove_mac_pool(mac_pool_name=pool_name)
    request.addfinalizer(fin)

    for pool_name, params in pools.iteritems():
        if params:
            testflow.setup("Creating MAC pool: %s", pool_name)
            assert ll_mac_pool.create_mac_pool(
                name=pool_name, ranges=params[0], allow_duplicates=params[1]
            )


@pytest.fixture(scope="class")
def create_dc_with_mac_pools(request):
    """
    Create a new Data-Center(s) with a specified name, version, MAC pool name
        and MAC pool range(s)
    """
    mac_pools = getattr(request.cls, "create_dc_with_mac_pools_params", dict())

    def fin():
        """
        Remove Data-Center
        """
        for dc, params in mac_pools.iteritems():
            if params[1]:
                testflow.teardown("Removing DC: %s", dc)
                assert ll_dc.remove_datacenter(positive=True, datacenter=dc)
    request.addfinalizer(fin)

    for dc, params in mac_pools.iteritems():
        testflow.setup("Creating DC: %s with MAC pool: %s ", dc, params[0])
        assert helper.create_dc_with_mac_pool(
            dc_name=dc, mac_pool_name=params[0]
        )


@pytest.fixture(scope="class")
def update_dcs_mac_pool(request):
    """
    Update Data-Center(s) to contain MAC pool
    """
    dcs_pools = getattr(request.cls, "update_dcs_mac_pool_params", dict())

    def fin():
        """
        Set Data-Center(s) MAC pool to default
        """
        default = mac_pool_conf.DEFAULT_MAC_POOL
        for dc_name in dcs_pools.iterkeys():
            testflow.teardown(
                "Updating DC: %s MAC pool to default: %s", dc_name, default
            )
            assert ll_dc.update_datacenter(
                positive=True, datacenter=dc_name,
                mac_pool=ll_mac_pool.get_mac_pool(pool_name=default)
            )
    request.addfinalizer(fin)

    for dc_name, pool_name in dcs_pools.iteritems():
        testflow.setup("Updating DC: %s MAC pool to: %s", dc_name, pool_name)
        assert ll_dc.update_datacenter(
            positive=True, datacenter=dc_name,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=pool_name)
        )


@pytest.fixture(scope="class")
def remove_vnics_from_vms(request):
    """
    Remove vNIC(s) from a VM
    """
    vms_vnics = getattr(request.cls, "remove_vnics_from_vms_params", dict())

    def fin():
        for vm, vnics in vms_vnics.iteritems():
            for vnic in vnics:
                testflow.teardown("Removing vNIC: %s from VM: %s", vnic, vm)
                ll_vms.removeNic(positive=True, vm=vm, nic=vnic)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def add_vnics_to_vm(request, remove_vnics_from_vms):
    """
    Add vNIC(s) to VM
    """
    vms_vnics = getattr(request.cls, "add_vnics_to_vm_params", dict())

    for vm_name, vnics in vms_vnics.iteritems():
        for vnic in vnics:
            testflow.setup("Adding vNIC: %s to VM: %s", vnic, vm_name)
            assert ll_vms.addNic(positive=True, vm=vm_name, name=vnic)


@pytest.fixture(scope="class")
def remove_non_default_mac_pool(request):
    """
    Remove all non-default MAC pools
    """
    def fin():
        testflow.teardown("Removing unneeded MAC pools")
        networking.remove_unneeded_mac_pools()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def add_vnics_to_template(request):
    """
    Add vNIC(s) to template(s)
    """
    vnic_temp = getattr(request.cls, "add_vnics_to_template_params", dict())

    def fin():
        """
        Remove template(s)
        """
        for temp in vnic_temp.iterkeys():
            testflow.teardown("Removing template: %s", temp)
            assert ll_templates.removeTemplate(positive=True, template=temp)
    request.addfinalizer(fin)

    for temp, vnics in vnic_temp.iteritems():
        for vnic in vnics:
            testflow.setup("Adding vNIC: %s to template: %s", vnic, temp)
            assert ll_templates.addTemplateNic(
                positive=True, template=temp, name=vnic
            )


@pytest.fixture(scope="class")
def create_vm_from_template(request):
    """
    Create VM(s) from template(s)
    """
    mac_pool = NetworkFixtures()
    vms_templates = getattr(
        request.cls, "create_vm_from_template_params", dict()
    )
    cluster = mac_pool_conf.MAC_POOL_CL

    def fin():
        """
        Remove VM(s)
        """
        for vm in vms_templates.iterkeys():
            testflow.teardown("Removing VM: %s", vm)
            assert ll_vms.removeVm(positive=True, vm=vm)
    request.addfinalizer(fin)

    for vm, template in vms_templates.iteritems():
        testflow.setup("Creating VM: %s from template: %s", vm, template)
        assert ll_vms.createVm(
            positive=True, vmName=vm, template=template, cluster=cluster,
            network=mac_pool.mgmt_bridge
        )
