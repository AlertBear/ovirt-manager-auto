"""
Scheduler - Affinity Test
Check different cases for migration and starting of VM's,
when VM's in different or in the same affinities groups
"""
import logging

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import pytest
import rhevmtests.helpers as rhevm_helpers
import rhevmtests.sla.config as conf
from art.test_handler.tools import polarion, bz
from rhevmtests.sla.fixtures import (
    choose_specific_host_as_spm,
    create_additional_cluster,
    deactivate_hosts,
    run_once_vms,
    start_vms,
    update_vms,
    update_vms_to_default_parameters,
    update_vms_memory_to_hosts_memory
)
from rhevmtests.sla.scheduler_tests.fixtures import create_affinity_groups


logger = logging.getLogger(__name__)
host_as_spm = 1


def change_arem_state(enable):
    """
    Enable or disable AREM via engine-config

    Args:
        enable (bool): Enable or disable AREM

    Returns:
        bool: True, if change AREM state action is succeed, otherwise False
    """
    state_msg = "Enable" if enable else "Disable"
    arem_state = "true" if enable else "false"
    logger.info("%s AREM manager via engine-config", state_msg)
    cmd = ["{0}={1}".format(conf.AREM_OPTION, arem_state)]
    if not conf.ENGINE.engine_config(action='set', param=cmd).get('results'):
        logger.error("Failed to set %s option to false", conf.AREM_OPTION)
        return False
    if not rhevm_helpers.wait_for_engine_api():
        return False
    return True


@pytest.fixture(scope="module", autouse=True)
def init_affinity_test(request):
    """
    1) Disable AREM manager
    2) Change cluster overcommitment
    """
    def fin():
        """
        1) Change cluster overcommitment
        2) Enable AREM manager
        """
        ll_clusters.updateCluster(
            positive=True, cluster=conf.CLUSTER_NAME[0], mem_ovrcmt_prc=200
        )
        change_arem_state(enable=True)
    request.addfinalizer(fin)

    assert change_arem_state(enable=False)
    assert ll_clusters.updateCluster(
        positive=True, cluster=conf.CLUSTER_NAME[0], mem_ovrcmt_prc=100
    )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    init_affinity_test.__name__
)
class BaseAffinity(u_libs.SlaTest):
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


@u_libs.attr(tier=1)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
class TestStartVmsUnderHardPositiveAffinity(BaseStartVms):
    """
    Start VM's that placed into the same hard positive affinity group,
    and check if they started on the same host
    """
    __test__ = True
    affinity_groups = {
        "hard_positive_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5539")
    def test_vms_hosts(self):
        """
        Check where VM's started
        """
        u_libs.testflow.step("Check if VM's started on the same host")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@u_libs.attr(tier=2)
class TestStartVmsUnderSoftPositiveAffinity(BaseStartVms):
    """
    Start VM's that placed into the same soft positive affinity group,
    and check if they started on the same host
    """
    __test__ = True

    affinity_groups = {
        "soft_positive_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5541")
    def test_vms_hosts(self):
        """
        Check where vms started
        """
        u_libs.testflow.step("Check if VM's started on the same host")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@u_libs.attr(tier=1)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
class TestStartVmsUnderHardNegativeAffinity(BaseStartVms):
    """
    Start VM's that placed into the same hard negative affinity group,
    and check if they started on different hosts
    """
    __test__ = True
    affinity_groups = {
        "hard_negative_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5553")
    def test_vms_host(self):
        """
        Check where VM's started
        """
        u_libs.testflow.step("Check if VM's started on different hosts")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@u_libs.attr(tier=2)
class TestStartVmsUnderSoftNegativeAffinity(BaseStartVms):
    """
    Start VM's that placed into the same soft negative affinity group,
    and check if they started on different hosts
    """
    __test__ = True
    affinity_groups = {
        "soft_negative_start_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False

    @polarion("RHEVM3-5542")
    def test_vms_host(self):
        """
        Check where VM's started
        """
        u_libs.testflow.step("Check if VM's started on different hosts")
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
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}
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
        u_libs.testflow.step("Migrate VM %s", conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])
        u_libs.testflow.step(
            "Check if VM %s migrated on the host %s second VM %s",
            conf.VM_NAME[0], flow_msg, conf.VM_NAME[1]
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        ) == positive


