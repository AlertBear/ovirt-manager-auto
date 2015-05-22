"""
Scheduler - Rhevm Cluster Policies Test
Check different cases for migration when cluster police is Evenly Distributed
and Power Saving
"""
import time
import random
import logging
from nose.tools import istest
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
timestamp = False

MAX_CPU_LOAD = 100
AVERAGE_CPU_LOAD = 50
MIN_CPU_LOAD = 0
# Time to update hosts stats
UPDATE_STATS = 30
# Time to wait for vm migration MAX_DURATION + 60(for migration)
WAIT_FOR_MIGRATION = 240
# Generate random value for CpuOverCommitDuration
DURATION = random.randint(1, 2) * 60
# Generate random value HighUtilization
HIGH_UTILIZATION = random.randint(70, 90)
# Generate random value LowUtilization
LOW_UTILIZATION = random.randint(10, 30)
CLUSTER_POLICIES = [config.ENUMS['scheduling_policy_evenly_distributed'],
                    config.ENUMS['scheduling_policy_power_saving'], 'none']


@attr(tier=1)
class RhevmClusterPolicies(TestCase):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Start vm on specific host for future migration
        """
        if not config.HOST_VM_MAP:
            raise errors.SkipTest("Number of hosts not enough to run test")
        logger.info("Starting all vms")
        for vm, host in config.HOST_VM_MAP.iteritems():
            logger.info("Run vm %s on host %s", vm, host)
            if not vm_api.runVmOnce(True, vm, host=host):
                raise errors.VMException("Failed to run vm")

    @classmethod
    def teardown_class(cls):
        """
        Stop vm
        """
        logger.info("Stopping all vms")
        vm_api.stop_vms_safely(config.VM_NAME[:3])
        logger.info("Update cluster policy to none")
        if not updateCluster(True, config.CLUSTER_NAME[0],
                             scheduling_policy=CLUSTER_POLICIES[2]):
            raise errors.ClusterException("Update cluster %s failed",
                                          config.CLUSTER_NAME[0])
        logger.info("Wait %s seconds until hosts update stats", UPDATE_STATS)
        time.sleep(UPDATE_STATS)

    @classmethod
    def _load_hosts_cpu(cls, hosts, load):
        """
        Load CPU of given hosts
        """
        for host in hosts:
            num_of_cpu = sla_api.get_num_of_cpus(host, config.HOSTS_USER,
                                                 config.HOSTS_PW)
            load_cpu = num_of_cpu / (100 / load)
            status = sla_api.load_cpu(host, config.HOSTS_USER,
                                      config.HOSTS_PW, load_cpu)
            if not status:
                logger.error("Loading host CPU failed")

    @classmethod
    def _release_hosts_cpu(cls, hosts):
        """
        Release hosts cpu's
        """
        for host in hosts:
            status = sla_api.stop_loading_cpu(host, config.HOSTS_USER,
                                              config.HOSTS_PW)
            if not status:
                logger.error("Stop CPU loading failed")

    def _check_migration(self, migration_host):
        """
        Check if vm migrated on given host in defined time
        """
        migration_duration = host_api.count_host_active_vms(
            migration_host, 2, timeout=WAIT_FOR_MIGRATION)
        status = True if migration_duration else False
        global timestamp
        if not timestamp:
            timestamp = True
            self.assertTrue(status and migration_duration >= DURATION)
        else:
            self.assertTrue(status)

    def _no_migration(self, host):
        """
        Check that no migration happened
        """
        self.assertTrue(vm_api.no_vm_migration(config.VM_NAME[0],
                                               host, WAIT_FOR_MIGRATION))

    def _maintenance_migration(self, src_host, dst_host):
        """
        Check that after deactivation of src host, vm migrated on dst host
        """
        self.assertTrue(
            vm_api.maintenance_vm_migration(config.VM_NAME[0],
                                            src_host, dst_host))


class EvenlyDistributed(RhevmClusterPolicies):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Evenly Distributed and run vm
        """
        if not updateCluster(True, config.CLUSTER_NAME[0],
                             scheduling_policy=CLUSTER_POLICIES[0],
                             thrhld_high=HIGH_UTILIZATION,
                             duration=DURATION):
            raise errors.ClusterException("Update cluster %s failed" %
                                          config.CLUSTER_NAME[0])
        super(EvenlyDistributed, cls).setup_class()


