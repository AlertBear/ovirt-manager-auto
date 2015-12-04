"""
Scheduler - Affinity Test
Check different cases for migration and starting of vms, when vms in different
or in the same affinities groups(soft/hard, positive/negative)
"""

import logging

from art.unittest_lib import attr
from rhevmtests.sla import config

from art.unittest_lib import SlaTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.high_level.vms as high_vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api


logger = logging.getLogger(__name__)

TIMEOUT = 120


class Affinity(TestCase):
    """
    Base class for affinity test
    """
    __test__ = False

    affinity_group_name = None
    positive = None
    hard = None

    @classmethod
    def _populate_affinity_group_with_vms(cls, group_name, vms):
        """
        Populate affinity group with vms

        :param group_name: affinity group name
        :type group_name: str
        :param vms: list of vms to add to affinity group
        :type vms: list
        :return: True, if action succeed, otherwise False
        :rtype: bool
        """
        logger.info(
            "Populate affinity group %s with vms %s", group_name, vms
        )
        return cluster_api.populate_affinity_with_vms(
            affinity_name=group_name,
            cluster_name=config.CLUSTER_NAME[0],
            vms=vms
        )

    @classmethod
    def setup_class(cls):
        """
        Create new affinity group and populate it with vms
        """
        logger.info(
            "Create new affinity group %s", cls.affinity_group_name
        )
        if not cluster_api.create_affinity_group(
            cluster_name=config.CLUSTER_NAME[0],
            name=cls.affinity_group_name,
            positive=cls.positive,
            enforcing=cls.hard
        ):
            raise errors.ClusterException(
                "Failed to create new affinity group %s" %
                cls.affinity_group_name
            )
        if not cls._populate_affinity_group_with_vms(
            group_name=cls.affinity_group_name, vms=config.VM_NAME[:2]
        ):
            raise errors.ClusterException(
                "Failed to populate affinity group %s with vms %s" %
                (cls.affinity_group_name, config.VM_NAME[:2])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove affinity group
        """
        logger.info("Remove affinity group %s", cls.affinity_group_name)
        if not cluster_api.remove_affinity_group(
            cls.affinity_group_name, config.CLUSTER_NAME[0]
        ):
            logger.error(
                "Failed to remove affinity group %s", cls.affinity_group_name
            )


class StartVms(Affinity):
    """
    Start vms that placed in the same affinity group
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Start all vms
        """
        super(StartVms, cls).setup_class()
        logger.info("Start all vms")
        for vm in config.VM_NAME[:2]:
            logger.info("Start vm %s", vm)
            if not vm_api.startVm(True, vm, wait_for_status=config.VM_UP):
                raise errors.VMException("Failed to start vms")

    @classmethod
    def teardown_class(cls):
        """
        Stop all vms
        """
        logger.info("Stop vms %s", config.VM_NAME[:2])
        try:
            vm_api.stop_vms_safely(config.VM_NAME[:2])
        except errors.VMException as e:
            logger.error(e.message)
        super(StartVms, cls).teardown_class()


@attr(tier=1)
class TestStartVmsUnderHardPositiveAffinity(StartVms):
    """
    Start vms that placed into the same hard, positive affinity group,
    and check if they started on the same host
    """
    __test__ = True

    affinity_group_name = 'hard_positive_start_vm'
    positive = True
    hard = True

    @polarion("RHEVM3-5539")
    def test_check_vms_host(self):
        """
        Check where vms started
        """
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "vms not run on the same host"
        )


@attr(tier=2)
class TestStartVmsUnderSoftPositiveAffinity(StartVms):
    """
    Start vms that placed into the same soft, positive affinity group,
    and check if they started on the same host
    """
    __test__ = True

    affinity_group_name = 'soft_positive_start_vm'
    positive = True
    hard = False

    @polarion("RHEVM3-5541")
    def test_check_vms_host(self):
        """
        Check where vms started
        """
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "vms not run on the same host"
        )


@attr(tier=1)
class TestStartVmsUnderHardNegativeAffinity(StartVms):
    """
    Start vms that placed into the same hard, negative affinity group,
    and check if they started on different hosts
    """
    __test__ = True

    affinity_group_name = 'hard_negative_start_vm'
    positive = False
    hard = True

    @polarion("RHEVM3-5553")
    def test_check_vms_host(self):
        """
        Check where vms started
        """
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vms runs on the same host"
        )


@attr(tier=2)
class TestStartVmsUnderSoftNegativeAffinity(StartVms):
    """
    Start vms that placed into the same soft, negative affinity group,
    and check if they started on different hosts
    """
    __test__ = True

    affinity_group_name = 'soft_negative_start_vm'
    positive = False
    hard = True

    @polarion("RHEVM3-5542")
    def test_check_vms_host(self):
        """
        Check where vms started
        """
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vms runs on the same host"
        )


class MigrateVm(Affinity):
    """
    Start vms on different hosts and
    migrate one of vm under specific affinity policy
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Start vms, and create new affinity group
        """
        if len(config.HOSTS) >= 2:
            host_vm_dict = {
                config.VM_NAME[0]: config.HOSTS[0],
                config.VM_NAME[1]: config.HOSTS[1]
            }
        else:
            raise errors.SkipTest("Not enough hosts to run this test")
        logger.info("Start vms on different hosts")
        for vm, host in host_vm_dict.iteritems():
            if not vm_api.runVmOnce(True, vm, host=host):
                raise errors.VMException("Failed to start vms")
        super(MigrateVm, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Stop vms and remove affinity group
        """
        logger.info("Stop vms %s", config.VM_NAME[:3])
        try:
            vm_api.stop_vms_safely(config.VM_NAME[:3])
        except errors.VMException as e:
            logger.error(e.message)
        for vm in config.VM_NAME[:2]:
            logger.info(
                "Update vm %s migration option to %s",
                vm, config.VM_MIGRATABLE
            )
            if not vm_api.updateVm(
                positive=True, vm=vm,
                placement_affinity=config.VM_MIGRATABLE
            ):
                logger.error("Failed to update vm %s" % vm)
        super(MigrateVm, cls).teardown_class()


@attr(tier=1)
class TestMigrateVmUnderHardPositiveAffinity(MigrateVm):
    """
    Migrate vm under hard positive affinity,
    so vm must migrate on the same host, where second vm run
    """
    __test__ = True

    affinity_group_name = 'hard_positive_migrate_vm'
    positive = True
    hard = True

    @classmethod
    def setup_class(cls):
        """
        Change migration options of vm
        """
        for vm in config.VM_NAME[:2]:
            logger.info(
                "Update vm %s migration option to %s",
                vm, config.VM_USER_MIGRATABLE
            )
            if not vm_api.updateVm(
                positive=True, vm=vm,
                placement_affinity=config.VM_USER_MIGRATABLE
            ):
                raise errors.VMException("Failed to update vm %s" % vm)
        super(TestMigrateVmUnderHardPositiveAffinity, cls).setup_class()

    @polarion("RHEVM3-5557")
    def test_check_vm_migration(self):
        """
        Check if vm succeeds to migrate
        """
        logger.info("Migrate vm %s", config.VM_NAME[0])
        if not vm_api.migrateVm(
            positive=True, vm=config.VM_NAME[0], force=True
        ):
            raise errors.VMException(
                "Failed to migrate vm %s", config.VM_NAME[0]
            )
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "vms don't run on the same host"
        )