@u_libs.attr(tier=1)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
class TestMigrateVmUnderHardPositiveAffinity(BaseMigrateVm):
    """
    Migrate VM under hard positive affinity,
    VM must migrate on the same host, where second vm run
    """
    __test__ = True
    affinity_groups = {
        "hard_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5557")
    def test_vm_migration(self):
        """
        Check if VM's succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=True)


@u_libs.attr(tier=2)
class TestMigrateVmUnderSoftPositiveAffinity(BaseMigrateVm):
    """
    Migrate VM under soft positive affinity,
    VM must migrate on the same host, where second VM run
    """
    __test__ = True
    affinity_groups = {
        "soft_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5543")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=True)


@u_libs.attr(tier=1)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_TWO_HOSTS)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
class TestMigrateVmUnderHardNegativeAffinity(BaseMigrateVm):
    """
    Migrate VM under hard negative affinity,
    VM must migrate on different from second VM host
    """
    __test__ = True
    affinity_groups = {
        "hard_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5558")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=False)


@u_libs.attr(tier=2)
class TestMigrateVmUnderSoftNegativeAffinity(BaseMigrateVm):
    """
    Migrate VM under soft negative affinity,
    so VM must migrate on different from second VM host
    """
    __test__ = True
    affinity_groups = {
        "soft_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5544")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        self.check_vm_host_after_migration(positive=False)


@u_libs.attr(tier=2)
class TestNegativeMigrateVmUnderHardPositiveAffinity(BaseMigrateVm):
    """
    Negative: Migrate VM under hard positive affinity to the opposite host
    """
    __test__ = True
    affinity_groups = {
        "negative_hard_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5559")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        u_libs.testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[2]
        )
        assert not ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[2]
        )


@u_libs.attr(tier=2)
class TestMigrateVmOppositeUnderSoftPositiveAffinity(BaseMigrateVm):
    """
    Migrate VM under soft positive affinity to the opposite host
    """
    __test__ = True
    affinity_groups = {
        "opposite_soft_positive_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5546")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        u_libs.testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[2]
        )
        assert ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[2]
        )


@u_libs.attr(tier=2)
class TestNegativeMigrateVmUnderHardNegativeAffinity(BaseMigrateVm):
    """
    Negative: Migrate vm under hard negative affinity
    to the host where second VM placed
    """
    __test__ = True
    affinity_groups = {
        "negative_hard_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5545")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        u_libs.testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[1]
        )
        assert not ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[1]
        )


@u_libs.attr(tier=2)
class TestMigrateVmSameUnderSoftNegativeAffinity(BaseMigrateVm):
    """
    Migrate VM under soft negative affinity to the host where second VM placed
    """
    __test__ = True
    affinity_groups = {
        "same_soft_negative_migrate_vm": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5547")
    def test_vm_migration(self):
        """
        Check if VM succeeds to migrate
        """
        u_libs.testflow.step(
            "Migrate VM %s on host %s", conf.VM_NAME[0], conf.HOSTS[1]
        )
        assert ll_vms.migrateVm(
            positive=True, vm=conf.VM_NAME[0], host=conf.HOSTS[1]
        )


@u_libs.attr(tier=2)
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
    __test__ = True
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

    @polarion("RHEVM3-5560")
    def test_affinity_group(self):
        """
        Check if VM removed from the affinity group
        """
        affinity_group_name = self.affinity_groups.keys()[0]
        u_libs.testflow.step(
            "Check that VM %s removed by the engine from affinity group %s",
            conf.VM_NAME[0], affinity_group_name
        )
        assert not ll_clusters.vm_exists_under_affinity_group(
            affinity_name=affinity_group_name,
            cluster_name=conf.CLUSTER_NAME[0],
            vm_name=conf.VM_NAME[0]
        )


@u_libs.attr(tier=2)
class TestPutHostToMaintenanceUnderHardPositiveAffinity(BaseStartVms):
    """
    Put host with VM's placed under hard positive affinity group to maintenance
    """
    __test__ = True
    affinity_groups = {
        "maintenance_hard_positive_affinity_group": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM3-5563")
    def test_vms_destination(self):
        """
        Check that after deactivate hosts vms migrated on the same host
        """
        vm_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])
        u_libs.testflow.step("Deactivate host %s", vm_host)
        assert not ll_hosts.deactivate_host(positive=True, host=vm_host)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    deactivate_hosts.__name__
)
class TestPutHostToMaintenanceUnderHardNegativeAffinity(BaseMigrateVm):
    """
    Put host to maintenance under hard negative affinity
    and check vms migration destination
    """
    __test__ = True
    affinity_groups = {
        "maintenance_hard_negative_affinity_group": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    hosts_to_maintenance = [0]

    @polarion("RHEVM3-5549")
    def test_check_vms_placement(self):
        """
        Check that after deactivate hosts vms migrated on different hosts
        """
        u_libs.testflow.step(
            "Check if VM %s migrated on the host without second VM %s",
            conf.VM_NAME[0], conf.VM_NAME[1]
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestTwoDifferentAffinitiesScenario1(BaseAffinity):
    """
    Negative: create two affinity groups with the same VM's
    1) hard and positive
    2) soft and negative
    Populate second group with VMS will fail
    because of affinity group rules collision
    """
    __test__ = True
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

    @polarion("RHEVM3-5562")
    def test_second_affinity_group(self):
        """
        Populate second affinity group with VMS
        """
        u_libs.testflow.step(
            "Populate affinity group %s with VM's %s",
            self.additional_affinity_group_name, conf.VM_NAME[:2]
        )
        assert not ll_clusters.populate_affinity_with_vms(
            affinity_name=self.additional_affinity_group_name,
            cluster_name=conf.CLUSTER_NAME[0],
            vms=conf.VM_NAME[:2]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestTwoDifferentAffinitiesScenario2(BaseAffinity):
    """
    Negative: create two affinity groups with the same VM's
    1) hard and negative
    2) soft and positive
    Populate second group with VM's will fail
    because of affinity group rules collision
    """
    __test__ = True
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

    @polarion("RHEVM3-5552")
    def test_second_affinity_group(self):
        """
        Populate second affinity group with VMS
        """
        u_libs.testflow.step(
            "Populate affinity group %s with VM's %s",
            self.additional_affinity_group_name, conf.VM_NAME[:2]
        )
        assert not ll_clusters.populate_affinity_with_vms(
            affinity_name=self.additional_affinity_group_name,
            cluster_name=conf.CLUSTER_NAME[0],
            vms=conf.VM_NAME[:2]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestTwoDifferentAffinitiesScenario3(BaseAffinity):
    """
    Negative: create two affinity groups with the same VM's
    1) hard and negative
    2) hard and positive
    Populate second group with VM's will fail
    because of affinity group rules collision
    """
    __test__ = True
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

    @polarion("RHEVM3-5551")
    def test_second_affinity_group(self):
        """
        Populate second affinity group with VMS
        """
        u_libs.testflow.step(
            "Populate affinity group %s with VM's %s",
            self.additional_affinity_group_name, conf.VM_NAME[:2]
        )
        assert not ll_clusters.populate_affinity_with_vms(
            affinity_name=self.additional_affinity_group_name,
            cluster_name=conf.CLUSTER_NAME[0],
            vms=conf.VM_NAME[:2]
        )


@u_libs.attr(tier=2)
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
    __test__ = True
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

    @polarion("RHEVM3-5548")
    def test_ha_vm(self):
        """
        1) Add HA VM to affinity group
        2) Kill HA VM
        3) Check that HA VM failed to start because affinity filter
        4) Stop VM VM_NAME[1]
        5) Check that HA VM succeeds to start
        """
        u_libs.testflow.step(
            "Add VM %s to affinity group %s",
            conf.VM_NAME[2], self.affinity_group_name
        )
        assert ll_clusters.populate_affinity_with_vms(
            affinity_name=self.affinity_group_name,
            cluster_name=conf.CLUSTER_NAME[0],
            vms=conf.VM_NAME[2:3]
        )
        ha_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[2])
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=ha_host
        )
        u_libs.testflow.step("Kill HA VM %s", conf.VM_NAME[2])
        assert ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=conf.VM_NAME[2]
        )
        u_libs.testflow.step("Wait for HA VM %s to be down", conf.VM_NAME[2])
        assert ll_vms.waitForVMState(vm=conf.VM_NAME[2], state=conf.VM_DOWN)
        u_libs.testflow.step(
            "Check that HA VM %s fails to start", conf.VM_NAME[2]
        )
        assert not ll_vms.waitForVMState(vm=conf.VM_NAME[2], timeout=120)
        u_libs.testflow.step("Stop VM %s", conf.VM_NAME[1])
        assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME[1])
        u_libs.testflow.step(
            "Check that HA VM %s succeeds to start", conf.VM_NAME[2]
        )
        assert ll_vms.waitForVMState(
            vm=conf.VM_NAME[2], state=conf.VM_POWERING_UP
        )


@u_libs.attr(tier=2)
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
    __test__ = True
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
            u_libs.testflow.step(
                "Kill QEMU process of VM %s on host %s", vm_name, vm_host
            )
            assert ll_hosts.kill_vm_process(
                resource=host_resource, vm_name=vm_name
            )
        u_libs.testflow.step("Wait until both HA VM's will change state to UP")
        assert ll_vms.waitForVmsStates(positive=True, names=conf.VM_NAME[:2])
        u_libs.testflow.step(
            "Check that both HA VM's started on the same host"
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) ==
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )


@u_libs.attr(tier=2)
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
    __test__ = True
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

    @polarion("RHEVM3-5561")
    def test_start_vms(self):
        """
        Check that affinity policy not prevent to start VM's
        """
        u_libs.testflow.step("Check if VM's started on different hosts")
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )
