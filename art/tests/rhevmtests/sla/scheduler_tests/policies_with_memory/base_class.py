"""
Base module for scheduler tests with memory load
"""
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import pytest
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.sla.fixtures import (  # noqa: F401
    run_once_vms,
    update_cluster,
    update_cluster_to_default_parameters,
    update_vms
)
from rhevmtests.sla.scheduler_tests.fixtures import (
    load_hosts_cpu,
    wait_for_scheduling_memory_update
)


def update_configuration_constants(min_memory):
    """
    Update configuration file constants according to the host memory

    Args:
        min_memory (int): The minimal memory that hosts have
    """
    half_host_memory = min_memory / 2
    conf.DEFAULT_PS_PARAMS[
        conf.MIN_FREE_MEMORY
    ] = (half_host_memory + 2 * conf.GB) / conf.MB
    conf.DEFAULT_PS_PARAMS[
        conf.MAX_FREE_MEMORY
    ] = (half_host_memory - 2 * conf.GB) / conf.MB
    conf.DEFAULT_ED_PARAMS[
        conf.MAX_FREE_MEMORY
    ] = (half_host_memory - 2 * conf.GB) / conf.MB
    overutilized_memory = (
        half_host_memory + 3 * conf.GB - half_host_memory % conf.MB
    )
    normalutilized_memory = (
        half_host_memory - conf.GB - half_host_memory % conf.MB
    )
    for normalutilized_vm, overutilized_vm in zip(
        conf.LOAD_NORMALUTILIZED_VMS, conf.LOAD_OVERUTILIZED_VMS
    ):
        conf.LOAD_MEMORY_VMS.update(
            {
                normalutilized_vm: {
                    conf.VM_MEMORY: normalutilized_memory,
                    conf.VM_MEMORY_GUARANTEED: normalutilized_memory,
                    conf.VM_MAX_MEMORY: normalutilized_memory + conf.GB
                },
                overutilized_vm: {
                    conf.VM_MEMORY: overutilized_memory,
                    conf.VM_MEMORY_GUARANTEED: overutilized_memory,
                    conf.VM_MAX_MEMORY: overutilized_memory + conf.GB
                }
            }
        )
    memory_near_overutilized = conf.DEFAULT_PS_PARAMS[
        conf.MIN_FREE_MEMORY
    ] * conf.MB - conf.GB / 2
    conf.MEMORY_NEAR_OVERUTILIZED = {
        conf.VM_MEMORY: memory_near_overutilized,
        conf.VM_MAX_MEMORY: memory_near_overutilized + conf.GB,
        conf.VM_MEMORY_GUARANTEED: memory_near_overutilized
    }


@pytest.fixture(scope="module")
def prepare_environment_for_tests(request):
    """
    1) Update cluster overcommitment to NONE
    2) Update and start VM's to equalize the scheduling memory on all hosts
    3) Update memory parameters for EvenDistribution and PowerSaving policies
    4) Create VM's for the memory load
    """
    def fin():
        """
        1) Remove memory load VM's
        2) Stop CPU load on all hosts
        3) Stop VM's that used to equalize the scheduling memory of hosts
        4) Update VM's to default parameters
        """
        results = []
        u_libs.testflow.teardown(
            "Remove VM's: %s", conf.LOAD_MEMORY_VMS.keys()
        )
        results.append(ll_vms.safely_remove_vms(conf.LOAD_MEMORY_VMS.keys()))
        u_libs.testflow.teardown("Stop CPU load on all hosts")
        sch_helpers.stop_cpu_load_on_all_hosts()
        u_libs.testflow.teardown("Stop VM's %s", conf.VM_NAME[3:5])
        results.append(ll_vms.stop_vms_safely(vms_list=conf.VM_NAME[3:5]))
        for vm_name in conf.VM_NAME[3:5]:
            u_libs.testflow.teardown(
                "Update the VM %s with parameters %s",
                vm_name, conf.DEFAULT_VM_PARAMETERS
            )
            results.append(
                ll_vms.updateVm(
                    positive=True, vm=vm_name, **conf.DEFAULT_VM_PARAMETERS
                )
            )
        assert all(results)
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Update the cluster %s overcommitment to %s",
        conf.CLUSTER_NAME[0], conf.CLUSTER_OVERCOMMITMENT_NONE
    )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_NONE
    )

    hosts_to_memory = {}
    for host_name in conf.HOSTS[:3]:
        hosts_to_memory[host_name] = ll_hosts.get_host_max_scheduling_memory(
            host_name=host_name
        )
    min_memory = min(hosts_to_memory.values())
    update_params = {
        conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
    }
    vm_index = 3
    for host_name, host_memory in hosts_to_memory.iteritems():
        if host_memory != min_memory:
            update_params[conf.VM_PLACEMENT_HOSTS] = [host_name]
            # Will give me number divided by conf.MB without remainder
            vm_memory = (
                (host_memory - min_memory) / conf.MB * conf.MB
            ) - conf.RESERVED_MEMORY * conf.MB
            for vm_param in (
                conf.VM_MEMORY, conf.VM_MEMORY_GUARANTEED, conf.VM_MAX_MEMORY
            ):
                update_params[vm_param] = vm_memory
            u_libs.testflow.setup(
                "Update the VM %s with parameters %s",
                conf.VM_NAME[vm_index], update_params
            )
            assert ll_vms.updateVm(
                positive=True, vm=conf.VM_NAME[vm_index], **update_params
            )
            vm_index += 1

    u_libs.testflow.setup("Start VM's %s", conf.VM_NAME[3:5])
    ll_vms.start_vms(vm_list=conf.VM_NAME[3:5])

    u_libs.testflow.setup("Update configuration constants")
    update_configuration_constants(min_memory=min_memory)

    for vm_name, vm_params in conf.LOAD_MEMORY_VMS.iteritems():
        u_libs.testflow.setup(
            "Create VM %s with parameters: %s", vm_name, vm_params
        )
        assert ll_vms.createVm(
            positive=True,
            vmName=vm_name,
            cluster=conf.CLUSTER_NAME[0],
            storageDomainName=conf.STORAGE_NAME[0],
            provisioned_size=conf.GB,
            nic=conf.NIC_NAME[0],
            network=conf.MGMT_BRIDGE,
            **vm_params
        )


@u_libs.attr(tier=3)
@pytest.mark.usefixtures(
    prepare_environment_for_tests.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    wait_for_scheduling_memory_update.__name__,
    update_cluster.__name__
)
class BaseStartVmsUnderPolicyWithMemory(u_libs.SlaTest):
    """
    Base class for scheduler tests with the memory load
    """
    hosts_cpu_load = None
    vms_to_run = None
    cluster_to_update_params = None


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    prepare_environment_for_tests.__name__,
    update_vms.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    wait_for_scheduling_memory_update.__name__,
    update_cluster.__name__
)
class BaseUpdateAndStartVmsUnderPolicyWithMemory(u_libs.SlaTest):
    """
    Base class for start and migrate vm test
    """
    vms_to_params = None
    hosts_cpu_load = {conf.CPU_LOAD_50: xrange(3)}
    vms_to_run = None
    cluster_to_update_params = None
