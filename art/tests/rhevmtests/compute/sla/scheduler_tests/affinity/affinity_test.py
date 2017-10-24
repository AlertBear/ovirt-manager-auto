"""
Scheduler - Affinity Test
Check different cases for migration and starting of VM's,
when VM's in different or in the same affinities groups
"""

import pytest
import rhevmtests.compute.sla.config as conf
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.compute.sla.fixtures import (
    choose_specific_host_as_spm,
    create_additional_cluster,
    deactivate_hosts,
    run_once_vms,
    start_vms,
    update_vms,
    update_vms_to_default_parameters,
    update_vms_memory_to_hosts_memory
)

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch_policies
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.helpers as rhevm_helpers
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, tier1, tier2, SlaTest
from rhevmtests.compute.sla.scheduler_tests.fixtures import (
    create_affinity_groups
)

host_as_spm = 1


@pytest.fixture(scope="module")
def init_affinity_test(request):
    """
    1) Create the affinity scheduler policy
    2) Update the cluster with the affinity scheduler policy
    """
    def fin():
        """
        1) Update the cluster scheduler policy to the 'none'
        2) Remove the affinity scheduler policy
        """
        result_list = list()
        result_list.append(
            ll_clusters.updateCluster(
                positive=True,
                cluster=conf.CLUSTER_NAME[0],
                scheduling_policy=conf.POLICY_NONE
            )
        )
        result_list.append(
            ll_sch_policies.remove_scheduling_policy(
                policy_name=conf.AFFINITY_POLICY_NAME
            )
        )
        assert all(result_list)
    request.addfinalizer(fin)

    sch_helpers.add_scheduler_policy(
        policy_name=conf.AFFINITY_POLICY_NAME,
        policy_units={
            conf.SCH_UNIT_TYPE_FILTER: conf.DEFAULT_SCHEDULER_FILTERS,
            conf.SCH_UNIT_TYPE_WEIGHT: conf.AFFINITY_SCHEDULER_WEIGHTS
        },
        additional_params={
            conf.PREFERRED_HOSTS: {conf.WEIGHT_FACTOR: 99},
            conf.VM_TO_HOST_AFFINITY_UNIT: {conf.WEIGHT_FACTOR: 10}
        }
    )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        mem_ovrcmt_prc=100,
        scheduling_policy=conf.AFFINITY_POLICY_NAME
    )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    init_affinity_test.__name__
)
class BaseAffinity(SlaTest):
    """
    Base class for all affinity tests
    """
    pass


@pytest.mark.usefixtures(
    create_affinity_groups.__name__,
    start_vms.__name__
)
class BaseStartVms(BaseAffinity):
    """
    Start VM's under different affinity groups
    """
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False


class TestStartVmsUnderHardPositiveAffinity(BaseStartVms):
    """
    Start VM's that placed into the same hard positive affinity group,
    and check if they started on the same host
    """
    affinity_groups = {
        "hard_positive_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM3-5539")
    def test_vms_hosts(self):
        """
        Check where VM's started
        """
        testflow.step("Check if VM's started on the same host")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


class TestStartVmsUnderSoftPositiveAffinity(BaseStartVms):
    """
    Start VM's that placed into the same soft positive affinity group,
    and check if they started on the same host
    """

    affinity_groups = {
        "soft_positive_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM3-5541")
    def test_vms_hosts(self):
        """
        Check where vms started
        """
        testflow.step("Check if VM's started on the same host")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


class TestStartVmsUnderHardNegativeAffinity(BaseStartVms):
    """
    Start VM's that placed into the same hard negative affinity group,
    and check if they started on different hosts
    """
    affinity_groups = {
        "hard_negative_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM3-5553")
    def test_vms_host(self):
        """
        Check where VM's started
        """
        testflow.step("Check if VM's started on different hosts")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


