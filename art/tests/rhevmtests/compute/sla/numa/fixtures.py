"""
Fixtures for NUMA test
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
import rhevmtests.compute.sla.helpers as sla_helpers


@pytest.fixture(scope="class")
def update_vm_numa_mode(request):
    """
    1) Update VM NUMA mode
    """
    vm_numa_mode = request.node.cls.vm_numa_mode

    def fin():
        """
        1) Update VM NUMA mode to interleave
        """
        ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            numa_mode=conf.ENGINE_NUMA_MODES[conf.INTERLEAVE_MODE]
        )
    request.addfinalizer(fin)

    assert ll_vms.updateVm(
        positive=True,
        vm=conf.VM_NAME[0],
        numa_mode=conf.ENGINE_NUMA_MODES[vm_numa_mode]
    )


@pytest.fixture(scope="class")
def update_vm_cpu_pinning():
    """
    1) Update VM CPU pinning
    """
    host_online_cpu = ll_sla.get_list_of_online_cpus_on_resource(
        resource=conf.VDS_HOSTS[0]
    )[0]
    assert ll_vms.updateVm(
        positive=True,
        vm=conf.VM_NAME[0],
        vcpu_pinning=[{"0": str(host_online_cpu)}]
    )


@pytest.fixture(scope="class")
def pin_one_vm_numa_node_to_two_host_numa_nodes():
    """
    Pin one VM NUMA node to two host NUMA nodes
    """
    host_numa_nodes_indexes = ll_hosts.get_numa_nodes_indexes(
        host_name=conf.HOSTS[0]
    )[:2]
    vm_numa_node_params = {
        conf.NUMA_NODE_PARAMS_INDEX: 0,
        conf.NUMA_NODE_PARAMS_CORES: [0, 1],
        conf.NUMA_NODE_PARAMS_MEMORY: 1024,
        conf.NUMA_NODE_PARAMS_PIN_LIST: host_numa_nodes_indexes
    }
    assert ll_vms.add_numa_node_to_vm(
        vm_name=conf.VM_NAME[0],
        host_name=conf.HOSTS[0],
        **vm_numa_node_params
    )


@pytest.fixture(scope="class")
def pin_two_vm_numa_nodes_to_tone_host_numa_node():
    """
    Pin two VM NUMA nodes to one host NUMA node
    """
    host_numa_node_index = ll_hosts.get_numa_nodes_indexes(
        host_name=conf.HOSTS[0]
    )[0]
    vm_numa_nodes_params = [
        {
            conf.NUMA_NODE_PARAMS_INDEX: 0,
            conf.NUMA_NODE_PARAMS_CORES: [0, 1],
            conf.NUMA_NODE_PARAMS_MEMORY: 512,
            conf.NUMA_NODE_PARAMS_PIN_LIST: [host_numa_node_index]
        },
        {
            conf.NUMA_NODE_PARAMS_INDEX: 1,
            conf.NUMA_NODE_PARAMS_CORES: [2, 3],
            conf.NUMA_NODE_PARAMS_MEMORY: 512,
            conf.NUMA_NODE_PARAMS_PIN_LIST: [host_numa_node_index]
        }
    ]
    for vm_numa_node_params in vm_numa_nodes_params:
        assert ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_node_params
        )


@pytest.fixture(scope="class")
def update_vm_memory_for_numa_test(request):
    """
    1) Update VM memory to be greater or lesser than host NUMA node memory
    """
    negative_test = request.node.cls.negative_test
    host_numa_node = ll_hosts.get_numa_nodes_from_host(
        host_name=conf.HOSTS[0]
    )[0]
    host_memory = ll_hosts.get_numa_node_memory(
        numa_node_obj=host_numa_node
    ) * conf.MB
    vm_memory = host_memory - conf.GB
    if negative_test:
        vm_memory = host_memory + conf.GB
    assert ll_vms.updateVm(
        positive=True,
        vm=conf.VM_NAME[0],
        memory=vm_memory,
        memory_guaranteed=vm_memory,
        max_memory=vm_memory + conf.GB
    )


@pytest.fixture(scope="class")
def get_pci_device_name(request):
    """
    Get PCI device and save it to the class variable
    """
    pci_device = sla_helpers.get_pci_device(host_name=conf.HOSTS[0])
    if not pci_device:
        pytest.skip(
            "Can not find PCI device for passthrough on the host %s" %
            conf.HOSTS[0]
        )
    request.node.cls.pci_device_name = pci_device.get_name()


@pytest.fixture(scope="class")
def get_pci_device_numa_node(request):
    """
    Get PCI device NUMA node and save it to the class variable
    """
    klass = request.node.cls
    pci_devices = helpers.get_pci_devices_numa_node_from_resource(
        resource=conf.VDS_HOSTS[0]
    )
    pci_device_numa_node = pci_devices[klass.pci_device_name]
    if pci_device_numa_node == -1:
        pytest.skip(
            "PCI device %s does not have mapping to NUMA nodes" %
            klass.pci_device_name
        )
    klass.pci_device_numa_node = pci_device_numa_node
