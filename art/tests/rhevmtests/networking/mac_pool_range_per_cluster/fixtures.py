#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MAC pool per DC test cases
"""
import pytest

import config as mac_pool_conf
import helper
import rhevmtests.config as global_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
    mac_pool as hl_mac_pool
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    mac_pool as ll_mac_pool,
    templates as ll_templates,
    vms as ll_vms
)
from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow


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
    template = mac_pool_conf.MP_TEMPLATE
    vms = mac_pool_conf.MP_VMS_NAMES[:2]
    cluster = mac_pool_conf.MAC_POOL_CL
    results = []

    def fin7():
        """
        Check finalizers results
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin7)

    def fin6():
        """
        Remove non-default MAC pools
        """
        testflow.teardown("Removing non-default MAC pools")
        results.append(
            (
                helper.remove_non_default_mac_pools(),
                "Failed to remove non-default MAC pools"
            )
        )
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
            results.append(
                (
                    hl_mac_pool.update_default_mac_pool(),
                    "Failed to revert default MAC pools"
                )
            )
    request.addfinalizer(fin5)

    def fin4():
        """
        Remove cluster
        """
        results.append(
            (
                ll_clusters.removeCluster(positive=True, cluster=cluster),
                "Failed to remove cluster: %s" % cluster
            )
        )
    request.addfinalizer(fin4)

    def fin3():
        """
        Move host to original cluster
        """
        results.append(
            (
                hl_hosts.move_host_to_another_cluster(
                    host=conf.HOST_1_NAME, cluster=conf.CL_0,
                    host_resource=conf.VDS_1_HOST
                ), "Failed to move host: %s to cluster: %s"
                % (conf.HOST_1_NAME, conf.CL_0)
            )
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove template
        """
        testflow.teardown("Remove template %s", template)
        results.append(
            (
                ll_templates.remove_template(positive=True, template=template),
                "Failed to remove template: %s" % template
            )
        )
    request.addfinalizer(fin2)

    @global_helper.wait_for_jobs_deco([global_conf.JOB_REMOVE_VM])
    def fin1():
        """
        Remove VM
        """
        for vm in vms:
            testflow.teardown("Removing VM: %s", vm)
            results.append(
                (
                    ll_vms.removeVm(positive=True, vm=vm),
                    "Failed to remove VM: %s" % vm
                )
            )
    request.addfinalizer(fin1)

    testflow.setup(
        "Add cluster %s to datacenter %s", cluster, conf.DC_0
    )
    assert ll_clusters.addCluster(
        positive=True, data_center=conf.DC_0, cpu=conf.CPU_NAME,
        name=cluster
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=conf.HOST_1_NAME, cluster=cluster,
        host_resource=conf.VDS_1_HOST
    )
    for vm in vms:
        testflow.setup("Creating new VM: %s", vm)
        assert ll_vms.createVm(
            positive=True, vmName=vm, cluster=cluster,
            template=conf.TEMPLATE_NAME[0]
        )
        # VMs created by the default template have vNIC with MAC allocated from
        # the default MAC pool.
        # In order to avoid confusion with the test pools, remove the default
        # vNIC.
        assert ll_vms.removeNic(positive=True, vm=vm, nic=conf.VM_NIC_0)
    testflow.setup("Create new template: %s", template)
    assert ll_templates.createTemplate(
        positive=True, vm=mac_pool_conf.MP_VM_0, cluster=cluster, name=template
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
        assert helper.remove_non_default_mac_pools()
    request.addfinalizer(fin)

    for pool_name, params in pools.items():
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
        results = []
        for cl, params in mac_pools.items():
            if params[1]:
                results.append(
                    (
                        ll_clusters.removeCluster(positive=True, cluster=cl),
                        "Failed to remove cluster: %s" % cl
                    )
                )
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin)

    for cluster, params in mac_pools.items():
        testflow.setup(
            "Creating cluster: %s with MAC pool: %s ", cluster, params[0]
        )
        assert helper.create_cluster_with_mac_pool(
            cluster_name=cluster, mac_pool_name=params[0]
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
        results = []

        for cl in cls_pools.keys():
            mac_pool = ll_mac_pool.get_mac_pool(pool_name=default)
            testflow.teardown(
                "Updating cluster: %s MAC pool to default: %s", cl,
                default
            )
            results.append(
                (
                    ll_clusters.updateCluster(
                        positive=True, cluster=cl, mac_pool=mac_pool
                    ),
                    "Failed to update cluster: %s MAC pool: %s "
                    % (cl, mac_pool)
                )
            )
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin)

    for cl_name, pool_name in cls_pools.items():
        testflow.setup(
            "Updating cluster: %s MAC pool to: %s", cl_name, pool_name
        )
        assert ll_clusters.updateCluster(
            positive=True, cluster=cl_name,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=pool_name)
        )


@pytest.fixture(scope="class")
def add_vnics_to_template(request):
    """
    Add vNIC(s) to template(s)
    """
    vnics_to_add = getattr(request.cls, "add_vnics_to_template_params", dict())
    vnics_to_remove = vnics_to_add

    def fin():
        """
        Remove vNIC(s) from template
        """
        results = []

        for template, vnics in vnics_to_remove.items():
            for vnic in vnics:
                testflow.teardown(
                    "Removing vNIC: %s from template: %s", vnic, template
                )
                results.append(
                    (
                        ll_templates.removeTemplateNic(
                            positive=True, template=template, nic=vnic
                        ), (
                            "Failed to remove vNIC: %s from template: %s"
                            % (vnic, template)
                        )
                    )
                )
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin)

    for template, vnics_to_add in vnics_to_add.items():
        for vnic in vnics_to_add:
            testflow.setup("Adding vNIC: %s to template: %s", vnic, template)
            assert ll_templates.addTemplateNic(
                positive=True, template=template, name=vnic
            )


@pytest.fixture(scope="class")
def create_vm_from_template(request):
    """
    Create VM(s) from template(s)
    """
    vms_templates = getattr(
        request.cls, "create_vm_from_template_params", dict()
    )
    cluster = mac_pool_conf.MAC_POOL_CL

    def fin():
        """
        Remove VM(s)
        """
        for vm in vms_templates.keys():
            testflow.teardown("Removing VM: %s", vm)
            assert ll_vms.removeVm(positive=True, vm=vm)
    request.addfinalizer(fin)

    for vm, template in vms_templates.items():
        testflow.setup("Creating VM: %s from template: %s", vm, template)
        assert ll_vms.createVm(
            positive=True, vmName=vm, template=template, cluster=cluster,
            network=conf.MGMT_BRIDGE
        )


@pytest.fixture(scope="class")
def set_stateless_vm(request):
    """
    Set stateless mode on VM
    """
    vm = request.cls.set_stateless_vm_param

    def fin():
        """
        Remove stateless mode from VM
        """
        assert ll_vms.updateVm(positive=True, vm=vm, stateless=False)

        # In a stateless VM after successful shutdown, snapshot restore
        # operation is created as background job
        assert not test_utils.wait_for_tasks(
            engine=conf.ENGINE, datacenter=conf.DC_0
        )
    request.addfinalizer(fin)

    assert ll_vms.updateVm(positive=True, vm=vm, stateless=True)


@pytest.fixture(scope="class")
def take_vms_snapshot(request):
    """
    Take VM(s) snapshot
    """
    vms_snapshot = request.cls.vms_snapshot

    def fin():
        """
        Delete VM(s) snapshot
        """
        results = []

        for vm, snap_desc in vms_snapshot.items():
            testflow.teardown(
                "Removing snapshot: %s from VM: %s", snap_desc, vm
            )
            results.append(
                (
                    ll_vms.removeSnapshot(
                        positive=True, vm=vm, description=snap_desc
                    ), "Failed to delete snapshot of VM: %s" % vm
                )
            )
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin)

    for vm, snap_desc in vms_snapshot.items():
        assert ll_vms.addSnapshot(positive=True, vm=vm, description=snap_desc)


@pytest.fixture(scope="class")
def undo_snapshot_preview(request):
    """
    Undo VM(s) snapshot preview
    """
    vms_snapshot = request.cls.vms_snapshot

    def fin():
        """
        Undo VM(s) snapshot preview
        """
        results = []

        for vm, snap_desc in vms_snapshot.items():
            if ll_vms.get_snapshot_description_in_preview(vm_name=vm):
                testflow.teardown(
                    "Undoing snapshot: %s of VM: %s", snap_desc, vm
                )
                results.append(
                    (
                        helper.undo_snapshot_and_wait(
                            vm=vm, snapshot_desc=snap_desc
                        ),
                        "Failed to undo snapshot: %s of VM: %s"
                        % (snap_desc, vm)
                    )
                )
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin)