@attr(tier=2)
class TestMigrateVmUnderSoftPositiveAffinity(MigrateVm):
    """
    Migrate vm under soft positive affinity,
    so vm must migrate on the same host, where second vm run
    """
    __test__ = True

    affinity_group_name = 'soft_positive_migrate_vm'
    positive = True
    hard = False

    @polarion("RHEVM3-5543")
    def test_check_vm_migration(self):
        """
        Check if vm success to migrate
        """
        logger.info("Migrate vm %s", config.VM_NAME[0])
        if not vm_api.migrateVm(True, config.VM_NAME[0]):
            raise errors.VMException("Failed to migrate vm")
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "vms not run on the same host"
        )


@attr(tier=1)
class TestMigrateVmUnderHardNegativeAffinity(MigrateVm):
    """
    Migrate vm under hard negative affinity,
    so vm must migrate on different from second vm host
    """
    __test__ = True

    affinity_group_name = 'hard_negative_migrate_vm'
    positive = False
    hard = True

    @classmethod
    def setup_class(cls):
        """
        Change migration options of vm
        """
        for vm in config.VM_NAME[:2]:
            logger.info(
                "Update vm %s migration option to %s",
                vm, config.VM_USER_MIGRATABLE
            )
            if not vm_api.updateVm(
                positive=True, vm=vm,
                placement_affinity=config.VM_USER_MIGRATABLE
            ):
                raise errors.VMException("Failed to update vm %s" % vm)
        super(TestMigrateVmUnderHardNegativeAffinity, cls).setup_class()

    @polarion("RHEVM3-5558")
    def test_check_vm_migration(self):
        """
        Check if vm succeeds to migrate
        """
        logger.info("Migrate vm %s", config.VM_NAME[0])
        if not vm_api.migrateVm(
            positive=True, vm=config.VM_NAME[0], force=True
        ):
            raise errors.VMException(
                "Failed to migrate vm %s" % config.VM_NAME[0]
            )
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "vms don't run on the same host"
        )


