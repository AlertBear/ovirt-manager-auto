import shlex

import pytest

import rhevmtests.compute.virt.config as config
import rhevmtests.helpers as helpers
from art.rhevm_api.tests_lib.low_level import clusters as ll_clusters
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
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
def set_hwrng_device():
    """
    Verify if hwrng device exists and is operational, if not operational -
    remove it and replace with /dev/zero, if not exist assign it to /dev/zero.
    """

    for host_name in config.HOSTS:
        host_ip = ll_hosts.get_host_ip(host_name)
        host = helpers.get_host_resource(host_ip, config.VDC_ROOT_PASSWORD)
        if host.fs.exists(config.DEST_HWRNG):
            if host.run_command(shlex.split(config.VERIFY_RNG_DEVICE_ACTIVE)):
                return
            else:
                host.run_command(shlex.split("rm -f /dev/hwrng"))
        if not host.fs.exists(config.DEST_HWRNG):
            cmd = "ln -s /dev/zero {device}".format(device=config.DEST_HWRNG)
            testflow.setup(
                "Create soft link for {device}".format(device=config.HW_RNG)
            )
            rc, _, _ = host.run_command(shlex.split(cmd))
            assert not rc, "failed to run %s on host %s" % (cmd, host.ip)
