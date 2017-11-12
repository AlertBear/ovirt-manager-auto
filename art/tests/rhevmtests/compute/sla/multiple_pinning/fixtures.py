"""
Multiple pinning fixtures
"""

import pytest

import config as conf
import helpers as pinning_helpers


@pytest.fixture(scope="class")
def update_class_cpu_pinning(request):
    """
    1) Update CPU pinning class variable
    """
    vcpu_pinning = [
        {"0": "%s" % pinning_helpers.get_the_same_cpus_from_resources()}
    ]
    request.node.cls.vms_to_params[
        conf.VM_NAME[0]
    ][conf.VM_CPU_PINNING] = vcpu_pinning


@pytest.fixture(scope="class")
def change_host_cluster(request):
    """
    Change the host cluster
    """
    def fin():
        pinning_helpers.change_host_cluster(cluster_name=conf.CLUSTER_NAME[0])
    request.addfinalizer(fin)

    assert pinning_helpers.change_host_cluster(
        cluster_name=conf.CLUSTER_NAME[1]
    )