@attr(tier=2)
class TestMigrateVmUnderSoftNegativeAffinity(MigrateVm):
    """
    Migrate vm under soft negative affinity,
    so vm must migrate on different from second vm host
    """
    __test__ = True

    affinity_group_name = 'soft_negative_migrate_vm'
    positive = False
    hard = False

    @polarion("RHEVM3-5544")
    def test_check_vm_migration(self):
        """
        Check if vm success to migrate
        """
        logger.info("Migrate vm %s", config.VM_NAME[0])
        if not vm_api.migrateVm(True, config.VM_NAME[0]):
            raise errors.VMException("Failed to migrate vm")
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "vms not run on the same host"
        )


@attr(tier=2)
class TestNegativeMigrateVmUnderHardPositiveAffinity(MigrateVm):
    """
    Negative: Migrate vm under hard positive affinity to opposite host
    """
    __test__ = True

    affinity_group_name = 'negative_hard_positive_migrate_vm'
    positive = True
    hard = True

    @polarion("RHEVM3-5559")
    def test_check_vm_migration(self):
        """
        Check if vm success to migrate
        """
        self.assertFalse(
            vm_api.migrateVm(True, config.VM_NAME[0], config.HOSTS[2]),
            "Vm migration success"
        )


@attr(tier=2)
class TestMigrateVmOppositeUnderSoftPositiveAffinity(MigrateVm):
    """
    Migrate vm under soft positive affinity to opposite host
    """
    __test__ = True

    affinity_group_name = 'opposite_soft_positive_migrate_vm'
    positive = True
    hard = False

    @polarion("RHEVM3-5546")
    def test_check_vm_migration(self):
        """
        Check if vm success to migrate
        """
        self.assertTrue(
            vm_api.migrateVm(True, config.VM_NAME[0], config.HOSTS[2]),
            "Vm migration failed"
        )


@attr(tier=2)
class TestNegativeMigrateVmUnderHardNegativeAffinity(MigrateVm):
    """
    Negative: Migrate vm under hard negative affinity
    to same host where second vm
    """
    __test__ = True

    affinity_group_name = 'negative_hard_negative_migrate_vm'
    positive = False
    hard = True

    @polarion("RHEVM3-5545")
    def test_check_vm_migration(self):
        """
        Check if vm success to migrate
        """
        self.assertFalse(
            vm_api.migrateVm(True, config.VM_NAME[0], config.HOSTS[1]),
            "Vm migration success"
        )


@attr(tier=2)
class TestMigrateVmSameUnderSoftNegativeAffinity(MigrateVm):
    """
    Migrate vm under soft negative affinity to same host where second vm
    """
    __test__ = True

    affinity_group_name = 'same_soft_negative_migrate_vm'
    positive = False
    hard = False

    @polarion("RHEVM3-5547")
    def test_check_vm_migration(self):
        """
        Check if vm success to migrate
        """
        self.assertTrue(
            vm_api.migrateVm(True, config.VM_NAME[0], config.HOSTS[1]),
            "Vm migration failed"
        )