class PowerSaving(RhevmClusterPolicies):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Power Saving and run vm
        """
        if not updateCluster(True, config.CLUSTER_NAME[0],
                             scheduling_policy=CLUSTER_POLICIES[1],
                             thrhld_high=HIGH_UTILIZATION,
                             thrhld_low=LOW_UTILIZATION,
                             duration=DURATION):
            raise errors.ClusterException("Update cluster %s failed" %
                                          config.CLUSTER_NAME[0])
        super(PowerSaving, cls).setup_class()


class MigrateFromUnderUtilizedHost(PowerSaving):
    """
    Positive: Migrate vm from host with low CPU utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host without vm to 50%
        """
        super(MigrateFromUnderUtilizedHost, cls).setup_class()
        logger.info("Load host %s CPU up to %d percent",
                    config.HOSTS[1], AVERAGE_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[1]], AVERAGE_CPU_LOAD)

    @polarion("RHEVM3-9498")
    @istest
    def check_migration(self):
        """
        Vm run on host with low cpu utilization and must migrate to host
        with CPU utilization between Low
        and High utilization after CpuOverCommitDuration
        """
        self._check_migration(config.HOSTS[1])

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s CPU", config.HOSTS[1])
        cls._release_hosts_cpu([config.HOSTS[1]])
        super(MigrateFromUnderUtilizedHost, cls).teardown_class()


class NoAvailableHostForMigrationPS(PowerSaving):
    """
    Positive: No available host for migration, vm stay on old host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host without vm to 100%
        """
        super(NoAvailableHostForMigrationPS, cls).setup_class()
        logger.info("Load host %s CPU up to %d percent",
                    config.HOSTS[1], MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[1]], MAX_CPU_LOAD)

    @polarion("RHEVM3-9489")
    @istest
    def check_migration(self):
        """
        Vm run on host with low cpu utilization, but another host in cluster
        above maximum service level of CPU, so vm must stay on old host
        """
        self._no_migration(config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s CPU", config.HOSTS[1])
        cls._release_hosts_cpu([config.HOSTS[1]])
        super(NoAvailableHostForMigrationPS, cls).teardown_class()


class MigrationFromLowCPUUtilization(PowerSaving):
    """
    Positive: Migrate vm from host with low CPU utilization to host
     with average cpu level and not on host with high cpu utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host one without vm to average load and
         to maximal on host two without vm
        """
        super(MigrationFromLowCPUUtilization, cls).setup_class()
        logger.info("Load host %s CPU up to %d percent",
                    config.HOSTS[2], MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[2]], MAX_CPU_LOAD)
        logger.info("Load host %s CPU up to %d percent",
                    config.HOSTS[1], AVERAGE_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[1]], AVERAGE_CPU_LOAD)

    @polarion("RHEVM3-9490")
    @istest
    def check_migration(self):
        """
        Vm run on host with low CPU utilization, check that vm migrate from
        host with low CPU utilization, to host with correct
        utilization after CpuOverCommitDuration
        """
        self._check_migration(config.HOSTS[1])

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s and %s CPU",
                    config.HOSTS[1], config.HOSTS[2])
        cls._release_hosts_cpu([config.HOSTS[1], config.HOSTS[2]])
        super(MigrationFromLowCPUUtilization, cls).teardown_class()


class PutHostToMaintenancePS(PowerSaving):
    """
    Positive: Put host with vm to maintenance state, choose host for migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host with vm and on second host
        to correct utilization CPU level
        """
        logger.info("Load host %s and %s CPU up to %d percent",
                    config.HOSTS[0], config.HOSTS[1], AVERAGE_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[0],
                             config.HOSTS[1]], AVERAGE_CPU_LOAD)
        super(PutHostToMaintenancePS, cls).setup_class()

    @polarion("RHEVM3-9492")
    @istest
    def check_migration(self):
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
            raise errors.HostException("Activation of host %s failed" %
                                       config.HOSTS[0])
        logger.info("Release host %s and %s CPU",
                    config.HOSTS[0], config.HOSTS[1])
        cls._release_hosts_cpu([config.HOSTS[0], config.HOSTS[1]])
        super(PutHostToMaintenancePS, cls).teardown_class()


class MigrateFromOverUtilizedHost(EvenlyDistributed):
    """
    Positive: Migrate vm from host with high CPU utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host with vm to 100%
        """
        super(MigrateFromOverUtilizedHost, cls).setup_class()
        logger.info("Load hosts %s and %s CPU up to %d percent",
                    config.HOSTS[0], config.HOSTS[1], MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[0],
                             config.HOSTS[1]], MAX_CPU_LOAD)

    @polarion("RHEVM3-9493")
    @istest
    def check_migration(self):
        """
        Vm run on host with high cpu utilization and must migrate to host
        with correct CPU utilization after CpuOverCommitDuration
        """
        self._check_migration(config.HOSTS[2])

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s and %s CPU",
                    config.HOSTS[0], config.HOSTS[1])
        cls._release_hosts_cpu([config.HOSTS[0], config.HOSTS[1]])
        super(MigrateFromOverUtilizedHost, cls).teardown_class()


class NoAvailableHostForMigrationED(EvenlyDistributed):
    """
    Positive: No available host for migration, vm stay on old host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host without vm to 100%
        """
        super(NoAvailableHostForMigrationED, cls).setup_class()
        logger.info("Load host %s and %s CPU up to %d percent",
                    config.HOSTS[1], config.HOSTS[2], MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[1],
                             config.HOSTS[2]], MAX_CPU_LOAD)

    @polarion("RHEVM3-9494")
    @istest
    def check_migration(self):
        """
        Vm run on host with low cpu utilization, but another host in cluster
        above maximum service level of CPU, so vm must stay on old host
        """
        self._no_migration(config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s and %s CPU",
                    config.HOSTS[1], config.HOSTS[2])
        cls._release_hosts_cpu([config.HOSTS[1], config.HOSTS[2]])
        super(NoAvailableHostForMigrationED, cls).teardown_class()


class PutHostToMaintenanceED(EvenlyDistributed):
    """
    Positive: Put host with vm to maintenance state, choose host for migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host with vm and on second host
        to correct utilization CPU level
        """
        super(PutHostToMaintenanceED, cls).setup_class()
        logger.info("Load host %s CPU up to %d percent",
                    config.HOSTS[2], MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.HOSTS[2]], MAX_CPU_LOAD)

    @polarion("RHEVM3-9496")
    @istest
    def check_migration(self):
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
            raise errors.HostException("Activation of host %s failed" %
                                       config.HOSTS[0])
        logger.info("Release host %s CPU", config.HOSTS[2])
        cls._release_hosts_cpu([config.HOSTS[2]])
        super(PutHostToMaintenanceED, cls).teardown_class()


@attr(tier=0)
class CheckClusterPolicyParameters(TestCase):
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

    @istest
    def check_parameters_ed(self):
        """
        Check if cluster success to do update to Evenly Distributed
        with given parameters
        Added, because this bug:
        https://bugzilla.redhat.com/show_bug.cgi?id=1070704
        """
        logger.info("Change cluster policy to %s with parameters",
                    CLUSTER_POLICIES[0])
        self.assertTrue(updateCluster(True, config.CLUSTER_NAME[0],
                                      scheduling_policy=CLUSTER_POLICIES[0],
                                      thrhld_high=self.high_utilization,
                                      duration=self.duration))

    @istest
    def check_parameters_ps(self):
        """
        Check if cluster success to do update to Power Saving
        with given parameters
        Added, because this bug:
        https://bugzilla.redhat.com/show_bug.cgi?id=1070704
        """
        logger.info("Change cluster policy to %s with parameters",
                    CLUSTER_POLICIES[1])
        self.assertTrue(updateCluster(True, config.CLUSTER_NAME[0],
                                      scheduling_policy=CLUSTER_POLICIES[1],
                                      thrhld_high=self.high_utilization,
                                      thrhld_low=self.low_utilization,
                                      duration=self.duration))

    @classmethod
    def teardown_class(cls):
        logger.info("Update cluster policy to none")
        if not updateCluster(True, config.CLUSTER_NAME[0],
                             scheduling_policy=CLUSTER_POLICIES[2]):
            raise errors.ClusterException("Update cluster %s failed" %
                                          config.CLUSTER_NAME[0])
        time.sleep(UPDATE_STATS)
