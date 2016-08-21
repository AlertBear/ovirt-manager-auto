"""
Multiple pinning helper
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf


def add_one_numa_node_to_vm(negative=False):
    """
    Create one NUMA node on VM
    """
    if ll_hosts.get_num_of_numa_nodes_on_host(host_name=conf.HOSTS[0]) < 2:
        pytest.skip(
            "Host %s does not have enough NUMA nodes" % conf.HOSTS[0]
        )
    vm_memory = ll_vms.get_vm_memory(vm_name=conf.VM_NAME[0])
    vm_cores = range(ll_vms.get_vm_cores(vm_name=conf.VM_NAME[0]))
    host_numa_node_index = ll_hosts.get_numa_nodes_indexes(
        host_name=conf.HOSTS[0]
    )[0]
    assert ll_vms.add_numa_node_to_vm(
        vm_name=conf.VM_NAME[0],
        host_name=conf.HOSTS[0],
        index=0,
        memory=vm_memory,
        cores=vm_cores,
        pin_list=[host_numa_node_index]
    ) == (not negative)


def get_the_same_cpus_from_resources():
    """
    Get intersection of online CPU's on all resources

    Returns:
        int: Index of CPU that exist on all resources
    """
    cpu_list = ll_sla.get_list_of_online_cpus_on_resource(
        resource=conf.VDS_HOSTS[0]
    )
    for resource in conf.VDS_HOSTS[:2]:
        cpu_list = set(cpu_list).intersection(
            ll_sla.get_list_of_online_cpus_on_resource(resource=resource)
        )
    if not cpu_list:
        pytest.skip(
            "Hosts %s do not have the same online CPU" % conf.VDS_HOSTS[:2]
        )
    return cpu_list.pop()
