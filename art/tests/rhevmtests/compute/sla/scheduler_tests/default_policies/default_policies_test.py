"""
Scheduler - Rhevm Cluster Policies Test
Check different cases for migration when cluster police is Evenly Distributed
and Power Saving
"""
import random

import pytest
import rhevmtests.compute.sla.config as sla_conf
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.compute.sla.fixtures import (
    choose_specific_host_as_spm,
    migrate_he_vm,
    run_once_vms,
    activate_hosts,
    update_cluster,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch_policies
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier1, tier2, SlaTest
from rhevmtests.compute.sla.scheduler_tests.fixtures import load_hosts_cpu

host_as_spm = 2
he_dst_host = 2


@pytest.fixture(scope="module")
def init_default_policies_test(request):
    """
    1) Create PowerSaving and EvenDistribution scheduler policies
    """
    def fin():
        """
        1) Remove PowerSaving and EvenDistribution scheduler policies
        """
        results = list()
        for policy_name in (
            sla_conf.POLICY_CUSTOM_PS, sla_conf.POLICY_CUSTOM_ED
        ):
            results.append(
                ll_sch_policies.remove_scheduling_policy(
                    policy_name=policy_name
                )
            )
        assert all(results)
    request.addfinalizer(fin)

    for policy_name, unit_name in zip(
        (sla_conf.POLICY_CUSTOM_PS, sla_conf.POLICY_CUSTOM_ED),
        (sla_conf.PS_OPTIMAL_FOR_CPU_UNIT, sla_conf.ED_OPTIMAL_FOR_CPU_UNIT)
    ):
        sch_helpers.add_scheduler_policy(
            policy_name=policy_name,
            policy_units=sla_conf.TEST_SCHEDULER_POLICIES_UNITS[policy_name],
            additional_params={
                sla_conf.PREFERRED_HOSTS: {sla_conf.WEIGHT_FACTOR: 99},
                unit_name: {sla_conf.WEIGHT_FACTOR: 10}
            }
        )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=sla_conf.CLUSTER_NAME[0],
        mem_ovrcmt_prc=100
    )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    migrate_he_vm.__name__,
    init_default_policies_test.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    update_cluster.__name__
)
class BaseDefaultPolicies(SlaTest):
    """
    Base class for all default policies
    """
    pass


class BasePowerSavingPolicy(BaseDefaultPolicies):
    """
    Base class for all tests with power_saving policy
    """
    cluster_to_update_params = {
        sla_conf.CLUSTER_SCH_POLICY: sla_conf.POLICY_CUSTOM_PS,
        sla_conf.CLUSTER_SCH_POLICY_PROPERTIES: sla_conf.DEFAULT_PS_PARAMS
    }


class TestPowerSavingBalanceModule1(BasePowerSavingPolicy):
    """
    VM run on under utilized host and must migrate to normal utilized host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_50: [1]}

    @tier2
    @polarion("RHEVM3-9498")
    def test_power_saving_balance_module_1(self):
        """
        Check if some of VM's migrate on the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[1], expected_num_of_vms=2
        )


class TestPowerSavingBalanceModule2(BasePowerSavingPolicy):
    """
    VM run on under utilized host, but another hosts in cluster over or under
    utilized, so VM must stay on old host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_RUN_ONCE_HOST: 0,
            sla_conf.VM_RUN_ONCE_WAIT_FOR_STATE: sla_conf.VM_UP
        },
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_100: [1]}

    @tier2
    @polarion("RHEVM3-9489")
    def test_power_saving_balance_module_2(self):
        """
        Check if some of VM's migrate on or from the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[0], expected_num_of_vms=1, negative=True
        )


class TestPowerSavingBalanceModule3(BasePowerSavingPolicy):
    """
    VM run on under utilized host, check that VM migrate
    to normal utilized host and not to over utilized host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_50: [1], sla_conf.CPU_LOAD_100: [2]}

    @tier2
    @polarion("RHEVM3-9490")
    def test_power_saving_balance_module_3(self):
        """
        Check if some of VM's migrate on the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[1], expected_num_of_vms=2
        )


