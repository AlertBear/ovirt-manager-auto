"""
Multiple pinning fixtures
"""
import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers as pinning_helpers
import pytest


logger = logging.getLogger(__name__)


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
def numa_pinning(request):
    """
    1) Add NUMA node to VM
    2) Pin VNUMA node to PNUMA
    """
    def fin():
        """
        1) Remove NUMA node from VM
        """
        u_libs.testflow.teardown(
            "Remove NUMA node with index %s from the VM %s", 0, conf.VM_NAME[0]
        )
        ll_vms.remove_numa_node_from_vm(
            vm_name=conf.VM_NAME[0], numa_node_index=0
        )
    request.addfinalizer(fin)

    pinning_helpers.add_one_numa_node_to_vm()


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