@attr(tier=2)
class TestRemoveVmFromAffinityGroupOnClusterChange(Affinity):
    """
    Change vm cluster, also must remove vm from affinity group of other cluster
    """
    __test__ = True

    affinity_group_name = 'cluster_change_affinity_group'
    positive = True
    hard = True
    additional_cluster_name = 'test_cluster'

    @classmethod
    def setup_class(cls):
        """
        Create new cluster, create affinity group,
        populate affinity group by vms and update vm cluster
        """
        super(TestRemoveVmFromAffinityGroupOnClusterChange, cls).setup_class()
        logger.info("Create new cluster for test")
        comp_version = config.PARAMETERS['compatibility_version']
        if not cluster_api.addCluster(
            True, name=cls.additional_cluster_name,
            cpu=config.PARAMETERS['cpu_name'],
            data_center=config.DC_NAME[0],
            version=comp_version
        ):
            raise errors.ClusterException("Failed to create new cluster")
        cpu_profile_obj = cluster_api.get_cpu_profile_obj(
            cls.additional_cluster_name, cls.additional_cluster_name
        )
        if not cpu_profile_obj:
            raise errors.ClusterException(
                "Failed to get cpu profile object %s from cluster %s" %
                (cls.additional_cluster_name, cls.additional_cluster_name)
            )
        logger.info(
            "Update vm %s cluster to %s",
            config.VM_NAME[0], cls.additional_cluster_name
        )
        if not vm_api.updateVm(
            True, config.VM_NAME[0],
            cluster=cls.additional_cluster_name,
            cpu_profile_id=cpu_profile_obj.get_id()
        ):
            raise errors.VMException("Failed update vm cluster")

    @polarion("RHEVM3-5560")
    def test_check_affinity_group(self):
        """
        Check if vm removed from affinity group
        """
        self.assertFalse(
            cluster_api.check_vm_affinity_group(
                self.affinity_group_name,
                config.CLUSTER_NAME[0],
                config.VM_NAME[0]
            ),
            "Vm still exist under affinity group"
        )

    @classmethod
    def teardown_class(cls):
        """
        Update vm cluster, remove new cluster and remove affinity group
        """
        logger.info(
            "Update vm %s cluster to %s",
            config.VM_NAME[0], config.CLUSTER_NAME[0]
        )
        if not vm_api.updateVm(
            True, config.VM_NAME[0], cluster=config.CLUSTER_NAME[0]
        ):
            logger.error("Failed update vm %s cluster", config.VM_NAME[0])
        logger.info("Remove cluster %s", cls.additional_cluster_name)
        if not cluster_api.removeCluster(True, cls.additional_cluster_name):
            logger.error(
                "Failed to remove cluster %s", cls.additional_cluster_name
            )
        super(
            TestRemoveVmFromAffinityGroupOnClusterChange, cls
        ).teardown_class()


@attr(tier=2)
class PutHostToMaintenance(StartVms):
    """
    Put host to maintenance and check vms migration destination
    """
    __test__ = False
    host = None

    @classmethod
    def setup_class(cls):
        """
        Put host to maintenance
        """
        super(PutHostToMaintenance, cls).setup_class()
        cls.host = vm_api.get_vm_host(config.VM_NAME[0])
        logger.info("Deactivate host %s", cls.host)
        if not host_api.deactivateHost(True, cls.host, timeout=TIMEOUT):
            raise errors.HostException("Failed to deactivate host.")

    @classmethod
    def teardown_class(cls):
        """
        Activate host
        """
        if cls.host:
            logger.info("Activate host %s", cls.host)
            if not host_api.activateHost(True, cls.host):
                logger.error("Failed to activate host %s", cls.host)
        super(PutHostToMaintenance, cls).teardown_class()


