#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MAC pool per DC test cases
"""
import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
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
def mac_pool_per_cl_prepare_setup(request):
    """
    Prepare environment for MAC pool per cluster tests:

    1.  Create extra DC, extra cluster and custom MAC pool
    2.  Move host_1 to the new cluster
    3.  Add NFS storage to DC
    4.  Create a new VM on the new DC which attached to the new cluster
    5.  Create VM template with the custom MAC pool
    """
    mac_pool = NetworkFixtures()
    template = mac_pool_conf.MP_TEMPLATE
    vm = mac_pool_conf.MP_VM_0
    cluster = mac_pool_conf.MAC_POOL_CL

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
        testflow.teardown("Setting default MAC pools")
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
        testflow.teardown("Removing cluster: %s", cluster)
        assert ll_clusters.removeCluster(positive=True, cluster=cluster)
    request.addfinalizer(fin4)

    def fin3():
        """
        Move host to original cluster
        """
        assert hl_hosts.move_host_to_another_cluster(
            host=mac_pool.host_1_name, cluster=conf.CL_0,
            host_resource=mac_pool.vds_1_host
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove template
        """
        testflow.teardown("Remove template %s", template)
        assert ll_templates.remove_template(positive=True, template=template)
    request.addfinalizer(fin2)

    @global_helper.wait_for_jobs_deco(["Removing VM"])
    def fin1():
        """
        Remove VM
        """
        testflow.teardown("Removing VM: %s", vm)
        assert ll_vms.removeVm(positive=True, vm=vm)
    request.addfinalizer(fin1)

    testflow.setup(
        "Add cluster %s to datacenter %s", cluster, mac_pool.dc_0
    )
    assert ll_clusters.addCluster(
        positive=True, data_center=mac_pool.dc_0, cpu=conf.CPU_NAME,
        name=cluster,
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=conf.HOST_1_NAME, cluster=cluster,
        host_resource=mac_pool.vds_1_host
    )
    testflow.setup("Create new VM: %s", vm)
    assert ll_vms.createVm(
        positive=True, vmName=vm, cluster=cluster,
        provisioned_size=conf.VM_DISK_SIZE,
        storageDomainName=conf.STORAGE_NAME[0]
    )
    testflow.setup("Create new template: %s", template)
    assert ll_templates.createTemplate(
        positive=True, vm=vm, cluster=cluster, name=template
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
        testflow.teardown("Removing unneeded MAC pools")
        networking.remove_unneeded_mac_pools()
    request.addfinalizer(fin)

    for pool_name, params in pools.iteritems():
        if params:
            testflow.setup("Creating MAC pool: %s", pool_name)
            assert ll_mac_pool.create_mac_pool(
                name=pool_name, ranges=params[0], allow_duplicates=params[1]
            )


@pytest.fixture(scope="class")
def create_cluster_with_mac_pools(request):
    """
    Create a new cluster(s) with a specified name, version, MAC pool name
        and MAC pool range(s)
    """
    mac_pools = getattr(request.cls, "create_cl_with_mac_pools_params", dict())

    def fin():
        """
        Remove clusters
        """
        for cl, params in mac_pools.iteritems():
            if params[1]:
                testflow.teardown("Removing cluster: %s", cl)
                assert ll_clusters.removeCluster(positive=True, cluster=cl)
    request.addfinalizer(fin)

    for cl, params in mac_pools.iteritems():
        testflow.setup(
            "Creating cluster: %s with MAC pool: %s ", cl, params[0]
        )
        assert helper.create_cluster_with_mac_pool(
            cluster_name=cl, mac_pool_name=params[0]
        )


@pytest.fixture(scope="class")
def update_clusters_mac_pool(request):
    """
    Update Data-Center(s) to contain MAC pool
    """
    cls_pools = getattr(request.cls, "update_cls_mac_pool_params", dict())

    def fin():
        """
        Set Data-Center(s) MAC pool to default
        """
        default = mac_pool_conf.DEFAULT_MAC_POOL
        for cl_name in cls_pools.iterkeys():
            testflow.teardown(
                "Updating cluster: %s MAC pool to default: %s", cl_name,
                default
            )
            assert ll_clusters.updateCluster(
                positive=True, cluster=cl_name,
                mac_pool=ll_mac_pool.get_mac_pool(pool_name=default)
            )
    request.addfinalizer(fin)

    for cl_name, pool_name in cls_pools.iteritems():
        testflow.setup(
            "Updating cluster: %s MAC pool to: %s", cl_name, pool_name
        )
        assert ll_clusters.updateCluster(
            positive=True, cluster=cl_name,
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
