"""
Host To VM affinity tests
"""
import pytest
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    activate_hosts,
    choose_specific_host_as_spm,
    configure_hosts_power_management,
    migrate_he_vm,
    run_once_vms,
    skip_if_not_he_environment,
    stop_host_network,
    stop_vms,
    update_cluster,
    update_vms,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch_policies
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, tier1, tier2, tier3, SlaTest
from rhevmtests.compute.sla.scheduler_tests.fixtures import (
    create_affinity_groups,
    load_hosts_cpu
)

host_as_spm = 2
he_dst_host = 2


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
        assert ll_sch_policies.remove_scheduling_policy(
            policy_name=conf.AFFINITY_POLICY_NAME
        )
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


@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    choose_specific_host_as_spm.__name__,
    init_affinity_test.__name__,
    update_cluster.__name__
)
class BaseHostAffinity(SlaTest):
    """
    Base class for all affinity tests
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.AFFINITY_POLICY_NAME
    }

    @staticmethod
    def check_vm_host(vm_name, host_name):
        """
        Check if the VM started on the correct host

        Args:
            vm_name (str): VM name
            host_name (str): Host name

        Returns:
            bool: True, if the VM started on correct host, otherwise False
        """
        testflow.step(
            "Check if the VM %s started on the host %s", vm_name, host_name
        )
        return ll_vms.get_vm_host(vm_name=vm_name) == host_name

    @staticmethod
    def start_vm(vm_name):
        """
        Start the VM

        Args:
            vm_name (str): VM name

        Returns:
            bool: True, if the VM started, otherwise False
        """
        testflow.step("Start the VM %s", vm_name)
        return ll_vms.startVm(positive=True, vm=vm_name)

    @staticmethod
    def migrate_vm(vm_name):
        """
        Migrate the VM

        Args:
            vm_name (str): VM name

        Returns:
            bool: True, if migration succeeds, otherwise False
        """
        testflow.step("Migrate the VM %s", vm_name)
        return ll_vms.migrateVm(positive=True, vm=vm_name)


@pytest.mark.usefixtures(create_affinity_groups.__name__)
class BaseHostAffinityStartVm(BaseHostAffinity):
    """
    Base class for all tests that start VM
    """
    affinity_groups = None


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmUnderHostAffinity01(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard positive affinity group with the host
    """
    affinity_groups = {
        "{0}_01".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-17586")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmUnderHostAffinity02(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group with the host
    """
    affinity_groups = {
        "{0}_02".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-17587")
    def test_vm_start(self):
        """
        Check that the engine does not start VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(run_once_vms.__name__)
class TestStartVmUnderHostAffinity03(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard positive affinity group with the host
    and to another hard positive affinity group with a VM
    """
    affinity_groups = {
        "{0}_03_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1,
        "{0}_03_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_1
    }
    vms_to_run = {conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}}

    @tier2
    @polarion("RHEVM-17588")
    def test_vm_start(self):
        """
        Check that the VM fails to start
        """
        assert not self.start_vm(vm_name=conf.VM_NAME[0])


@pytest.mark.usefixtures(run_once_vms.__name__)
class TestStartVmUnderHostAffinity04(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group with the host
    and to another hard negative affinity group with VM's
    """
    affinity_groups = {
        "{0}_04_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_2,
        "{0}_04_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_run = conf.VMS_TO_RUN_0

    @tier2
    @polarion("RHEVM-17589")
    def test_vm_start(self):
        """
        Check that the VM fails to start
        """
        assert not self.start_vm(vm_name=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    stop_vms.__name__
)
class TestStartVmUnderHostAffinity05(BaseHostAffinityStartVm):
    """
    Start the VM that placed into soft positive affinity group with the host
    and to another hard positive affinity group with a VM
    """
    affinity_groups = {
        "{0}_05_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_3,
        "{0}_05_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_1
    }
    vms_to_run = {conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}}
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM-17590")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-1
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[1]
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    stop_vms.__name__
)
class TestStartVmUnderHostAffinity06(BaseHostAffinityStartVm):
    """
    Start the VM that placed into soft negative affinity group with the host
    and to another hard negative affinity group with VM's
    """
    affinity_groups = {
        "{0}_06_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_4,
        "{0}_06_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_run = conf.VMS_TO_RUN_0
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM-17591")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    stop_vms.__name__
)
class TestStartVmUnderHostAffinity07(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group with the host
    and other VM's, when VM to VM affinity disabled
    """
    affinity_groups = {
        "{0}_07".format(conf.AFFINITY_START_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: False
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }
    vms_to_run = conf.VMS_TO_RUN_0
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM-18192")
    def test_vm_start(self):
        """
        Check that the engine does not start VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmUnderHostAffinity08(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group
    with multiple hosts
    """
    affinity_groups = {
        "{0}_08".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_5
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-19279")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-2
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[2]
        )


@pytest.mark.usefixtures(run_once_vms.__name__)
class BaseHostAffinityMigrateVm(BaseHostAffinityStartVm):
    """
    Base class for all tests that migrate VM
    """
    vms_to_run = {conf.VM_NAME[0]: {}}


class TestMigrateVmUnderHostAffinity01(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into hard positive affinity group with the host
    """
    affinity_groups = {
        "{0}_01".format(
            conf.AFFINITY_MIGRATE_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-17592")
    def test_vm_migration(self):
        """
        Check that the engine migrates VM-0 on the host-0
        """
        assert not self.migrate_vm(vm_name=conf.VM_NAME[0])


class TestMigrateVmUnderHostAffinity02(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into hard negative affinity group with the host
    """
    affinity_groups = {
        "{0}_02".format(
            conf.AFFINITY_MIGRATE_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_2
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-17593")
    def test_vm_migration(self):
        """
        Check that the engine does not migrate the VM-0 on the host-0
        """
        assert self.migrate_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


class TestMigrateVmUnderHostAffinity03(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into soft positive affinity group with the host
    """
    affinity_groups = {
        "{0}_03".format(
            conf.AFFINITY_MIGRATE_VM_TEST
        ): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: True,
                conf.AFFINITY_GROUP_ENFORCING: False
            },
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:1],
            conf.AFFINITY_GROUP_HOSTS: [0, 1]
        }
    }

    @tier2
    @polarion("RHEVM-17594")
    def test_vm_migration(self):
        """
        Check that the engine does not migrate the VM-0 on the host-2
        """
        assert self.migrate_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[2]
        )


class TestMigrateVmUnderHostAffinity04(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into soft negative affinity group with the host
    """
    affinity_groups = {
        "{0}_04".format(
            conf.AFFINITY_MIGRATE_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_4
    }

    @tier2
    @polarion("RHEVM-17595")
    def test_vm_migration(self):
        """
        Check that the engine does not migrate the VM-0 on the host-0
        """
        assert self.migrate_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class TestMigrateVmUnderHostAffinity05(BaseHostAffinity):
    """
    Migrate the VM that placed into hard positive affinity group with hosts
    and with the VM
    """
    vms_to_params = {
        conf.VM_NAME[1]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [2]
        }
    }
    vms_to_run = conf.VMS_TO_RUN_2
    affinity_groups = {
        "{0}_05".format(conf.AFFINITY_MIGRATE_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: True,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: True,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0, 1],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM-18193")
    def test_vm_migration(self):
        """
        Check that the engine can not migrate the VM-0
        """
        assert not self.migrate_vm(vm_name=conf.VM_NAME[0])


class TestMigrateVmUnderHostAffinity06(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into hard negative affinity group with the host
    and with the VM
    """
    affinity_groups = {
        "{0}_06".format(conf.AFFINITY_MIGRATE_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_run = conf.VMS_TO_RUN_2

    @tier2
    @polarion("RHEVM-18194")
    def test_vm_migration(self):
        """
        Check that the engine can not migrate the VM-0
        """
        assert not self.migrate_vm(vm_name=conf.VM_NAME[0])


class TestMigrateVmUnderHostAffinity07(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into hard negative affinity group with the host
    and with the VM, when the VM to VM affinity disabled
    """
    affinity_groups = {
        "{0}_07".format(conf.AFFINITY_MIGRATE_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUPS_ENABLED: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_run = conf.VMS_TO_RUN_2

    @tier2
    @polarion("RHEVM-18196")
    def test_vm_migration(self):
        """
        Check that the engine does not migrate the VM-0 on the host-0
        """
        assert self.migrate_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


class TestMigrateVmUnderHostAffinity08(BaseHostAffinityMigrateVm):
    """
    Migrate the VM that placed into hard positive affinity group
    with multiple hosts
    """
    affinity_groups = {
        "{0}_08".format(conf.AFFINITY_MIGRATE_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: True,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0, 1],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:1]
        }
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-19280")
    def test_vm_migration(self):
        """
        Check that the engine can migrate the VM-0
        """
        assert self.migrate_vm(vm_name=conf.VM_NAME[0])


@pytest.mark.usefixtures(activate_hosts.__name__)
class BaseHostAffinityPutHostToMaintenance(BaseHostAffinityMigrateVm):
    """
    Base class for all tests that need to put host to the maintenance
    """
    hosts_to_activate_indexes = [0]


class TestMaintenanceUnderHostAffinity01(BaseHostAffinityPutHostToMaintenance):
    """
    Put the host with the VM to the maintenance, when both host and VM placed
    under the same hard positive affinity group
    """
    affinity_groups = {
        "{0}_01".format(
            conf.AFFINITY_MAINTENANCE_HOST_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1
    }

    @tier2
    @polarion("RHEVM-17596")
    def test_host_maintenance(self):
        """
        Check that the engine can not put the host-0 to the maintenance
        """
        assert not ll_hosts.deactivate_host(positive=True, host=conf.HOSTS[0])


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    activate_hosts.__name__
)
class TestMaintenanceUnderHostAffinity02(BaseHostAffinityStartVm):
    """
    Put the host with the VM to the maintenance, when both host and VM placed
    under the same hard negative affinity group
    """
    affinity_groups = {
        "{0}_02".format(
            conf.AFFINITY_MAINTENANCE_HOST_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1}
    }
    hosts_to_activate_indexes = [1]

    @tier2
    @polarion("RHEVM-17597")
    def test_host_maintenance(self):
        """
        Check that the engine migrates the VM-0 on the host-2
        """
        assert ll_hosts.deactivate_host(
            positive=True, host=conf.HOSTS[1], host_resource=conf.VDS_HOSTS[1]
        )
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[2]
        )


class TestMaintenanceUnderHostAffinity03(BaseHostAffinityPutHostToMaintenance):
    """
    Put the host with the VM to the maintenance, when both host and VM placed
    under the same soft positive affinity group
    """
    affinity_groups = {
        "{0}_03".format(
            conf.AFFINITY_MAINTENANCE_HOST_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_3
    }

    @tier2
    @polarion("RHEVM-17598")
    def test_host_maintenance(self):
        """
        Check that the engine can deactivate the host-0
        """
        assert ll_hosts.deactivate_host(
            positive=True, host=conf.HOSTS[0], host_resource=conf.VDS_HOSTS[0]
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    activate_hosts.__name__
)
class TestMaintenanceUnderHostAffinity04(BaseHostAffinityStartVm):
    """
    Put the host with the VM to the maintenance, when both host and VM placed
    under the same soft negative affinity group
    """
    affinity_groups = {
        "{0}_04".format(
            conf.AFFINITY_MAINTENANCE_HOST_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_4
    }
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1}
    }
    hosts_to_activate_indexes = [1]

    @tier2
    @polarion("RHEVM-17599")
    def test_host_maintenance(self):
        """
        Check that the engine migrates the VM-0 on the host-2
        """
        assert ll_hosts.deactivate_host(
            positive=True, host=conf.HOSTS[1], host_resource=conf.VDS_HOSTS[1]
        )
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[2]
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class BaseHostAffinityEnforcement(BaseHostAffinity):
    """
    Base class for all host to VM affinity enforcement tests
    """
    vms_to_run = None
    affinity_groups = None


class TestEnforcementUnderHostAffinity01(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement migrates the VM
    from incorrect host to the correct one under hard positive affinity
    """
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1}}
    affinity_groups = {
        "{0}_01".format(
            conf.AFFINITY_ENFORCEMENT_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-17607")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrates the VM-0 from the host-1 to the host-0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )


class TestEnforcementUnderHostAffinity02(BaseHostAffinityEnforcement):
    """
    Test that affinity enforcement migrates the VM
    from incorrect host to the correct one under hard negative affinity
    """
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0}}
    affinity_groups = {
        "{0}_02".format(
            conf.AFFINITY_ENFORCEMENT_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_5
    }

    @tier1
    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @polarion("RHEVM-17608")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrates the VM-0 from the host-0 to the host-2
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2], expected_num_of_vms=1
        )


class TestEnforcementUnderHostAffinity03(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement migrates the VM
    from incorrect host to the correct one under soft positive affinity
    """
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1}}
    affinity_groups = {
        "{0}_03".format(
            conf.AFFINITY_ENFORCEMENT_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_3
    }

    @tier2
    @polarion("RHEVM-18189")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrates the VM-0 from the host-1 to the host-0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )


class TestEnforcementUnderHostAffinity04(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement migrates the VM
    from incorrect host to the correct one under soft negative affinity
    """
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0}}
    affinity_groups = {
        "{0}_04".format(
            conf.AFFINITY_ENFORCEMENT_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_5
    }

    @tier2
    @polarion("RHEVM-18190")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrates the VM-0 from the host-0 to the host-2
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2], expected_num_of_vms=1
        )


class TestEnforcementUnderHostAffinity05(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement does not migrate the VM,
    when VM placed under hard positive host to VM affinity group with the
    additional affinity constraint
    """
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 0}
    }
    affinity_groups = {
        "{0}_05".format(conf.AFFINITY_ENFORCEMENT_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: True,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM-18229")
    def test_affinity_enforcement(self):
        """
        Check that the engine does not migrate VM-0 to the host-0
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=2
        )


class TestEnforcementUnderHostAffinity06(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement does not migrate the VM,
    when VM placed under hard negative host to VM affinity group with the
    additional affinity constraint
    """
    vms_to_run = conf.VMS_TO_RUN_3
    affinity_groups = {
        "{0}_06".format(conf.AFFINITY_ENFORCEMENT_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier2
    @polarion("RHEVM-18230")
    def test_affinity_enforcement(self):
        """
        Check that the engine does not migrate the VM-0 from the host-0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=0
        )


class TestEnforcementUnderHostAffinity07(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement migrates the VM,
    when VM placed under soft positive host to VM affinity group with the
    additional affinity constraint
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 0}
    }
    affinity_groups = {
        "{0}_07".format(conf.AFFINITY_ENFORCEMENT_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: True,
                conf.AFFINITY_GROUP_ENFORCING: False
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM-18231")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrate the VM-0 from the host-0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )


class TestEnforcementUnderHostAffinity08(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement migrates the VM,
    when VM placed under soft negative host to VM affinity group with the
    additional affinity constraint
    """
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[2]: {conf.VM_RUN_ONCE_HOST: 2}
    }
    affinity_groups = {
        "{0}_08".format(conf.AFFINITY_ENFORCEMENT_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: False
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier2
    @polarion("RHEVM-18232")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrates some VM from the host-1 to the host-0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )


class TestEnforcementUnderHostAffinity09(BaseHostAffinityEnforcement):
    """
    Test that the affinity enforcement migrates the VM,
    when VM placed under hard negative host to VM affinity group with the
    additional affinity constraint and with VM to VM affinity disabled
    """
    vms_to_run = conf.VMS_TO_RUN_3
    affinity_groups = {
        "{0}_09".format(conf.AFFINITY_ENFORCEMENT_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: False
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: False
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }

    @tier2
    @polarion("RHEVM-18234")
    def test_affinity_enforcement(self):
        """
        Check that the engine migrates the VM-0 from the host-0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=0
        )


@pytest.mark.usefixtures(create_affinity_groups.__name__)
class TestNegativeAddAffinityGroup(SlaTest):
    """
    Add affinity group negative test cases
    """
    affinity_group_name = "name_in_use_affinity_group"
    affinity_groups = {
        affinity_group_name: conf.HOST_TO_VM_AFFINITY_GROUP_1
    }

    @tier2
    @polarion("RHEVM-18985")
    def test_add_affinity_group_with_name_in_use(self):
        """
        Add the affinity group with the name that already in use
        """
        assert not ll_clusters.create_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0], name=self.affinity_group_name
        )

    @tier2
    @polarion("RHEVM-18986")
    def test_add_affinity_group_with_long_name(self):
        """
        Add the affinity group with the name that exceeds the defined limit
        """
        affinity_group_name = "a" * 256
        assert not ll_clusters.create_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0], name=affinity_group_name
        )

    @tier2
    @polarion("RHEVM-18987")
    def test_add_affinity_group_with_special_characters_name(self):
        """
        Add the affinity group with the name that includes special characters
        """
        affinity_group_name = "@_@"
        assert not ll_clusters.create_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0], name=affinity_group_name
        )