@attr(tier=2)
class TestPutHostToMaintenanceUnderHardPositiveAffinity(StartVms):
    """
    Put host to maintenance under hard positive affinity
    and check vms migration destination
    """
    __test__ = True
    affinity_group_name = 'maintenance_hard_positive_affinity_group'
    positive = True
    hard = True
    bz = {
        "1261880": {"engine": None, "version": ["3.6.0"]}
    }

    @polarion("RHEVM3-5563")
    def test_check_affinity_group(self):
        """
        Check that after deactivate hosts vms migrated on the same host
        """
        vm_host = vm_api.get_vm_host(config.VM_NAME[0])
        self.assertTrue(
            host_api.deactivateHost(True, vm_host, timeout=TIMEOUT),
            "Success to deactivate host"
        )
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vm's migrated on different hosts"
        )


@attr(tier=2)
class TestPutHostToMaintenanceUnderHardNegativeAffinity(PutHostToMaintenance):
    """
    Put host to maintenance under hard negative affinity
    and check vms migration destination
    """
    __test__ = True
    affinity_group_name = 'maintenance_hard_negative_affinity_group'
    positive = False
    hard = True

    @polarion("RHEVM3-5549")
    def test_check_affinity_group(self):
        """
        Check that after deactivate hosts vms migrated on different hosts
        """
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vm's migrated on the same hosts"
        )