class TestStartVmsUnderSoftNegativeAffinity(BaseStartVms):
    """
    Start VM's that placed into the same soft negative affinity group,
    and check if they started on different hosts
    """
    affinity_groups = {
        "soft_negative_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-5542")
    def test_vms_host(self):
        """
        Check where VM's started
        """
        testflow.step("Check if VM's started on different hosts")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class BaseMigrateVm(BaseAffinity):
    """
    Migrate VM under different affinity groups
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[2]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        }
    }

    @staticmethod
    def check_vm_host_after_migration(positive):
        """
        1) Migrate VM
        2) Check VM host after migration

        Args:
            positive (bool): Positive or negative behaviour
        """
        flow_msg = "with" if positive else "without"
        testflow.step("Migrate VM %s", conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])
        testflow.step(
            "Check if VM %s migrated on the host %s second VM %s",
            conf.VM_NAME[0], flow_msg, conf.VM_NAME[1]
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        ) == positive


class TestMigrateVmUnderHardPositiveAffinity(BaseMigrateVm):
    """
    Migrate VM under hard positive affinity,
    VM must migrate on the same host, where second vm run
    """
    affinity_groups = {
        "hard_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM3-5557")
    def test_vm_migration(self):
        """
        Check if VM's succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=True)


class TestMigrateVmUnderSoftPositiveAffinity(BaseMigrateVm):
    """
    Migrate VM under soft positive affinity,
    VM must migrate on the same host, where second VM runs
    """
    affinity_groups = {
        "soft_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier2
    @polarion("RHEVM3-5543")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=True)


class TestMigrateVmUnderHardNegativeAffinity(BaseMigrateVm):
    """
    Migrate VM under hard negative affinity,
    VM must migrate on different from second VM host
    """
    affinity_groups = {
        "hard_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier1
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_TWO_HOSTS)
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM3-5558")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=False)


class TestMigrateVmUnderSoftNegativeAffinity(BaseMigrateVm):
    """
    Migrate VM under soft negative affinity,
    so VM must migrate on different from second VM host
    """
    affinity_groups = {
        "soft_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM3-5544")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=False)


class TestNegativeMigrateVmUnderHardPositiveAffinity(BaseMigrateVm):
    """
    Negative: Migrate VM under hard positive affinity to the opposite host
    """
    affinity_groups = {
        "negative_hard_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM3-5559")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[2]
        )
        assert not ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[2]
        )


class TestMigrateVmOppositeUnderSoftPositiveAffinity(BaseMigrateVm):
    """
    Migrate VM under soft positive affinity to the opposite host
    """
    affinity_groups = {
        "opposite_soft_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier2
    @polarion("RHEVM3-5546")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[2]
        )
        assert ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[2]
        )


class TestNegativeMigrateVmUnderHardNegativeAffinity(BaseMigrateVm):
    """
    Negative: Migrate vm under hard negative affinity
    to the host where second VM placed
    """
    affinity_groups = {
        "negative_hard_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM3-5545")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[1]
        )
        assert not ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[1]
        )


class TestMigrateVmSameUnderSoftNegativeAffinity(BaseMigrateVm):
    """
    Migrate VM under soft negative affinity to the host where second VM placed
    """
    affinity_groups = {
        "same_soft_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM3-5547")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[1]
        )
        assert ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[1]
        )


