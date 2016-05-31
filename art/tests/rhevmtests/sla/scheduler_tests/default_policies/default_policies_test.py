"""
Scheduler - Rhevm Cluster Policies Test
Check different cases for migration when cluster police is Evenly Distributed
and Power Saving
"""
import random

import art.unittest_lib as u_libs
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from art.test_handler.tools import polarion  # pylint: disable=E0611
from rhevmtests.sla.scheduler_tests.fixtures import *  # flake8: noqa

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def setup_default_policies(request):
    """
    1) Change engine-config LowUtilizationForEvenlyDistribute to 35
    """
    def fin():
        """
        1) Stop all GE VM's and update them to default parameters
        2) Release all hosts from CPU load
        3) Change engine-config LowUtilizationForEvenlyDistribute to 0
        """
        sla_helpers.stop_all_ge_vms_and_update_to_default_params()
        sch_helpers.stop_cpu_load_on_all_hosts()
        sch_helpers.change_engine_config_low_utilization_value(0)
    request.addfinalizer(fin)
    assert sch_helpers.change_engine_config_low_utilization_value(
        conf.LOW_UTILIZATION_VALUE
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu", [{conf.CPU_LOAD_50: [1]}], indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_power_saving"
)
@polarion("RHEVM3-9498")
def test_power_saving_balance_module_1():
    """
    VM run on under utilized host and must migrate to normal utilized host
    """
    assert sch_helpers.is_balancing_happen(
        host_name=conf.HOSTS[1], expected_num_of_vms=2
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu", [{conf.CPU_LOAD_100: [1]}], indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_power_saving"
)
@polarion("RHEVM3-9489")
def test_power_saving_balance_module_2():
    """
    VM run on under utilized host, but another hosts in cluster over or under
    utilized, so VM must stay on old host
    """
    assert not sch_helpers.is_balancing_happen(
        host_name=conf.HOSTS[0], expected_num_of_vms=1, negative=True
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu",
    [{conf.CPU_LOAD_50: [1], conf.CPU_LOAD_100: [2]}],
    indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_power_saving"
)
@polarion("RHEVM3-9490")
def test_power_saving_balance_module_3():
    """
    VM run on under utilized host, check that VM migrate
    to normal utilized host and not to over utilized host
    """
    assert sch_helpers.is_balancing_happen(
        host_name=conf.HOSTS[1], expected_num_of_vms=2
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu", [{conf.CPU_LOAD_50: range(2)}], indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_power_saving",
    "activate_host"
)
@polarion("RHEVM3-9492")
def test_power_saving_weight_module_1():
    """
    VM run on normal utilized host, we put host to
    maintenance and check that VM migrated to normal utilized host
    """
    assert (
        sch_helpers.migrate_vm_by_maintenance_and_get_destination_host(
            src_host=conf.HOSTS[0], vm_name=conf.VM_NAME[0]
        ) == conf.HOSTS[1]
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu", [{conf.CPU_LOAD_100: range(2)}], indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_even_distributed"
)
@polarion("RHEVM3-9493")
def test_even_distributed_balance_module_1():
    """
    VM run on over utilized host and must migrate to normal utilized host
    """
    assert sch_helpers.is_balancing_happen(
        host_name=conf.HOSTS[2], expected_num_of_vms=2
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu", [{conf.CPU_LOAD_100: range(3)}], indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_even_distributed"
)
@polarion("RHEVM3-9494")
def test_even_distributed_balance_module_2():
    """
    VM run on over utilized host, but other cluster hosts also over utilized,
    so VM must stay on old host
    """
    assert not sch_helpers.is_balancing_happen(
        host_name=conf.HOSTS[0], expected_num_of_vms=1, negative=True
    )


@u_libs.attr(team="sla", tier=2)
@pytest.mark.parametrize(
    "load_hosts_cpu", [{conf.CPU_LOAD_100: [2]}], indirect=True
)
@pytest.mark.usefixtures(
    "setup_default_policies",
    "start_vms_on_three_hosts",
    "load_hosts_cpu",
    "update_cluster_policy_to_even_distributed",
    "activate_host"
)
@polarion("RHEVM3-9496")
def test_even_distributed_weight_module_1():
    """
    VM run on normal utilized host, we put host to
    maintenance and check that VM migrated on normal utilized host
    """
    assert (
        sch_helpers.migrate_vm_by_maintenance_and_get_destination_host(
            src_host=conf.HOSTS[0], vm_name=conf.VM_NAME[0]
        ) == conf.HOSTS[1]
    )


@u_libs.attr(team="sla", tier=1)
@pytest.mark.usefixtures("update_cluster_policy_to_none")
@polarion("RHEVM3-14841")
def test_check_cluster_policies_parameters():
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
        conf.POLICY_EVEN_DISTRIBUTION: {
            conf.HIGH_UTILIZATION: high_utilization,
            conf.OVER_COMMITMENT_DURATION: duration
        },
        conf.POLICY_POWER_SAVING: {
            conf.HIGH_UTILIZATION: high_utilization,
            conf.LOW_UTILIZATION: low_utilization,
            conf.OVER_COMMITMENT_DURATION: duration

        }
    }
    for policy, params in policies_params.iteritems():
        assert ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=policy,
            **params
        )
