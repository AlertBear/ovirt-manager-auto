"""
Scheduler - Rhevm Cluster Policies Test
Check different cases for migration when cluster police is Evenly Distributed
and Power Saving
"""
import time
import config
import random
import logging
from unittest import TestCase
from nose.tools import istest
from art.test_handler.tools import bz, tcms
from art.test_handler.settings import opts
import art.test_handler.exceptions as Errors
import art.rhevm_api.tests_lib.low_level.vms as Vm
import art.rhevm_api.tests_lib.low_level.sla as Sla
import art.rhevm_api.tests_lib.low_level.hosts as Host
from art.rhevm_api.tests_lib.low_level.clusters import updateCluster


logger = logging.getLogger(__name__)
timestamp = 0

MAX_CPU_LOAD = 100
AVERAGE_CPU_LOAD = 50
MIN_CPU_LOAD = 0
#Time to update hosts stats
UPDATE_STATS = 30
#Time to wait for vm migration MAX_DURATION + 60(for migration)
WAIT_FOR_MIGRATION = 240
#Generate random value for CpuOverCommitDuration
DURATION = random.randint(1, 2) * 60
#Generae random value HighUtilization
HIGH_UTILIZATION = random.randint(60, 90)
#Generae random value LowUtilization
LOW_UTILIZATION = random.randint(10, 30)
ENUMS = opts['elements_conf']['RHEVM Enums']
CLUSTER_POLICIES = [ENUMS['scheduling_policy_evenly_distributed'],
                    ENUMS['scheduling_policy_power_saving'], 'none']


class RhevmClusterPolicies(TestCase):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Start vm on specific host for future migration
        """
        logger.info("Starting vm %s", config.vm_for_migration)
        if not Vm.startVm(True, config.vm_for_migration):
            raise Errors.VMException("Starting vm failed")

    @classmethod
    def teardown_class(cls):
        """
        Stop vm
        """
        logger.info("Stopping vm %s", config.vm_for_migration)
        if not Vm.stopVms(config.vm_for_migration):
            raise Errors.VMException("Stopping vm failed")
        logger.info("Update cluster policy to none")
        if not updateCluster(True, config.cluster_name,
                             scheduling_policy=CLUSTER_POLICIES[2]):
            raise Errors.ClusterException("Update cluster %s failed",
                                          config.cluster_name)
        logger.info("Wait %s seconds until hosts update stats", UPDATE_STATS)
        time.sleep(UPDATE_STATS)

    @classmethod
    def _load_hosts_cpu(cls, hosts, load):
        """
        Load CPU of given hosts
        """
        for host in hosts:
            num_of_cpu = Sla.get_num_of_cpus(host, config.host_user,
                                             config.host_password)
            load_cpu = num_of_cpu / (100 / load)
            status = Sla.load_cpu(host, config.host_user,
                                  config.host_password, load_cpu)
            if not status:
                logger.error("Loading host CPU failed")

    @classmethod
    def _release_hosts_cpu(cls, hosts):
        """
        Release hosts cpu's
        """
        for host in hosts:
            status = Sla.stop_loading_cpu(host, config.host_user,
                                          config.host_password)
            if not status:
                logger.error("Stop CPU loading failed")

    def _check_migration(self, migration_host):
        """
        Check if vm migrated on given host in defined time
        """
        result, migration_duration = Vm.check_vm_migration(
            config.vm_for_migration, migration_host, WAIT_FOR_MIGRATION)
        global timestamp
        if not timestamp:
            timestamp = 1
            self.assertTrue(result and migration_duration >= DURATION)
        else:
            self.assertTrue(result)

    def _no_migration(self, host):
        """
        Check that no migration happened
        """
        self.assertTrue(Vm.no_vm_migration(config.vm_for_migration,
                                           host, WAIT_FOR_MIGRATION))

    def _maintenance_migration(self, src_host, dst_host):
        """
        Check that after deactivation of src host, vm migrated on dst host
        """
        self.assertTrue(Vm.maintenance_vm_migration(config.vm_for_migration,
                                                    src_host, dst_host))


class EvenlyDistributed(RhevmClusterPolicies):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Evenly Distributed and run vm
        """
        if not updateCluster(True, config.cluster_name,
                             scheduling_policy=CLUSTER_POLICIES[0],
                             thrhld_high=HIGH_UTILIZATION,
                             duration=DURATION):
            raise Errors.ClusterException("Update cluster %s failed" %
                                          config.cluster_name)
        super(EvenlyDistributed, cls).setup_class()