@pytest.mark.usefixtures(
    create_affinity_groups.__name__,
    create_additional_cluster.__name__,
    update_vms.__name__
)
class TestRemoveVmFromAffinityGroupOnClusterChange(BaseAffinity):
    """
    Change VM cluster, and check that VM removed from
    affinity group on the old cluster
    """
    affinity_groups = {
        "cluster_change_affinity_group": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    additional_cluster_name = "affinity_additional_cluster"
    vms_to_params = {
        conf.VM_NAME[0]: {conf.VM_CLUSTER: additional_cluster_name}
    }

    @tier2
    @polarion("RHEVM3-5560")
    def test_affinity_group(self):
        """
        Check if VM removed from the affinity group
        """
        affinity_group_name = self.affinity_groups.keys()[0]
        testflow.step(
            "Check that VM %s removed by the engine from affinity group %s",
            conf.VM_NAME[0], affinity_group_name
        )
        assert not ll_clusters.vm_exists_under_affinity_group(
            affinity_name=affinity_group_name,
            cluster_name=conf.CLUSTER_NAME[0],
            vm_name=conf.VM_NAME[0]
        )


class TestPutHostToMaintenanceUnderHardPositiveAffinity(BaseMigrateVm):
    """
    Put host with VM's placed under hard positive affinity group to maintenance
    """
    affinity_groups = {
        "maintenance_hard_positive_affinity_group": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier2
    @polarion("RHEVM3-5563")
    def test_vms_destination(self):
        """
        Check that after deactivate hosts vms migrated on the same host
        """
        testflow.step("Deactivate host %s", conf.HOSTS[0])
        assert not ll_hosts.deactivate_host(positive=True, host=conf.HOSTS[0])


@pytest.mark.usefixtures(
    deactivate_hosts.__name__
)
class TestPutHostToMaintenanceUnderHardNegativeAffinity(BaseMigrateVm):
    """
    Put host to maintenance under hard negative affinity
    and check vms migration destination
    """
    affinity_groups = {
        "maintenance_hard_negative_affinity_group": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    hosts_to_maintenance = [0]

    @tier2
    @polarion("RHEVM3-5549")
    def test_check_vms_placement(self):
        """
        Check that after deactivate hosts vms migrated on different hosts
        """
        testflow.step(
            "Check if VM %s migrated on the host without second VM %s",
            conf.VM_NAME[0], conf.VM_NAME[1]
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestTwoDifferentAffinitiesScenario1(BaseAffinity):
    """
    Negative: create two affinity groups with the same VM's
    1) hard and positive
    2) soft and negative
    Populate second group with VMS will fail
    because of affinity group rules collision
    """
    additional_affinity_group_name = "affinity_group_scenario_1_2"
    affinity_groups = {
        "affinity_group_scenario_1_1": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        },
        additional_affinity_group_name: {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False
        }
    }

    @tier2
    @polarion("RHEVM3-5562")
    def test_second_affinity_group(self):
        """
        Populate second affinity group with VMS
        """
        testflow.step(
            "Populate affinity group %s with VM's %s",
            self.additional_affinity_group_name, conf.VM_NAME[:2]
        )
        assert not ll_clusters.update_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0],
            old_name=self.additional_affinity_group_name,
            vms=conf.VM_NAME[:2],
            positive=False
        )


@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestTwoDifferentAffinitiesScenario2(BaseAffinity):
    """
    Negative: create two affinity groups with the same VM's
    1) hard and negative
    2) soft and positive
    Populate second group with VM's will fail
    because of affinity group rules collision
    """
    additional_affinity_group_name = "affinity_group_scenario_2_2"
    affinity_groups = {
        "affinity_group_scenario_2_1": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        },
        additional_affinity_group_name: {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False
        }
    }

    @tier2
    @polarion("RHEVM3-5552")
    def test_second_affinity_group(self):
        """
        Populate second affinity group with VMS
        """
        testflow.step(
            "Populate affinity group %s with VM's %s",
            self.additional_affinity_group_name, conf.VM_NAME[:2]
        )
        assert not ll_clusters.update_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0],
            old_name=self.additional_affinity_group_name,
            vms=conf.VM_NAME[:2],
            positive=True
        )


@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestTwoDifferentAffinitiesScenario3(BaseAffinity):
    """
    Negative: create two affinity groups with the same VM's
    1) hard and negative
    2) hard and positive
    Populate second group with VM's will fail
    because of affinity group rules collision
    """
    additional_affinity_group_name = "affinity_group_scenario_3_2"
    affinity_groups = {
        "affinity_group_scenario_3_1": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        },
        additional_affinity_group_name: {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False
        }
    }

    @tier2
    @polarion("RHEVM3-5551")
    def test_second_affinity_group(self):
        """
        Populate second affinity group with VMS
        """
        testflow.step(
            "Populate affinity group %s with VM's %s",
            self.additional_affinity_group_name, conf.VM_NAME[:2]
        )
        assert not ll_clusters.update_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0],
            old_name=self.additional_affinity_group_name,
            vms=conf.VM_NAME[:2],
            positive=True
        )