class TestAffinityModuleExistenceUnderPolicies(SlaTest):
    """
    Test that affinity filter and weight modules exist under each
    engine policy except the InClusterUpgrade policy
    """

    @tier1
    @polarion("RHEVM-19282")
    def test_modules_existence(self):
        """
        Verify that affinity units exist under the scheduling policies
        """
        affinity_host_to_vm_filter_id = ll_sch_policies.get_policy_unit(
            unit_name=conf.VM_TO_HOST_AFFINITY_UNIT,
            unit_type=conf.SCH_UNIT_TYPE_FILTER
        ).get_id()
        affinity_host_to_vm_weight_id = ll_sch_policies.get_policy_unit(
            unit_name=conf.VM_TO_HOST_AFFINITY_UNIT,
            unit_type=conf.SCH_UNIT_TYPE_WEIGHT
        ).get_id()
        for policy_name in conf.ENGINE_POLICIES:
            for unit_type, affinity_module_id in zip(
                (conf.SCH_UNIT_TYPE_FILTER, conf.SCH_UNIT_TYPE_WEIGHT),
                (affinity_host_to_vm_filter_id, affinity_host_to_vm_weight_id)
            ):
                policy_units = ll_sch_policies.get_sch_policy_units(
                    policy_name=policy_name, unit_type=unit_type
                )
                policy_modules_ids = [
                    policy_unit.get_id() for policy_unit in policy_units
                ]
                testflow.step(
                    "Verify that affinity unit with id %s "
                    "exists under the scheduling policy %s",
                    affinity_module_id, policy_name
                )
                assert affinity_module_id in policy_modules_ids


