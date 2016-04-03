"""
Scheduler - Rhevm Cluster Policies Test
Check different cases for migration when cluster police is Evenly Distributed
and Power Saving
"""
import random
import logging
from rhevmtests.sla import config
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import SlaTest as TestCase
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.sla as sla_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
from art.rhevm_api.tests_lib.low_level.clusters import updateCluster


logger = logging.getLogger(__name__)

MAX_CPU_LOAD = 100
AVERAGE_CPU_LOAD = 50
MIN_CPU_LOAD = 0
# Time to wait for vm migration MAX_DURATION + 60(for migration)
WAIT_FOR_MIGRATION = 240
# Generate random value for CpuOverCommitDuration
DURATION = random.randint(1, 2) * 60
# Generate random value HighUtilization
HIGH_UTILIZATION = random.randint(70, 90)
# Generate random value LowUtilization
LOW_UTILIZATION = random.randint(10, 30)
CLUSTER_POLICIES = [
    config.ENUMS['scheduling_policy_evenly_distributed'],
    config.ENUMS['scheduling_policy_power_saving'],
    'none'
]


def teardown_module(module):
    """
    1) Release all hosts CPU
    """
    logger.info("Free all host CPU's from loading")
    sla_api.stop_cpu_loading_on_resources(config.VDS_HOSTS[:3])


@attr(tier=2)
class RhevmClusterPolicies(TestCase):
    __test__ = False
    load_hosts = None

    @classmethod
    def setup_class(cls):
        """
        Start vm on specific host for future migration and load host CPU
        """
        vm_host_d = dict(
            (vm_name, {"host": host_name, "wait_for_state": config.VM_UP})
            for vm_name, host_name in zip(config.VM_NAME[:3], config.HOSTS[:3])
        )
        vm_api.run_vms_once(vms=config.VM_NAME[:3], **vm_host_d)
        if cls.load_hosts:
            for load, hosts_d in cls.load_hosts.iteritems():
                if not sla_api.start_cpu_loading_on_resources(
                    hosts_d[config.RESOURCE], load
                ):
                    raise errors.HostException(
                        "Failed to load hosts %s CPU" %
                        hosts_d[config.RESOURCE]
                    )
                for host in hosts_d[config.HOST]:
                    host_expected_cpu_load = max(load - 10, LOW_UTILIZATION)
                    if not host_api.wait_for_host_cpu_load(
                        host_name=host,
                        expected_min_load=host_expected_cpu_load
                    ):
                        raise errors.HostException(
                            "Host %s have cpu load below expected one" % host
                        )

    @classmethod
    def teardown_class(cls):
        """
        Stop vm
        """
        logger.info("Stopping all vms")
        vm_api.stop_vms_safely(config.VM_NAME[:3])
        logger.info("Update cluster policy to none")
        if not updateCluster(
            positive=True,
            cluster=config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICIES[2]
        ):
            logger.error(
                "Update cluster %s failed", config.CLUSTER_NAME[0]
            )
        for hosts_d in cls.load_hosts.itervalues():
            sla_api.stop_cpu_loading_on_resources(hosts_d[config.RESOURCE])
            for host in hosts_d[config.HOST]:
                if not host_api.wait_for_host_cpu_load(
                    host_name=host, expected_max_load=5
                ):
                    logger.error(
                        "Host %s have cpu load below expected one", host
                    )

    def _check_migration(self, migration_host):
        """
        Check if vm migrated on given host in defined time

        :param migration_host: migration destination host
        :type migration_host: str
        """
        logger.info("Wait until host %s, will have two vms", migration_host)
        migration_duration = host_api.wait_for_active_vms_on_host(
            migration_host,
            2,
            timeout=WAIT_FOR_MIGRATION
        )
        self.assertTrue(
            migration_duration,
            "Host %s still not have two vms" % migration_host
        )

    def _no_migration(self, host):
        """
        Check that no migration happened and vm stay on source host

        :param host: migration source host
        :type host: str
        """
        self.assertTrue(
            vm_api.no_vm_migration(config.VM_NAME[0], host, WAIT_FOR_MIGRATION)
        )

    def _maintenance_migration(self, src_host, dst_host):
        """
        Check that after deactivation of src host, vm migrated on dst host

        :param src_host: migration source host
        :type src_host: str
        :param dst_host: migration destination host
        :type dst_host: str
        """
        self.assertTrue(
            vm_api.maintenance_vm_migration(
                config.VM_NAME[0], src_host, dst_host
            )
        )


