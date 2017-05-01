import config
import pytest
import shlex
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    clusters as ll_clusters
)
from art.unittest_lib import testflow


@pytest.fixture(scope='class')
def enable_rng_on_vm(request):
    """
    Enable RNG device on VM
    """
    vm_name = request.node.cls.vm_name
    rng_device = request.node.cls.rng_device

    def fin():
        """
        Disable RNG device
        """
        testflow.teardown("Set rng device from VM %s to urandom", vm_name)
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, rng_device=config.URANDOM_RNG
        )
    request.addfinalizer(fin)

    testflow.setup("Set rng device %s on VM %s ", rng_device, vm_name)
    assert ll_vms.updateVm(positive=True, vm=vm_name, rng_device=rng_device)


@pytest.fixture(scope='class')
def update_vm_host(request):
    """
    Update Vm to be pinned to host
    """
    vm_name = request.node.cls.vm_name

    def fin():
        """
        Unpin VM
        """
        testflow.teardown("Update VM %s to be unpin to host", vm_name)
        assert ll_vms.updateVm(
            True, vm_name,
            placement_affinity=config.VM_MIGRATABLE,
            placement_host=config.VM_ANY_HOST
        )

    request.addfinalizer(fin)
    testflow.setup(
        "Update VM %s to be pinned to host %s", vm_name, config.HOSTS[0]
    )
    assert ll_vms.updateVm(
        True, vm_name,
        placement_affinity=config.VM_PINNED,
        placement_host=config.HOSTS[0]
    )


@pytest.fixture(scope='class')
def enable_hwrng_source_on_cluster(request):
    """
    1. create hwrng device on host if not exists already
    2. Enable hwrng device on cluster
    """
    host_resource = config.VDS_HOSTS[0]
    hwrng_exists = True

    def fin():
        """
        1. Update urandom device on cluster
        2. remove hwrng if created in setup
        """
        testflow.teardown(
            "Update cluster to use %s device", config.URANDOM_RNG
        )
        assert ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], rng_sources=['urandom']
        ), "Failed to update cluster rng device"
        if not hwrng_exists:
            testflow.teardown("remove soft link %s", config.HW_RNG)
            assert host_resource.fs.remove(config.DEST_HWRNG), (
                "Failed to remove %s" % config.DEST_HWRNG
            )
    request.addfinalizer(fin)

    if not host_resource.fs.exists(config.DEST_HWRNG):
        hwrng_exists = False
        cmd = "ln -s /dev/zero %s" % config.DEST_HWRNG
        testflow.setup("Create soft link for %s", config.HW_RNG)
        rc, _, _ = host_resource.run_command(shlex.split(cmd))
        assert not rc, "failed to run %s on host %s" % (cmd, config.HOSTS[0])
    testflow.setup("Update Cluster to use %s device", config.HW_RNG)
    assert ll_clusters.updateCluster(
        True, config.CLUSTER_NAME[0], rng_sources=["hwrng", 'urandom']
    ), "Failed to update cluster rng device"