@pytest.mark.usefixtures(
    configure_hosts_power_management.__name__,
    update_vms.__name__,
    run_once_vms.__name__,
    stop_host_network.__name__
)
class TestHaVmUnderHostAffinity(BaseHostAffinityStartVm):
    """
    Test that the engine restart the HA VM that placed under soft, positive
    affinity group with the problematic host
    """
    affinity_groups = {"test_ha_vm": conf.HOST_TO_VM_AFFINITY_GROUP_3}
    hosts_to_pms = [0]
    vms_to_params = {conf.VM_NAME[0]: {conf.VM_HIGHLY_AVAILABLE: True}}
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0}}
    stop_network_on_host = 0

    @tier3
    @polarion("RHEVM-19283")
    def test_ha_vm_restart(self):
        """
        Verify that the engine restart the HA VM
        """
        testflow.step("Wait for the HA VM restart")
        assert ll_vms.waitForVmsStates(
            positive=True, names=conf.VM_NAME[:1], states=conf.VM_POWERING_UP
        )


@pytest.mark.usefixtures(
    skip_if_not_he_environment.__name__,
    create_affinity_groups.__name__,
    stop_vms.__name__
)
class TestEnforcementUnderHostAffinityWithHeVm(BaseHostAffinity):
    """
    Test that the affinity enforcement does not try to balance the HE VM
    """
    affinity_group_name = "test_enforcement_with_he_vm"
    affinity_groups = {
        affinity_group_name: {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUPS_ENABLED: False
            },
            conf.AFFINITY_GROUP_VMS: [conf.VM_NAME[0], conf.HE_VM]
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM-19314")
    def test_he_vm_host(self):
        """
        Verify that the HE VM stays on the old host
        """
        he_vm_host = ll_vms.get_vm_host(vm_name=conf.HE_VM)

        run_once_params = {
            conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: he_vm_host}
        }
        testflow.step(
            "Run the VM %s on the host %s", conf.VM_NAME[0], he_vm_host
        )
        ll_vms.run_vms_once(vms=[conf.VM_NAME[0]], **run_once_params)

        assert ll_clusters.update_affinity_group(
            cluster_name=conf.CLUSTER_NAME[0],
            old_name=self.affinity_group_name,
            hosts=[he_vm_host]
        )

        assert not sch_helpers.is_balancing_happen(
            host_name=he_vm_host, expected_num_of_vms=0, add_he_vm=False
        )

        assert self.check_vm_host(vm_name=conf.HE_VM, host_name=he_vm_host)


