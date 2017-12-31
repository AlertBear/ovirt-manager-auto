"""
High performance VM test fixtures
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.sla.high_performance_vm.config as conf


@pytest.fixture(scope="module")
def fill_numa_nodes_constants():
    """
    Fill NUMA node constants
    """
    host_numa_nodes = ll_hosts.get_numa_nodes_from_host(
        host_name=conf.HOSTS[0]
    )
    numa_nodes_with_memory = filter(
        lambda node: ll_hosts.get_numa_node_memory(numa_node_obj=node) > 0,
        host_numa_nodes
    )
    if len(numa_nodes_with_memory) < 2:
        return
    numa_nodes_with_memory.sort(key=ll_hosts.get_numa_node_index)
    conf.NUMA_NODE_0 = numa_nodes_with_memory[0]
    conf.NUMA_NODE_1 = numa_nodes_with_memory[1]


@pytest.fixture(scope="class")
def update_vm_cpu_and_numa_pinning(request):
    """
    Update VM CPU and NUMA pinning before run other fixtures
    """
    vm_params = request.node.cls.vms_to_params[conf.VM_NAME[0]]
    on_the_same_node = request.node.cls.on_the_same_node

    numa_nodes = [conf.NUMA_NODE_0, conf.NUMA_NODE_1]
    cores_number = len(numa_nodes)
    vm_params[conf.VM_CPU_CORES] = cores_number

    cpu_pinning = []
    if on_the_same_node:
        for i, node in enumerate(numa_nodes):
            node_cpu = ll_hosts.get_numa_node_cpus(numa_node_obj=node)[0]
            cpu_pinning.append({str(i): str(node_cpu)})
    else:
        node_index = ll_hosts.get_numa_node_index(
            numa_node_obj=conf.NUMA_NODE_0
        )
        vm_numa_nodes_params = getattr(
            request.node.cls, "vm_numa_nodes_params", []
        )
        # Update VM NUMA node parameters
        vm_numa_nodes_params.append(
            {
                conf.NUMA_NODE_PARAMS_INDEX: 0,
                conf.NUMA_NODE_PARAMS_CORES: range(cores_number),
                conf.NUMA_NODE_PARAMS_MEMORY: ll_vms.get_vm_memory(
                    vm_name=conf.VM_NAME[0]
                ) / conf.MB,
                conf.NUMA_NODE_PARAMS_PIN_LIST: [node_index]
            }
        )
        node_cpus = ll_hosts.get_numa_node_cpus(numa_node_obj=conf.NUMA_NODE_1)
        for i in range(cores_number):
            cpu_pinning.append({str(i): str(node_cpus[i])})

    # Update VM CPU pinning parameters
    vm_params[conf.VM_CPU_PINNING] = cpu_pinning