class PowerSaving(RhevmClusterPolicies):
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Power Saving and run vm
        """
        if not updateCluster(True, config.cluster_name,
                             scheduling_policy=CLUSTER_POLICIES[1],
                             thrhld_high=HIGH_UTILIZATION,
                             thrhld_low=LOW_UTILIZATION,
                             duration=DURATION):
            raise Errors.ClusterException("Update cluster %s failed" %
                                          config.cluster_name)
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
                    config.load_host_2, AVERAGE_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_2], AVERAGE_CPU_LOAD)

    @tcms('9904', '50879')
    @istest
    def check_migration(self):
        """
        Vm run on host with low cpu utilization and must migrate to host
        with CPU utilization between Low
        and High utilization after CpuOverCommitDuration
        """
        self._check_migration(config.load_host_2)

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s CPU", config.load_host_2)
        cls._release_hosts_cpu([config.load_host_2])
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
                    config.load_host_2, MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_2], MAX_CPU_LOAD)

    @tcms('9904', '50882')
    @istest
    def check_migration(self):
        """
        Vm run on host with low cpu utilization, but another host in cluster
        above maximum service level of CPU, so vm must stay on old host
        """
        self._no_migration(config.load_host_1)

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s CPU", config.load_host_2)
        cls._release_hosts_cpu([config.load_host_2])
        super(NoAvailableHostForMigrationPS, cls).teardown_class()


class MigrationFromHighCPUUtilization(PowerSaving):
    """
    Positive: Migrate vm from host with high CPU utilization
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set CPU load on host with vm to high utilization
        and other cost with correct CPU utilization
        """
        super(MigrationFromHighCPUUtilization, cls).setup_class()
        logger.info("Load host %s CPU up to %d percent",
                    config.load_host_1, MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_1], MAX_CPU_LOAD)
        logger.info("Load host %s CPU up to %d percent",
                    config.load_host_2, AVERAGE_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_2], AVERAGE_CPU_LOAD)

    @tcms('9904', '50884')
    @istest
    def check_migration(self):
        """
        Vm run on host with high CPU utilization, check that vm migrate from
        host with high CPU utilization, to host with correct
        utilization after CpuOverCommitDuration
        """
        self._check_migration(config.load_host_2)

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s and %s CPU",
                    config.load_host_1, config.load_host_2)
        cls._release_hosts_cpu([config.load_host_1, config.load_host_2])
        super(MigrationFromHighCPUUtilization,
              cls).teardown_class()


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
        super(PutHostToMaintenancePS, cls).setup_class()
        logger.info("Load host %s and %s CPU up to %d percent",
                    config.load_host_1, config.load_host_2, AVERAGE_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_1,
                             config.load_host_2], AVERAGE_CPU_LOAD)

    @tcms('9904', '50888')
    @istest
    def check_migration(self):
        """
        Vm run on host with correct cpu utilization, we put host to
        maintenance and check if vm migrated on host with correct
        CPU utilization level
        """
        self._maintenance_migration(config.load_host_1, config.load_host_2)

    @classmethod
    def teardown_class(cls):
        """
        Release hosts CPU, activate host and stop vm
        """
        if not Host.activateHost(True, config.load_host_1):
            raise Errors.HostException("Activation of host %s failed" %
                                       config.load_host_1)
        logger.info("Release host %s and %s CPU",
                    config.load_host_1, config.load_host_2)
        cls._release_hosts_cpu([config.load_host_1, config.load_host_2])
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
                    config.load_host_1, config.load_host_2, MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_1,
                             config.load_host_2], MAX_CPU_LOAD)

    @tcms('9904', '51149')
    @istest
    def check_migration(self):
        """
        Vm run on host with high cpu utilization and must migrate to host
        with correct CPU utilization after CpuOverCommitDuration
        """
        self._check_migration(config.load_host_3)

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s and %s CPU",
                    config.load_host_1, config.load_host_2)
        cls._release_hosts_cpu([config.load_host_1, config.load_host_2])
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
                    config.load_host_2, config.load_host_3, MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_2,
                             config.load_host_3], MAX_CPU_LOAD)

    @tcms('9904', '51152')
    @istest
    def check_migration(self):
        """
        Vm run on host with low cpu utilization, but another host in cluster
        above maximum service level of CPU, so vm must stay on old host
        """
        self._no_migration(config.load_host_1)

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU and stop vm
        """
        logger.info("Release host %s and %s CPU",
                    config.load_host_2, config.load_host_3)
        cls._release_hosts_cpu([config.load_host_2, config.load_host_3])
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
                    config.load_host_3, MAX_CPU_LOAD)
        cls._load_hosts_cpu([config.load_host_3], MAX_CPU_LOAD)

    @tcms('9904', '51185')
    @istest
    def check_migration(self):
        """
        Vm run on host with correct cpu utilization, we put host to
        maintenance and check if vm migrated on host with correct
        CPU utilization level
        """
        self._maintenance_migration(config.load_host_1, config.load_host_2)

    @classmethod
    def teardown_class(cls):
        """
        Release host CPU, activate host and stop vm
        """
        if not Host.activateHost(True, config.load_host_1):
            raise Errors.HostException("Activation of host %s failed" %
                                       config.load_host_1)
        logger.info("Release host %s CPU", config.load_host_3)
        cls._release_hosts_cpu([config.load_host_3])
        super(PutHostToMaintenanceED, cls).teardown_class()