class AdditionalAffinityGroup(Affinity):
    """
    Create additional affinity group and start vms
    """
    __test__ = False
    additional_name = None
    additional_positive = None
    additional_hard = None

    @classmethod
    def setup_class(cls):
        """
        Create additional affinity group with the same vms
        """
        super(AdditionalAffinityGroup, cls).setup_class()
        logger.info(
            "Create new affinity group %s", cls.additional_name
        )
        if not cluster_api.create_affinity_group(
            cluster_name=config.CLUSTER_NAME[0],
            name=cls.additional_name,
            positive=cls.additional_positive,
            enforcing=cls.additional_hard
        ):
            raise errors.ClusterException(
                "Failed to create new affinity group %s" % cls.additional_name
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove all affinity groups
        """
        logger.info("Remove affinity group %s", cls.additional_name)
        if not cluster_api.remove_affinity_group(
            cls.additional_name, config.CLUSTER_NAME[0]
        ):
            logger.error(
                "Failed to remove affinity group %s", cls.additional_name
            )
        super(AdditionalAffinityGroup, cls).teardown_class()


@attr(tier=2)
class TestTwoDifferentAffinitiesScenario1(AdditionalAffinityGroup):
    """
    Negative: create two affinity groups with the same vms
    1) hard and positive
    2) soft and negative
    Populate second group with vms will fail
    because of affinity group rules collision
    """
    __test__ = True
    affinity_group_name = 'affinity_group_scenario_1_1'
    positive = True
    hard = True
    additional_name = 'affinity_group_scenario_1_2'
    additional_positive = False
    additional_hard = False

    @polarion("RHEVM3-5562")
    def test_check_vms_placement(self):
        """
        Populate second affinity group with vms
        """
        self.assertFalse(
            self._populate_affinity_group_with_vms(
                group_name=self.additional_name, vms=config.VM_NAME[:2]
            ),
            "Succeed to populate affinity group %s with vms %s" %
            (self.additional_name, config.VM_NAME[:2])
        )


@attr(tier=2)
class TestTwoDifferentAffinitiesScenario2(AdditionalAffinityGroup):
    """
    Negative: create two affinity groups with the same vms
    1) hard and negative
    2) soft and positive
    Populate second group with vms will fail
    because of affinity group rules collision
    """
    __test__ = True
    affinity_group_name = 'affinity_group_scenario_2_1'
    positive = False
    hard = True
    additional_name = 'affinity_group_scenario_2_2'
    additional_positive = True
    additional_hard = False

    @polarion("RHEVM3-5552")
    def test_check_vms_placement(self):
        """
        Populate second affinity group with vms
        """
        self.assertFalse(
            self._populate_affinity_group_with_vms(
                group_name=self.additional_name, vms=config.VM_NAME[:2]
            ),
            "Succeed to populate affinity group %s with vms %s" %
            (self.additional_name, config.VM_NAME[:2])
        )


@attr(tier=2)
class TestTwoDifferentAffinitiesScenario3(AdditionalAffinityGroup):
    """
    Negative: create two affinity groups with the same vms
    1) hard and negative
    2) hard and positive
    Populate second group with vms will fail
    because of affinity group rules collision
    """
    __test__ = True
    affinity_group_name = 'affinity_group_scenario_3_1'
    positive = True
    hard = True
    additional_name = 'affinity_group_scenario_3_2'
    additional_positive = False
    additional_hard = True

    @polarion("RHEVM3-5551")
    def test_start_vms(self):
        """
        Populate second affinity group with vms
        """
        self.assertFalse(
            self._populate_affinity_group_with_vms(
                group_name=self.additional_name, vms=config.VM_NAME[:2]
            ),
            "Succeed to populate affinity group %s with vms %s" %
            (self.additional_name, config.VM_NAME[:2])
        )


@attr(tier=2)
class TestFailedToStartHAVmUnderHardNegativeAffinity(MigrateVm):
    """
    Kill HA vm and check that vm failed to start,
    because hard negative affinity
    """
    __test__ = True
    ha_vm = 'ha_vm'
    affinity_group_name = 'failed_ha_affinity_group'
    positive = False
    hard = True

    @classmethod
    def setup_class(cls):
        """
        Create additional HA vm and deactivate one of hosts
        """
        logger.info("Deactivate host %s", config.HOSTS[2])
        if not host_api.deactivateHost(True, config.HOSTS[2]):
            raise errors.HostException("Failed to deactivate host")
        logger.info("Create HA vm")
        if not vm_api.createVm(
            positive=True, vmName=cls.ha_vm,
            vmDescription='Affinity VM',
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            size=config.DISK_SIZE, nic=config.NIC_NAME[0],
            display_type=config.VM_DISPLAY_TYPE,
            type=config.VM_TYPE_SERVER,
            network=config.MGMT_BRIDGE,
            highly_available=True
        ):
            raise errors.VMException("Failed to create HA vm")
        logger.info("Start vm %s", cls.ha_vm)
        if not vm_api.startVm(True, cls.ha_vm):
            raise errors.VMException("Failed to start vm")
        super(
            TestFailedToStartHAVmUnderHardNegativeAffinity, cls
        ).setup_class()
        logger.info(
            "Add vm %s to affinity group %s",
            cls.ha_vm, cls.affinity_group_name
        )
        if not cluster_api.populate_affinity_with_vms(
            cls.affinity_group_name, config.CLUSTER_NAME[0], [cls.ha_vm]
        ):
            raise errors.ClusterException(
                "Failed to add vm to affinity group"
            )

    @polarion("RHEVM3-5548")
    def test_check_ha_vm(self):
        """
        Kill HA vm and check that vm failed to run because affinity policy
        """
        ha_host = vm_api.get_vm_host(self.ha_vm)
        logger.info("Kill HA vm")
        if not host_api.kill_qemu_process(
            self.ha_vm, ha_host, config.HOSTS_USER, config.HOSTS_PW
        ):
            raise errors.HostException("Failed to kill vm process")
        self.assertTrue(
            vm_api.waitForVMState(self.ha_vm, state=config.VM_DOWN)
        )
        self.assertFalse(vm_api.waitForVMState(self.ha_vm, timeout=TIMEOUT))

    @classmethod
    def teardown_class(cls):
        """
        Remove HA vm and activate host
        """
        super(
            TestFailedToStartHAVmUnderHardNegativeAffinity, cls
        ).teardown_class()
        logger.info("Stop vm %s", cls.ha_vm)
        try:
            vm_api.stop_vms_safely([cls.ha_vm])
        except errors.VMException as e:
            logger.error(e.message)
        logger.info("Remove HA vm")
        if not vm_api.removeVm(True, cls.ha_vm):
            logger.error("Failed to remove vm %s", cls.ha_vm)
        logger.info("Activate host %s", config.HOSTS[2])
        if not host_api.activateHost(True, config.HOSTS[2]):
            logger.error("Failed to activate host %s", config.HOSTS[2])


@attr(tier=2)
class TestStartHAVmsUnderHardPositiveAffinity(StartVms):
    """
    Start two HA vms under hard positive affinity, kill them and
    check that they started on the same host
    """
    __test__ = True
    affinity_group_name = 'start_ha_vms'
    positive = True
    hard = True

    @classmethod
    def setup_class(cls):
        """
        Enable HA for test vms
        """
        for vm in config.VM_NAME[:2]:
            logger.info("Enable HA on vm %s", vm)
            if not vm_api.updateVm(True, vm, highly_available=True):
                raise errors.VMException("Failed to update vm")
        super(TestStartHAVmsUnderHardPositiveAffinity, cls).setup_class()

    @polarion("RHEVM3-5550")
    def test_check_ha_vms(self):
        """
        Kill qemu process of HA vms and check if vms started on the same host
        """
        vm_host = vm_api.get_vm_host(config.VM_NAME[0])
        logger.info("Kill qemu process of vm %s", config.VM_NAME[0])
        if not host_api.kill_qemu_process(
            config.VM_NAME[0], vm_host, config.HOSTS_USER, config.HOSTS_PW
        ):
            raise errors.HostException("Failed to kill vm process")
        logger.info("Kill qemu process of vm %s", config.VM_NAME[1])
        if not host_api.kill_qemu_process(
            config.VM_NAME[1], vm_host, config.HOSTS_USER, config.HOSTS_PW
        ):
            raise errors.HostException("Failed to kill vm process")
        logger.info("Wait until both vms change status to UP")
        if not vm_api.waitForVmsStates(True, config.VM_NAME[:2]):
            raise errors.VMException("One of vms still down")
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vms started on different hosts"
        )

    @classmethod
    def teardown_class(cls):
        """
        Disable HA on test vms
        """
        super(
            TestStartHAVmsUnderHardPositiveAffinity, cls
        ).teardown_class()
        for vm in config.VM_NAME[:2]:
            logger.info("Disable HA on vm %s", vm)
            if not vm_api.updateVm(True, vm, highly_available=False):
                logger.error("Failed to update vm %s", vm)


@attr(tier=2)
class TestSoftPositiveAffinityVsMemoryFilter(StartVms):
    """
    Change memory of vms to prevent possibility to start two vms on the same
    host and check if soft positive affinity not prevent this.
    """
    __test__ = True
    affinity_group_name = 'memory_vs_soft_affinity'
    positive = True
    hard = False

    @classmethod
    def setup_class(cls):
        """
        Change vms memory to prevent start of vms on the same host
        """
        logger.info(
            "Update cluster %s over commit to 100 percent",
            config.CLUSTER_NAME[0]
        )
        if not cluster_api.updateCluster(
            True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=100
        ):
            raise errors.ClusterException("Failed to update cluster")
        host_list = config.HOSTS[:3]
        memory = high_vm_api.calculate_memory_for_memory_filter(host_list)
        for vm, vm_memory in zip(config.VM_NAME[:2], memory):
            logger.info("Update vm %s with memory %d", vm, vm_memory)
            if not vm_api.updateVm(
                positive=True, vm=vm, memory=vm_memory,
                memory_guaranteed=vm_memory, os_type='rhel_6x64'
            ):
                raise errors.VMException("Failed to update vm")
        super(TestSoftPositiveAffinityVsMemoryFilter, cls).setup_class()

    @polarion("RHEVM3-5561")
    def test_start_vms(self):
        """
        Check that affinity policy not prevent to start vms
        """
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vms started on the same host"
        )

    @classmethod
    def teardown_class(cls):
        """
        Update vm memory to default value
        """
        super(TestSoftPositiveAffinityVsMemoryFilter, cls).teardown_class()
        logger.info(
            "Update cluster %s over commit to 200 percent",
            config.CLUSTER_NAME[0]
        )
        if not cluster_api.updateCluster(
            True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=200
        ):
            logger.error(
                "Failed to update cluster %s over commit percent",
                config.CLUSTER_NAME[0]
            )
        for vm in config.VM_NAME[:2]:
            logger.info("Update vm %s", vm)
            if not vm_api.updateVm(
                positive=True, vm=vm, memory=config.GB,
                memory_guaranteed=config.GB,
            ):
                logger.error("Failed to update vm %s", vm)