@pytest.mark.usefixtures(activate_hosts.__name__)
class TestPowerSavingWeightModule1(BasePowerSavingPolicy):
    """
    VM run on normal utilized host, we put host to
    maintenance and check that VM migrated to normal utilized host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_50: range(2)}
    hosts_to_activate_indexes = [0]

    @tier2
    @polarion("RHEVM3-9492")
    def test_power_saving_weight_module_1(self):
        """
        Check if VM migrate on the normalutilized host
        """
        testflow.step(
            "Check that VM %s migrates on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[1]
        )
        assert (
            sch_helpers.migrate_vm_by_maintenance_and_get_destination_host(
                src_host=sla_conf.HOSTS[0],
                vm_name=sla_conf.VM_NAME[0],
                host_resource=sla_conf.VDS_HOSTS[0]
            ) == sla_conf.HOSTS[1]
        )


class BasePowerEvenDistribution(BaseDefaultPolicies):
    """
    Base class for all tests with even_distribution policy
    """
    cluster_to_update_params = {
        sla_conf.CLUSTER_SCH_POLICY: sla_conf.POLICY_CUSTOM_ED,
        sla_conf.CLUSTER_SCH_POLICY_PROPERTIES: sla_conf.DEFAULT_ED_PARAMS
    }


class TestEvenDistributedBalanceModule1(BasePowerEvenDistribution):
    """
    VM run on over utilized host and must migrate to normal utilized host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_100: range(2)}

    @tier2
    @polarion("RHEVM3-9493")
    def test_even_distributed_balance_module_1(self):
        """
        Check if some VM migrated on the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[2], expected_num_of_vms=2
        )


class TestEvenDistributedBalanceModule2(BasePowerEvenDistribution):
    """
    VM run on over utilized host, but other cluster hosts also over utilized,
    so VM must stay on old host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_RUN_ONCE_HOST: 0,
            sla_conf.VM_RUN_ONCE_WAIT_FOR_STATE: sla_conf.VM_UP
        },
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_100: range(3)}

    @tier2
    @polarion("RHEVM3-9494")
    def test_even_distributed_balance_module_2(self):
        """
        Check if VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[0], expected_num_of_vms=1, negative=True
        )


@pytest.mark.usefixtures(activate_hosts.__name__)
class TestEvenDistributedWeightModule1(BasePowerEvenDistribution):
    """
    VM run on normal utilized host, we put host to
    maintenance and check that VM migrated on normal utilized host
    """
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    hosts_cpu_load = {sla_conf.CPU_LOAD_100: [2]}
    hosts_to_activate_indexes = [0]

    @tier2
    @polarion("RHEVM3-9496")
    def test_even_distributed_weight_module_1(self):
        """
        Check if VM migrated on the normalutilized host
        """
        testflow.step(
            "Check that VM %s migrates on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[1]
        )
        assert (
            sch_helpers.migrate_vm_by_maintenance_and_get_destination_host(
                src_host=sla_conf.HOSTS[0],
                vm_name=sla_conf.VM_NAME[0],
                host_resource=sla_conf.VDS_HOSTS[0]
            ) == sla_conf.HOSTS[1]
        )


@pytest.mark.usefixtures(update_cluster_to_default_parameters.__name__)
class TestCheckClusterPoliciesParameters(SlaTest):
    """
    Check different values for cluster policy parameters:
        1) CpuOverCommitDurationMinutes - min=1; max=99
        2) HighUtilization - min=50; max=99
        3) LowUtilization - min=0; max=49
    Added, because the bug
        https://bugzilla.redhat.com/show_bug.cgi?id=1070704
    """

    @tier1
    @polarion("RHEVM-14841")
    def test_check_cluster_policies_parameters(self):
        """
        Check different values for cluster policy parameters:
            1) CpuOverCommitDurationMinutes - min=1; max=99
            2) HighUtilization - min=50; max=99
            3) LowUtilization - min=0; max=49
        Added, because the bug
            https://bugzilla.redhat.com/show_bug.cgi?id=1070704
        """
        high_utilization = random.randint(50, 99)
        low_utilization = random.randint(1, 49)
        duration = random.randint(1, 99) * 60
        policies_params = {
            sla_conf.POLICY_EVEN_DISTRIBUTION: {
                sla_conf.HIGH_UTILIZATION: high_utilization,
                sla_conf.OVER_COMMITMENT_DURATION: duration
            },
            sla_conf.POLICY_POWER_SAVING: {
                sla_conf.HIGH_UTILIZATION: high_utilization,
                sla_conf.LOW_UTILIZATION: low_utilization,
                sla_conf.OVER_COMMITMENT_DURATION: duration

            }
        }
        for policy, properties in policies_params.iteritems():
            assert ll_clusters.updateCluster(
                positive=True,
                cluster=sla_conf.CLUSTER_NAME[0],
                scheduling_policy=policy,
                properties=properties
            )
