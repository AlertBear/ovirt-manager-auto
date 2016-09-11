"""
Scheduler - Even Vm Count Distribution Test
Check different cases for start, migration and balancing when cluster policy
is Vm_Evenly_Distribute
"""
import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import pytest
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from art.test_handler.tools import polarion
from rhevmtests.sla.fixtures import (
    update_cluster,
    update_cluster_to_default_parameters,  # flake8: noqa
    configure_hosts_power_management,
    choose_specific_host_as_spm,
    deactivate_hosts,
    run_once_vms,
    stop_host_network,
    stop_vms,
    update_vms
)

logger = logging.getLogger(__name__)
host_as_spm = 0


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    run_once_vms.__name__,
    update_cluster.__name__
)
class BaseEvenVmCountDistribution(u_libs.SlaTest):
    """
    Base class for EvenVmCountDistribution policy
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_EVEN_VM_DISTRIBUTION,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_EVCD_PARAMS
    }


@pytest.mark.usefixtures(deactivate_hosts.__name__)
class BaseEvenVmCountDistributionTwoHosts(BaseEvenVmCountDistribution):
    """
    Test cases with 2 hosts, so in setup need to deactivate third host
    """
    hosts_to_maintenance = [2]


class TestBalancingWithDefaultParameters(BaseEvenVmCountDistributionTwoHosts):
    """
    Positive: test balancing under vm_evenly_distributed cluster policy with
    default parameters
    """
    __test__ = True
    vms_to_run = dict(
        (
            conf.VM_NAME[i], {conf.VM_RUN_ONCE_HOST: 0}
        ) for i in xrange(conf.NUM_OF_VMS)
    )

    @polarion("RHEVM3-5565")
    def test_balancing(self):
        """
        Check that three VM's migrate on the host_2
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
            sampler_timeout=conf.LONG_BALANCE_TIMEOUT
        )


class TestNoHostForMigration(BaseEvenVmCountDistributionTwoHosts):
    """
    Positive: Run equal number of VM's on two hosts and check
    that no migration happens under vm_evenly_distributed cluster policy
    """
    __test__ = True
    vms_to_run = conf.DEFAULT_VMS_TO_RUN

    @polarion("RHEVM3-5566")
    def test_balancing(self):
        """
        Check that migration does not happen
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST - 1,
            negative=True
        )


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVm(BaseEvenVmCountDistributionTwoHosts):
    """
    Positive: Start the VM under vm_evenly_distributed cluster policy,
    when on the host_1(SPM) and on the host_2 equal number of VM's
    """
    __test__ = True
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.VM_NAME[2]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[3]: {conf.VM_RUN_ONCE_HOST: 1}
    }
    vms_to_stop = [conf.VM_NAME[4]]

    @polarion("RHEVM3-5568")
    def test_start_vm(self):
        """
        Start the VM and check that VM starts on the correct host
        """
        u_libs.testflow.step("Start the VM %s", conf.VM_NAME[4])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[4])
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
            sampler_timeout=conf.LONG_BALANCE_TIMEOUT
        )


@u_libs.attr(tier=3)
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    deactivate_hosts.__name__,
    configure_hosts_power_management.__name__,
    update_vms.__name__,
    run_once_vms.__name__,
    update_cluster.__name__,
    stop_host_network.__name__
)
class TestHaVmStartOnHostAboveMaxLevel(u_libs.SlaTest):
    """
    Positive: Start VM's under vm_evenly_distributed cluster policy,
    when the host_1(SPM) has two VM's and the host_2 has three HA VM's.
    After killing the host_2 VM's from host_2 must start on the host_1
    """
    __test__ = True
    hosts_to_maintenance = [2]
    hosts_to_pms = [1]
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_EVEN_VM_DISTRIBUTION,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_EVCD_PARAMS
    }
    vms_to_params = dict(
        (
            conf.VM_NAME[i], {conf.VM_HIGHLY_AVAILABLE: True}
        ) for i in xrange(2, 5)
    )
    vms_to_run = conf.DEFAULT_VMS_TO_RUN
    stop_network_on_host = 1

    @polarion("RHEVM3-5570")
    def test_balancing(self):
        """
        Kill the host with HA VM's, VM's from the host_2
        must start on the host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=conf.NUM_OF_VMS,
            sampler_timeout=conf.LONG_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(deactivate_hosts.__name__)
class PutHostToMaintenance(BaseEvenVmCountDistribution):
    """
    Positive: Start VM's under vm_evenly_distributed cluster policy,
    when the host_1(SPM) has two VM's and the host_2 has three VM's
    put host_2 to the maintenance and as result all VM's from
    the host_2 must migrate to the host_3
    """
    __test__ = True
    vms_to_run = conf.DEFAULT_VMS_TO_RUN
    hosts_to_maintenance = [1]

    @polarion("RHEVM3-5567")
    def test_balancing(self):
        """
        Check that all VM's from the host_2 migrate to the host_3
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2],
            expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
            sampler_timeout=conf.LONG_BALANCE_TIMEOUT
        )


class MigrateVmUnderPolicyBase(BaseEvenVmCountDistribution):
    """
    Positive: Start vms under vm_evenly_distributed cluster policy,
    when on host_1(SPM) one vm, on host_2 three vms and on host_3 one vm,
    migrate one of vms from host_2, without specify destination host, engine
    must migrate vm on host_3
    """
    __test__ = True
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[2]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[3]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[4]: {conf.VM_RUN_ONCE_HOST: 2}
    }

    @polarion("RHEVM3-5569")
    def test_check_migration(self):
        """
        Migrate vm from host_2 and check number of vms on the host_3
        """
        u_libs.testflow.step("Migrate the VM %s", conf.VM_NAME[1])
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2],
            expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST - 1,
            sampler_timeout=conf.LONG_BALANCE_TIMEOUT
        )