class EvenlyDistributed(RhevmClusterPolicies):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Evenly Distributed and run vms
        """
        super(EvenlyDistributed, cls).setup_class()
        if not updateCluster(
            True,
            config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICIES[0],
            thrhld_high=HIGH_UTILIZATION,
            duration=DURATION
        ):
            raise errors.ClusterException(
                "Update cluster %s failed" % config.CLUSTER_NAME[0]
            )


class PowerSaving(RhevmClusterPolicies):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Power Saving and run vms
        """
        super(PowerSaving, cls).setup_class()
        if not updateCluster(
            True,
            config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICIES[1],
            thrhld_high=HIGH_UTILIZATION,
            thrhld_low=LOW_UTILIZATION,
            duration=DURATION
        ):
            raise errors.ClusterException(
                "Update cluster %s failed" % config.CLUSTER_NAME[0]
            )


class TestMigrateFromUnderUtilizedHost(PowerSaving):
    """
    Positive: Migrate vm from host with low CPU utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            AVERAGE_CPU_LOAD: {
                config.RESOURCE: [config.VDS_HOSTS[1]],
                config.HOST: [config.HOSTS[1]]
            }
        }
        super(TestMigrateFromUnderUtilizedHost, cls).setup_class()

    @polarion("RHEVM3-9498")
    def test_check_migration(self):
        """
        Vm run on host with low cpu utilization and must migrate to host
        with CPU utilization between Low
        and High utilization after CpuOverCommitDuration
        """
        self._check_migration(config.HOSTS[1])


class TestNoAvailableHostForMigrationPS(PowerSaving):
    """
    Positive: No available host for migration, vm stay on old host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            MAX_CPU_LOAD: {
                config.RESOURCE: [config.VDS_HOSTS[1]],
                config.HOST: [config.HOSTS[1]]
            }
        }
        super(TestNoAvailableHostForMigrationPS, cls).setup_class()

    @polarion("RHEVM3-9489")
    def test_check_migration(self):
        """
        Vm run on host with low cpu utilization, but another host in cluster
        above maximum service level of CPU, so vm must stay on old host
        """
        self._no_migration(config.HOSTS[0])


class TestMigrationFromLowCPUUtilization(PowerSaving):
    """
    Positive: Migrate vm from host with low CPU utilization to host
     with average cpu level and not on host with high cpu utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            MAX_CPU_LOAD: {
                config.RESOURCE: [config.VDS_HOSTS[2]],
                config.HOST: [config.HOSTS[2]]
            },
            AVERAGE_CPU_LOAD: {
                config.RESOURCE: [config.VDS_HOSTS[1]],
                config.HOST: [config.HOSTS[1]]
            }
        }
        super(TestMigrationFromLowCPUUtilization, cls).setup_class()

    @polarion("RHEVM3-9490")
    def test_check_migration(self):
        """
        Vm run on host with low CPU utilization, check that vm migrate from
        host with low CPU utilization, to host with correct
        utilization after CpuOverCommitDuration
        """
        self._check_migration(config.HOSTS[1])


class TestPutHostToMaintenancePS(PowerSaving):
    """
    Positive: Put host with vm to maintenance state, choose host for migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            AVERAGE_CPU_LOAD: {
                config.RESOURCE: config.VDS_HOSTS[:2],
                config.HOST: config.HOSTS[:2]
            }
        }
        super(TestPutHostToMaintenancePS, cls).setup_class()

    @polarion("RHEVM3-9492")
    def test_check_migration(self):
        """
        Vm run on host with correct cpu utilization, we put host to
        maintenance and check if vm migrated on host with correct
        CPU utilization level
        """
        self._maintenance_migration(config.HOSTS[0], config.HOSTS[1])

    @classmethod
    def teardown_class(cls):
        """
        Release hosts CPU, activate host and stop vm
        """
        if not host_api.activateHost(True, config.HOSTS[0]):
            raise logger.error(
                "Activation of host %s failed", config.HOSTS[0]
            )
        super(TestPutHostToMaintenancePS, cls).teardown_class()


