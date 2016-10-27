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
from rhevmtests.sla.fixtures import (
    run_once_vms,
    update_cluster,
    update_cluster_to_default_parameters,  # flake8: noqa
    update_vms
)
from rhevmtests.sla.scheduler_tests.fixtures import (
    load_hosts_cpu,
    wait_for_scheduling_memory_update
)


def update_configuration_constants():
    """
    Update configuration file constants according to the host memory
    """
    first_host_sch_memory = ll_hosts.get_host_max_scheduling_memory(
        host_name=conf.HOSTS[0]
    )
    for host_name in conf.HOSTS[1:3]:
        host_sch_memory = ll_hosts.get_host_max_scheduling_memory(
            host_name=host_name
        )
        if (
            first_host_sch_memory - 512 * conf.MB > host_sch_memory or
            host_sch_memory > first_host_sch_memory + 512 * conf.MB
        ):
            pytest.skip(
                "Host %s scheduling memory %s does not equal "
                "to the host %s scheduling memory %s",
                host_name, host_sch_memory,
                conf.HOSTS[0], first_host_sch_memory
            )
    half_host_memory = first_host_sch_memory / 2
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
                    conf.VM_MEMORY_GUARANTEED: normalutilized_memory
                },
                overutilized_vm: {
                    conf.VM_MEMORY: overutilized_memory,
                    conf.VM_MEMORY_GUARANTEED: overutilized_memory
                }
            }
        )
    memory_near_overutilized = conf.DEFAULT_PS_PARAMS[
        conf.MIN_FREE_MEMORY
    ] * conf.MB - conf.GB / 2
    conf.MEMORY_NEAR_OVERUTILIZED[conf.VM_MEMORY] = memory_near_overutilized
    conf.MEMORY_NEAR_OVERUTILIZED[
        conf.VM_MEMORY_GUARANTEED
    ] = memory_near_overutilized


@pytest.fixture(scope="module")
def prepare_environment_for_tests(request):
    """
    1) Update cluster overcommitment to NONE
    2) Update memory parameters for EvenDistribution and PowerSaving policies
    3) Create VM's for the memory load
    """
    def fin():
        """
        1) Remove memory load VM's
        2) Stop CPU load on all hosts
        """
        u_libs.testflow.teardown(
            "Remove VM's: %s", conf.LOAD_MEMORY_VMS.keys()
        )
        ll_vms.safely_remove_vms(conf.LOAD_MEMORY_VMS.keys())
        u_libs.testflow.teardown("Stop CPU load on all hosts")
        sch_helpers.stop_cpu_load_on_all_hosts()
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

    u_libs.testflow.setup("Update configuration constants")
    update_configuration_constants()

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
