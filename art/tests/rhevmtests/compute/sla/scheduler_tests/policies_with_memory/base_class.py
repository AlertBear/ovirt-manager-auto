"""
Base module for scheduler tests with memory load
"""
import pytest
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from concurrent.futures import ThreadPoolExecutor
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    migrate_he_vm,
    run_once_vms,
    choose_specific_host_as_spm,
    update_cluster,
    update_vms,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch_policies
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
from rhevmtests.compute.sla.scheduler_tests.fixtures import (
    load_hosts_cpu,
    wait_for_scheduling_memory_update
)

he_dst_host = 2
host_as_spm = 2


@pytest.fixture(scope="class")
def update_vm_parameters_variable(request):
    """
    Update parameters for the VM update
    """
    request.node.cls.vms_to_params = {
        conf.VM_NAME[2]: conf.MEMORY_NEAR_OVERUTILIZED,
    }


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
    5) Create custom PowerSaving and EvenDistribution policies
    """
    def fin():
        """
        1) Remove custom PowerSaving and EvenDistribution policies
        2) Remove memory load VM's
        3) Stop CPU load on all hosts
        4) Stop VM's that used to equalize the scheduling memory of hosts
        5) Update VM's to default parameters
        """
        results = []
        for policy_name in conf.POLICY_CUSTOM_FACTOR.iterkeys():
            results.append(
                ll_sch_policies.remove_scheduling_policy(
                    policy_name=policy_name
                )
            )
        u_libs.testflow.teardown(
            "Remove VM's: %s", conf.LOAD_MEMORY_VMS.keys()
        )
        results.append(ll_vms.safely_remove_vms(conf.LOAD_MEMORY_VMS.keys()))
        u_libs.testflow.teardown("Stop CPU load on all hosts")
        sch_helpers.stop_cpu_load_on_all_hosts()
        u_libs.testflow.teardown("Stop VM's %s", conf.VM_NAME[4:6])
        results.append(ll_vms.stop_vms_safely(vms_list=conf.VM_NAME[4:6]))
        for vm_name in conf.VM_NAME[4:6]:
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
    vm_index = 4
    for host_name, host_memory in hosts_to_memory.iteritems():
        if host_memory == min_memory:
            continue

        # Will give me number divided by conf.MB without remainder
        vm_memory = (host_memory - min_memory) / conf.MB * conf.MB
        if vm_memory <= conf.RESERVED_MEMORY:
            continue
        update_params[conf.VM_PLACEMENT_HOSTS] = [host_name]
        vm_memory -= conf.RESERVED_MEMORY
        for vm_param in (
            conf.VM_MEMORY, conf.VM_MEMORY_GUARANTEED, conf.VM_MAX_MEMORY
        ):
            update_params[vm_param] = vm_memory
        assert ll_vms.updateVm(
            positive=True, vm=conf.VM_NAME[vm_index], **update_params
        )
        u_libs.testflow.setup("Start VM %s", conf.VM_NAME[vm_index])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[vm_index])
        vm_index += 1

    u_libs.testflow.setup("Update configuration constants")
    update_configuration_constants(min_memory=min_memory)

    with ThreadPoolExecutor(max_workers=len(conf.LOAD_MEMORY_VMS)) as executor:
        results = []
        for vm_name, vm_params in conf.LOAD_MEMORY_VMS.iteritems():
            u_libs.testflow.setup(
                "Create VM %s with parameters: %s", vm_name, vm_params
            )
            results.append(
                executor.submit(
                    fn=ll_vms.createVm,
                    positive=True,
                    vmName=vm_name,
                    cluster=conf.CLUSTER_NAME[0],
                    storageDomainName=conf.STORAGE_NAME[0],
                    provisioned_size=conf.GB,
                    nic=conf.NIC_NAME[0],
                    network=conf.MGMT_BRIDGE,
                    **vm_params
                )
            )
    assert all([result.result() for result in results])

    for policy_type, policies_names in conf.TEST_SCH_POLICIES.iteritems():
        for policy_name in policies_names:
            sch_helpers.add_scheduler_policy(
                policy_name=policy_name,
                policy_units=conf.TEST_SCHEDULER_POLICIES_UNITS[policy_type],
                additional_params={
                    conf.PREFERRED_HOSTS: {conf.WEIGHT_FACTOR: 99},
                    conf.POLICY_CUSTOM_FACTOR[policy_name]: {
                        conf.WEIGHT_FACTOR: 10
                    }
                }
            )


@u_libs.tier3
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    migrate_he_vm.__name__,
    prepare_environment_for_tests.__name__,
    wait_for_scheduling_memory_update.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    update_cluster.__name__
)
class BaseStartVmsUnderPolicyWithMemory(u_libs.SlaTest):
    """
    Base class for scheduler tests with the memory load
    """
    hosts_cpu_load = None
    vms_to_run = None
    cluster_to_update_params = None


@u_libs.tier2
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    migrate_he_vm.__name__,
    prepare_environment_for_tests.__name__,
    update_vms.__name__,
    wait_for_scheduling_memory_update.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    update_cluster.__name__
)
class BaseUpdateAndStartVmsUnderPolicyWithMemory(u_libs.SlaTest):
    """
    Base class for VM start and migrate tests
    """
    vms_to_params = None
    hosts_cpu_load = {conf.CPU_LOAD_50: xrange(3)}
    vms_to_run = None
    cluster_to_update_params = None


@u_libs.tier2
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    migrate_he_vm.__name__,
    prepare_environment_for_tests.__name__,
    update_vm_parameters_variable.__name__,
    update_vms.__name__,
    wait_for_scheduling_memory_update.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    update_cluster.__name__
)
class BaseTakeVmMemoryInAccount(u_libs.SlaTest):
    """
    Base class to verify that the scheduler take in account the VM memory
    before balancing operation
    """
    vms_to_params = None
    hosts_cpu_load = {conf.CPU_LOAD_50: xrange(3)}
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_6
    cluster_to_update_params = None