class TestMigrateFromOverUtilizedHost(EvenlyDistributed):
    """
    Positive: Migrate vm from host with high CPU utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            MAX_CPU_LOAD: {
                config.RESOURCE: config.VDS_HOSTS[:2],
                config.HOST: config.HOSTS[:2]
            }
        }
        super(TestMigrateFromOverUtilizedHost, cls).setup_class()

    @polarion("RHEVM3-9493")
    def test_check_migration(self):
        """
        Vm run on host with high cpu utilization and must migrate to host
        with correct CPU utilization after CpuOverCommitDuration
        """
        self._check_migration(config.HOSTS[2])


class TestNoAvailableHostForMigrationED(EvenlyDistributed):
    """
    Positive: No available host for migration, vm stay on old host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            MAX_CPU_LOAD: {
                config.RESOURCE: config.VDS_HOSTS[1:3],
                config.HOST: config.HOSTS[1:3]
            }
        }
        super(TestNoAvailableHostForMigrationED, cls).setup_class()

    @polarion("RHEVM3-9494")
    def test_check_migration(self):
        """
        Vm run on host with low cpu utilization, but another host in cluster
        above maximum service level of CPU, so vm must stay on old host
        """
        self._no_migration(config.HOSTS[0])


class TestPutHostToMaintenanceED(EvenlyDistributed):
    """
    Positive: Put host with vm to maintenance state, choose host for migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.load_hosts = {
            MAX_CPU_LOAD: {
                config.RESOURCE: [config.VDS_HOSTS[2]],
                config.HOST: [config.HOSTS[2]]
            }
        }
        super(TestPutHostToMaintenanceED, cls).setup_class()

    @polarion("RHEVM3-9496")
    def test_check_migration(self):
        """
        Vm run on host with correct cpu utilization, we put host to
        maintenance and check if vm migrated on host with correct
        CPU utilization level
        """
        self._maintenance_migration(config.HOSTS[0], config.HOSTS[1])

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU, activate host and stop vm
        """
        if not host_api.activateHost(True, config.HOSTS[0]):
            logger.error("Activation of host %s failed", config.HOSTS[0])
        super(TestPutHostToMaintenanceED, cls).teardown_class()


@attr(tier=1)
class TestCheckClusterPolicyParameters(TestCase):
    """
    Check different values for cluster policy parameters:
        1) CpuOverCommitDurationMinutes - min=1; max=99
        2) HighUtilization - min=50; max=99
        3) LowUtilization - min=0; max=49
    """
    __test__ = True
    high_utilization = random.randint(50, 99)
    low_utilization = random.randint(0, 49)
    duration = random.randint(1, 99) * 60

    def test_check_parameters_ed(self):
        """
        Check if cluster success to do update to Evenly Distributed
        with given parameters
        Added, because this bug:
        https://bugzilla.redhat.com/show_bug.cgi?id=1070704
        """
        logger.info(
            "Change cluster policy to %s with parameters", CLUSTER_POLICIES[0]
        )
        self.assertTrue(
            updateCluster(
                True,
                config.CLUSTER_NAME[0],
                scheduling_policy=CLUSTER_POLICIES[0],
                thrhld_high=self.high_utilization,
                duration=self.duration
            )
        )

    def test_check_parameters_ps(self):
        """
        Check if cluster success to do update to Power Saving
        with given parameters
        Added, because this bug:
        https://bugzilla.redhat.com/show_bug.cgi?id=1070704
        """
        logger.info(
            "Change cluster policy to %s with parameters", CLUSTER_POLICIES[1]
        )
        self.assertTrue(
            updateCluster(
                True,
                config.CLUSTER_NAME[0],
                scheduling_policy=CLUSTER_POLICIES[1],
                thrhld_high=self.high_utilization,
                thrhld_low=self.low_utilization,
                duration=self.duration
            )
        )

    @classmethod
    def teardown_class(cls):
        logger.info("Update cluster policy to none")
        if not updateCluster(
            True,
            config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICIES[2]
        ):
            logger.error("Update cluster %s failed", config.CLUSTER_NAME[0])