@pytest.mark.usefixtures(load_hosts_cpu.__name__)
class TestEnforcementAndPowerSavingBalancingLoop(BaseHostAffinityMigrateVm):
    """
    Test that the engine does not migrate the VM in the loop, because of
    power saving load balancing and affinity enforcement
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_POWER_SAVING,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_PARAMS
    }
    affinity_groups = {
        "test_balancing_loop_ps": conf.HOST_TO_VM_AFFINITY_GROUP_3
    }
    vms_to_run = conf.VMS_TO_RUN_1
    hosts_cpu_load = {conf.CPU_LOAD_50: [1]}

    @tier2
    @polarion("RHEVM-18236")
    def test_balancing_loop(self):
        """
        Verify that the affinity enforcement has stronger effect on the VM
        balancing
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=0
        )


@pytest.mark.usefixtures(load_hosts_cpu.__name__)
class TestEnforcementAndEvenDistributionBalancingLoop(
    BaseHostAffinityMigrateVm
):
    """
    Test that the engine does not migrate the VM in the loop, because of
    even distribution load balancing and affinity enforcement
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_EVEN_DISTRIBUTION,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_ED_PARAMS
    }
    affinity_groups = {
        "test_balancing_loop_ed": conf.HOST_TO_VM_AFFINITY_GROUP_3
    }
    vms_to_run = conf.VMS_TO_RUN_1
    hosts_cpu_load = {conf.CPU_LOAD_100: [0]}

    @tier2
    @polarion("RHEVM-18237")
    def test_balancing_loop(self):
        """
        Verify that the high CPU utilization has
        priority over affinity enforcement
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1], expected_num_of_vms=2
        )
