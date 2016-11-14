"""
Multiple pinning fixtures
"""
import logging

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
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
def attach_host_device(request):
    """
    1) Attach host device to VM
    """
    host_device_name = ll_hosts.get_host_devices(
        host_name=conf.HOSTS[0]
    )[0].get_name()

    def fin():
        """
        1) Remove host device from VM
        """
        if ll_vms.get_vm_host_devices(vm_name=conf.VM_NAME[0]):
            u_libs.testflow.teardown(
                "Detach the host device %s from VM %s",
                host_device_name, conf.VM_NAME[0]
            )
            ll_vms.remove_vm_host_device(
                vm_name=conf.VM_NAME[0], device_name=host_device_name
            )
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Attach the host device %s to VM %s", host_device_name, conf.VM_NAME[0]
    )
    assert ll_vms.add_vm_host_device(
        vm_name=conf.VM_NAME[0],
        device_name=host_device_name,
        host_name=conf.HOSTS[0]
    )
