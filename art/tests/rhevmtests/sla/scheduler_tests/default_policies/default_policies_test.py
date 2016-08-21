"""
Scheduler - Rhevm Cluster Policies Test
Check different cases for migration when cluster police is Evenly Distributed
and Power Saving
"""
import logging
import random

import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.unittest_lib as u_libs
import rhevmtests.sla.config as sla_conf
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from art.test_handler.tools import polarion, bz
from rhevmtests.sla.fixtures import (
    choose_specific_host_as_spm,
    run_once_vms,
    activate_hosts
)
from rhevmtests.sla.scheduler_tests.fixtures import (
    load_hosts_cpu,
    update_cluster_policy_to_even_distributed,
    update_cluster_policy_to_none,
    update_cluster_policy_to_power_saving
)

logger = logging.getLogger(__name__)
host_as_spm = 2


@pytest.fixture(scope="module")
def setup_default_policies(request):
    """
    1) Change engine-config LowUtilizationForEvenlyDistribute to 35
    """
    def fin():
        """
        1) Change engine-config LowUtilizationForEvenlyDistribute to 0
        """
        sch_helpers.change_engine_config_low_utilization_value(0)
    request.addfinalizer(fin)

    assert sch_helpers.change_engine_config_low_utilization_value(
        sla_conf.LOW_UTILIZATION_VALUE
    )


@bz({'1316456': {}})
@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    setup_default_policies.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__
)
class BaseDefaultPolicies(u_libs.SlaTest):
    """
    Base class for all default policies
    """
    pass


@pytest.mark.usefixtures(update_cluster_policy_to_power_saving.__name__)
class TestPowerSavingBalanceModule1(BaseDefaultPolicies):
    """
    VM run on under utilized host and must migrate to normal utilized host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_50: [1]}

    @polarion("RHEVM3-9498")
    def test_power_saving_balance_module_1(self):
        """
        Check if some of VM's migrate on the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[1], expected_num_of_vms=2
        )


@pytest.mark.usefixtures(update_cluster_policy_to_power_saving.__name__)
class TestPowerSavingBalanceModule2(BaseDefaultPolicies):
    """
    VM run on under utilized host, but another hosts in cluster over or under
    utilized, so VM must stay on old host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_RUN_ONCE_HOST: 0,
            sla_conf.VM_RUN_ONCE_WAIT_FOR_STATE: sla_conf.VM_UP
        },
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_100: [1]}

    @polarion("RHEVM3-9489")
    def test_power_saving_balance_module_2(self):
        """
        Check if some of VM's migrate on or from the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[0], expected_num_of_vms=1, negative=True
        )


@pytest.mark.usefixtures(update_cluster_policy_to_power_saving.__name__)
class TestPowerSavingBalanceModule3(BaseDefaultPolicies):
    """
    VM run on under utilized host, check that VM migrate
    to normal utilized host and not to over utilized host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_50: [1], sla_conf.CPU_LOAD_100: [2]}

    @polarion("RHEVM3-9490")
    def test_power_saving_balance_module_3(self):
        """
        Check if some of VM's migrate on the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[1], expected_num_of_vms=2
        )


@pytest.mark.usefixtures(
    update_cluster_policy_to_power_saving.__name__,
    activate_hosts.__name__
)
class TestPowerSavingWeightModule1(BaseDefaultPolicies):
    """
    VM run on normal utilized host, we put host to
    maintenance and check that VM migrated to normal utilized host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_50: range(2)}
    hosts_to_activate_indexes = [0]

    @polarion("RHEVM3-9492")
    def test_power_saving_weight_module_1(self):
        """
        Check if VM migrate on the normalutilized host
        """
        assert (
            sch_helpers.migrate_vm_by_maintenance_and_get_destination_host(
                src_host=sla_conf.HOSTS[0], vm_name=sla_conf.VM_NAME[0]
            ) == sla_conf.HOSTS[1]
        )


@pytest.mark.usefixtures(update_cluster_policy_to_even_distributed.__name__)
class TestEvenDistributedBalanceModule1(BaseDefaultPolicies):
    """
    VM run on over utilized host and must migrate to normal utilized host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_100: range(2)}

    @polarion("RHEVM3-9493")
    def test_even_distributed_balance_module_1(self):
        """
        Check if some VM migrated on the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[2], expected_num_of_vms=2
        )


@pytest.mark.usefixtures(update_cluster_policy_to_even_distributed.__name__)
class TestEvenDistributedBalanceModule2(BaseDefaultPolicies):
    """
    VM run on over utilized host, but other cluster hosts also over utilized,
    so VM must stay on old host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_RUN_ONCE_HOST: 0,
            sla_conf.VM_RUN_ONCE_WAIT_FOR_STATE: sla_conf.VM_UP
        },
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_100: range(3)}

    @polarion("RHEVM3-9494")
    def test_even_distributed_balance_module_2(self):
        """
        Check if VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=sla_conf.HOSTS[0], expected_num_of_vms=1, negative=True
        )


@pytest.mark.usefixtures(
    update_cluster_policy_to_even_distributed.__name__,
    activate_hosts.__name__
)
class TestEvenDistributedWeightModule1(BaseDefaultPolicies):
    """
    VM run on normal utilized host, we put host to
    maintenance and check that VM migrated on normal utilized host
    """
    __test__ = True
    vms_to_run = {
        sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0},
        sla_conf.VM_NAME[1]: {sla_conf.VM_RUN_ONCE_HOST: 1},
        sla_conf.VM_NAME[2]: {sla_conf.VM_RUN_ONCE_HOST: 2}
    }
    vms_to_stop = sla_conf.VM_NAME[:3]
    load_d = {sla_conf.CPU_LOAD_100: [2]}
    hosts_to_activate_indexes = [0]

    @polarion("RHEVM3-9496")
    def test_even_distributed_weight_module_1(self):
        """
        Check if VM migrated on the normalutilized host
        """
        assert (
            sch_helpers.migrate_vm_by_maintenance_and_get_destination_host(
                src_host=sla_conf.HOSTS[0], vm_name=sla_conf.VM_NAME[0]
            ) == sla_conf.HOSTS[1]
        )


@bz({'1316456': {}})
@u_libs.attr(tier=1)
@pytest.mark.usefixtures(update_cluster_policy_to_none.__name__)
class TestCheckClusterPoliciesParameters(u_libs.SlaTest):
    """
    Check different values for cluster policy parameters:
        1) CpuOverCommitDurationMinutes - min=1; max=99
        2) HighUtilization - min=50; max=99
        3) LowUtilization - min=0; max=49
    Added, because the bug
        https://bugzilla.redhat.com/show_bug.cgi?id=1070704
    """
    __test__ = True

    @polarion("RHEVM3-14841")
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
        low_utilization = random.randint(0, 49)
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
