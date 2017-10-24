"""
Quota test fixtures
"""
import pytest

import art.rhevm_api.tests_lib.high_level.disks as hl_disks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers


@pytest.fixture(scope="class")
def update_quota_cluster_hard_limit(request):
    """
    1) Update the quota cluster hard limit
    """
    quota_cluster_hard_limit = request.node.cls.quota_cluster_hard_limit

    if quota_cluster_hard_limit:
        def fin():
            """
            1) Update the quota cluster hard limit to 20
            """
            u_libs.testflow.teardown(
                "Update quota %s cluster grace value to 20", conf.QUOTA_NAME
            )
            ll_datacenters.update_dc_quota(
                dc_name=conf.DC_NAME[0],
                quota_name=conf.QUOTA_NAME,
                cluster_hard_limit_pct=20
            )
        request.addfinalizer(fin)

        u_libs.testflow.setup(
            "Update quota %s cluster grace value", conf.QUOTA_NAME
        )
        assert ll_datacenters.update_dc_quota(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA_NAME,
            cluster_hard_limit_pct=quota_cluster_hard_limit
        )


@pytest.fixture(scope="class")
def create_quota_limits(request):
    """
    1) Create cluster and storage limits on the quota
    """
    quota_limits = request.node.cls.quota_limits
    cluster_limit = quota_limits.get(conf.QUOTA_CLUSTER_LIMIT)
    storage_limit = quota_limits.get(conf.QUOTA_STORAGE_LIMIT)

    def fin():
        """
        1) Remove cluster and storage limits from the quota
        """
        quota_limits_d = {
            conf.LIMIT_TYPE_CLUSTER: cluster_limit,
            conf.LIMIT_TYPE_STORAGE: storage_limit
        }
        for limit_type, limits in quota_limits_d.iteritems():
            if limits:
                u_libs.testflow.teardown(
                    "Delete the limit %s on the quota %s",
                    limit_type, conf.QUOTA_NAME
                )
                ll_datacenters.delete_quota_limits(
                    dc_name=conf.DC_NAME[0],
                    quota_name=conf.QUOTA_NAME,
                    limit_type=limit_type,
                    objects_names_l=[None]
                )
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Create cluster %s and storage %s limits on quota %s",
        cluster_limit, storage_limit, conf.QUOTA_NAME
    )
    assert helpers.create_quota_limits(
        dc_name=conf.DC_NAME[0],
        quota_name=conf.QUOTA_NAME,
        quota_cluster_limit=cluster_limit,
        quota_storage_limit=storage_limit
    )


@pytest.fixture()
def stop_and_update_vm_cpus_and_memory(request):
    """
    1) Stop the VM
    2) Update VM number of CPU's and memory
    """
    def fin():
        u_libs.testflow.teardown("Stop the VM %s", conf.VM_NAME)
        ll_vms.stop_vms_safely(vms_list=[conf.VM_NAME])
        u_libs.testflow.teardown(
            "Update the VM %s", conf.VM_NAME
        )
        ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME,
            cpu_socket=1,
            cpu_cores=1,
            memory=conf.SIZE_512_MB,
            memory_guaranteed=conf.SIZE_512_MB
        )
    request.addfinalizer(fin)


@pytest.fixture()
def remove_additional_disk(request):
    """
    1) Remove additional disk
    """
    def fin():
        u_libs.testflow.teardown(
            "Check if the disk %s exists", conf.DISK_NAME
        )
        if ll_disks.checkDiskExists(positive=True, disk=conf.DISK_NAME):
            u_libs.testflow.teardown("Delete the disk %s", conf.DISK_NAME)
            hl_disks.delete_disks(disks_names=[conf.DISK_NAME])
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_vm_snapshot(request):
    """
    1) Create VM snapshot
    """
    def fin():
        u_libs.testflow.teardown(
            "Remove snapshot %s from VM %s", conf.VM_SNAPSHOT, conf.VM_NAME
        )
        ll_vms.removeSnapshot(
            positive=True, vm=conf.VM_NAME, description=conf.VM_SNAPSHOT
        )
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Add snapshot %s to VM %s", conf.VM_SNAPSHOT, conf.VM_NAME
    )
    assert ll_vms.addSnapshot(
        positive=True, vm=conf.VM_NAME, description=conf.VM_SNAPSHOT
    )