@pytest.mark.usefixtures(
    deactivate_hosts.__name__,
    create_affinity_groups.__name__,
    update_vms.__name__,
    start_vms.__name__
)
class TestFailedToStartHAVmUnderHardNegativeAffinity(BaseAffinity):
    """
    Kill HA VM and check that VM failed to start,
    because hard negative affinity
    """
    hosts_to_maintenance = [2]
    vms_to_params = {
        conf.VM_NAME[2]: {conf.VM_HIGHLY_AVAILABLE: True}
    }
    affinity_group_name = "failed_ha_affinity_group"
    affinity_groups = {
        affinity_group_name: {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_start = conf.VM_NAME[:3]

    @tier2
    @polarion("RHEVM3-5548")
    def test_ha_vm(self):
        """
        1) Add HA VM to affinity group
        2) Kill HA VM
        3) Check that HA VM failed to start because affinity filter
        4) Stop VM VM_NAME[1]
        5) Check that HA VM succeeds to start
        """
        testflow.step(
            "Add VM %s to affinity group %s",
            conf.VM_NAME[2], self.affinity_group_name
        )
        assert ll_clusters.update_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0],
            old_name=self.affinity_group_name,
            vms=conf.VM_NAME[:3],
            positive=False
        )
        ha_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[2])
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=ha_host
        )
        testflow.step("Kill HA VM %s", conf.VM_NAME[2])
        assert ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=conf.VM_NAME[2]
        )
        testflow.step("Wait for HA VM %s to be down", conf.VM_NAME[2])
        assert ll_vms.waitForVMState(vm=conf.VM_NAME[2], state=conf.VM_DOWN)
        testflow.step(
            "Check that HA VM %s fails to start", conf.VM_NAME[2]
        )
        assert not ll_vms.waitForVMState(vm=conf.VM_NAME[2], timeout=120)
        testflow.step("Stop VM %s", conf.VM_NAME[1])
        assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME[1])
        testflow.step(
            "Check that HA VM %s succeeds to start", conf.VM_NAME[2]
        )
        assert ll_vms.waitForVMState(
            vm=conf.VM_NAME[2], state=conf.VM_POWERING_UP
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    create_affinity_groups.__name__,
    start_vms.__name__
)
class TestStartHAVmsUnderHardPositiveAffinity(BaseAffinity):
    """
    Start two HA VM's under hard positive affinity, kill them and
    check that they started on the same host
    """
    vms_to_params = {
        conf.VM_NAME[0]: {conf.VM_HIGHLY_AVAILABLE: True},
        conf.VM_NAME[1]: {conf.VM_HIGHLY_AVAILABLE: True}
    }
    affinity_groups = {
        "start_ha_vms": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_state = conf.VM_UP
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-5550")
    def test_ha_vms(self):
        """
        1) Kill both HA VM's
        2) Check if HA VM's start on the same host
        """
        vm_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=vm_host
        )
        for vm_name in conf.VM_NAME[:2]:
            testflow.step(
                "Kill QEMU process of VM %s on host %s", vm_name, vm_host
            )
            assert ll_hosts.kill_vm_process(
                resource=host_resource, vm_name=vm_name
            )

        testflow.step(
            "Wait until both HA VM's %s will change state to %s",
            conf.VM_NAME[:2], conf.VM_POWERING_UP
        )
        assert ll_vms.waitForVmsStates(
            positive=True, names=conf.VM_NAME[:2], states=conf.VM_POWERING_UP
        )

        testflow.step(
            "Check that both HA VM's started on the same host"
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@pytest.mark.usefixtures(
    update_vms_memory_to_hosts_memory.__name__,
    update_vms_to_default_parameters.__name__,
    create_affinity_groups.__name__,
    start_vms.__name__
)
class TestSoftPositiveAffinityVsMemoryFilter(BaseAffinity):
    """
    Change memory of VM's to prevent possibility to start two VM's on the same
    host and check if soft positive affinity not prevent this
    """
    update_vms_memory = conf.VM_NAME[:2]
    update_to_default_params = conf.VM_NAME[:2]
    affinity_groups = {
        "memory_vs_soft_affinity": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_start = conf.VM_NAME[:2]

    @tier2
    @polarion("RHEVM3-5561")
    def test_start_vms(self):
        """
        Check that affinity policy not prevent to start VM's
        """
        testflow.step("Check if VM's started on different hosts")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )
