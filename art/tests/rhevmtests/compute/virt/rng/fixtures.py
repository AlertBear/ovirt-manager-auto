import shlex

import pytest

import config
import rhevmtests.helpers as helpers
from art.rhevm_api.tests_lib.low_level import clusters as ll_clusters
from art.unittest_lib import testflow


@pytest.fixture(scope='class')
def enable_hwrng_source_on_cluster(request):
    """
    Enable HWRNG on cluster.
    """

    def fin():
        """
        Update urandom device on cluster
        """
        testflow.teardown(
            "Update cluster to use %s device", config.URANDOM_RNG
        )
        assert ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], rng_sources=['urandom']
        ), "Failed to update cluster rng device"
    request.addfinalizer(fin)

    testflow.setup("Update Cluster to use %s device", config.HW_RNG)
    assert ll_clusters.updateCluster(
        True, config.CLUSTER_NAME[0], rng_sources=["hwrng", 'urandom']
    ), "Failed to update cluster rng device"


@pytest.fixture(scope='class')
def add_symbolic_link_on_host(request):
    """
    Add sym link on cluster.
    """
    vm_name = request.node.cls.vm_name
    hwrng_exists = True

    def fin():
        """
        Remove hwrng if created in setup
        """
        if not hwrng_exists:
            testflow.teardown("remove soft link %s", config.HW_RNG)
            assert host_resource.fs.remove(config.DEST_HWRNG), (
                "Failed to remove %s" % config.DEST_HWRNG
            )
    request.addfinalizer(fin)

    host_resource = helpers.get_host_resource_of_running_vm(vm_name)
    if not host_resource.fs.exists(config.DEST_HWRNG):
        hwrng_exists = False
        cmd = "ln -s /dev/zero %s" % config.DEST_HWRNG
        testflow.setup("Create soft link for %s", config.HW_RNG)
        rc, _, _ = host_resource.run_command(shlex.split(cmd))
        assert not rc, "failed to run %s on host %s" % (cmd, host_resource.ip)
