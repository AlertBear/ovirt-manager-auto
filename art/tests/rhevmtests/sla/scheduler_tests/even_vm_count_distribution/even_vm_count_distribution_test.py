"""
Scheduler - Even Vm Count Distribution Test
Check different cases for start, migration and balancing when cluster policy
is Vm_Evenly_Distribute
"""

import time
import logging

from rhevmtests.sla import config
from nose.tools import istest
from art.unittest_lib import attr
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
from art.unittest_lib import SlaTest as TestCase
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
from art.rhevm_api.tests_lib.low_level.clusters import updateCluster


logger = logging.getLogger(__name__)

UPDATE_STATS = 30
WAIT_FOR_MIGRATION = 600
WAIT_FOR_BALANCING = 240
SLEEP_TIME = 5
NUM_OF_VM_NAME = 5
HOST_START_INDEX = 2
NUM_OF_VMS_ON_HOST = 3
ENUMS = opts['elements_conf']['RHEVM Enums']
CLUSTER_POLICIES = [ENUMS['scheduling_policy_vm_evenly_distributed'], 'none']
PROPERTIES = {'HighVmCount': 2, 'MigrationThreshold': 2, 'SpmVmGrace': 1}
NON_RESPONSIVE = ENUMS['host_state_non_responsive']

# BUGS:
# 1) Bug 1175824 - [JSON RPC] shutdown/reboot a host on state 'up'
#    result in fault behaviour which is resolved only by engine restart

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class EvenVmCountDistribution(TestCase):
    """Base test class"""
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Evenly Vm Count Distributed
        with default parameters
        """
        if not updateCluster(True, config.CLUSTER_NAME[0],
                             scheduling_policy=CLUSTER_POLICIES[0],
                             properties=PROPERTIES):
            raise errors.ClusterException("Update cluster %s failed" %
                                          config.CLUSTER_NAME[0])

    @classmethod
    def teardown_class(cls):
        """
        Stop vms and change cluster policy to 'None'
        """
        logger.info("Stop all vms")
        vm_api.stop_vms_safely(config.VM_NAME)
        logger.info("Update cluster policy to none")
        if not updateCluster(True, config.CLUSTER_NAME[0],
                             scheduling_policy=CLUSTER_POLICIES[1]):
            raise errors.ClusterException("Update cluster %s failed",
                                          config.CLUSTER_NAME[0])
        logger.info("Wait %s seconds until hosts update stats", UPDATE_STATS)
        time.sleep(UPDATE_STATS)

    @classmethod
    def _start_vms(cls, num_of_vms, index_host_2):
        """
        Start given number of vms, when vms from 0 to index_host_2, starts on
        host_1 and other vms starts on host_2
        """
        logger.info("Start part of vms on host %s and part on host %s",
                    config.HOSTS[0], config.HOSTS[1])
        for i in range(num_of_vms):
            if i < index_host_2:
                test_host = config.HOSTS[0]
            else:
                test_host = config.HOSTS[1]
            if not vm_api.runVmOnce(True, config.VM_NAME[i], host=test_host):
                raise errors.VMException("Vm exception")

    def _check_migration(self, migration_host, num_of_vms):
        """
        Check number of vms on given host
        """
        logger.info(
            "Wait until %d vms will be run on host %s",
            num_of_vms, migration_host
        )
        status = host_api.count_host_active_vms(
            migration_host,
            num_of_vms,
            WAIT_FOR_MIGRATION,
            SLEEP_TIME
        ) is not None
        self.assertTrue(status)


class TwoHostsTests(EvenVmCountDistribution):
    """
    Test cases with 2 hosts, so in setup need to deactivate third host
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Deactivate third host
        """
        logger.info("Deactivate host %s", config.HOSTS[2])
        if not host_api.deactivateHost(True, config.HOSTS[2]):
            raise errors.HostException("Deactivation of host %s failed",
                                       config.HOSTS[2])
        super(TwoHostsTests, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Activate third host
        """
        super(TwoHostsTests, cls).teardown_class()
        logger.info("Activate host %s", config.HOSTS[2])
        if not host_api.activateHost(True, config.HOSTS[2]):
            raise errors.HostException("Activation of host %s failed"
                                       % config.HOSTS[2])


class BalancingWithDefaultParameters(TwoHostsTests):
    """
    Positive: Balance server under vm_evenly_distributed cluster policy with
    default parameters
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run vms on specific hosts
        """
        logger.info("Start all vms on host %s", config.HOSTS[0])
        cls._start_vms(NUM_OF_VM_NAME, 5)
        super(BalancingWithDefaultParameters, cls).setup_class()

    @tcms('12212', '335371')
    @istest
    def check_migration(self):
        """
        All vms runs on host_1 and three of them must migrate to host_2,
        because balancing policy
        """
        self._check_migration(config.HOSTS[1], NUM_OF_VMS_ON_HOST)


class NoHostForMigration(TwoHostsTests):
    """
    Positive: Run equal number of vms on two different hosts and check
    that no migration appear under vm_evenly_distributed cluster policy
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run vms on specific hosts
        """
        cls._start_vms(NUM_OF_VM_NAME, HOST_START_INDEX)
        super(NoHostForMigration, cls).setup_class()

    @tcms('12212', '335393')
    @istest
    def check_migration(self):
        """
        Vms 1 and 2 runs on host_1 and 3,4 and 5 on host_2,
        so migration must not appear, because it's no hosts for balancing
        """
        logger.info("Wait %d seconds to check if balancing not activated",
                    WAIT_FOR_BALANCING)
        time.sleep(WAIT_FOR_BALANCING)
        self._check_migration(config.HOSTS[0], NUM_OF_VMS_ON_HOST - 1)


class StartVmUnderClusterPolicy(TwoHostsTests):
    """
    Positive: Start vms under vm_evenly_distributed cluster policy,
    when on host_1(SPM) and host_2 equal number of vms
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run vms on specific hosts
        """
        cls._start_vms(NUM_OF_VM_NAME - 1, HOST_START_INDEX)
        super(StartVmUnderClusterPolicy, cls).setup_class()

    @tcms('12212', '335397')
    @istest
    def check_migration(self):
        """
        Host_1 and host_2 have equal number of vms, but host_1 also SPM, so
        scheduling must choose host_2 to start vm on it
        """
        test_vm = config.VM_NAME[NUM_OF_VM_NAME - 1]
        logger.info("Start vm %s", test_vm)
        if not vm_api.startVm(True, test_vm):
            raise errors.VMException("Failed to start vm")
        self._check_migration(config.HOSTS[1], NUM_OF_VMS_ON_HOST)


@attr(tier=3)
class HaVmStartOnHostAboveMaxLevel(TwoHostsTests):
    """
    Positive: Start vms under vm_evenly_distributed cluster policy,
    when on host_1(SPM) two vms and on host_2 three vms, all vms on host_2 HA,
    after killing host_2 vms from host_2 must start on host_1
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run vms on specific hosts
        """
        host_pm = config.pm_mapping.get(
            config.VDS_HOSTS[1].network.hostname
        )
        if host_pm is None:
            raise errors.SkipTest(
                "Host %s with fqdn don't have power management" %
                config.HOSTS[1], host_pm
            )
        logger.info("Update host %s power management", config.HOSTS[1])
        if not host_api.updateHost(True, config.HOSTS[1], pm=True, **host_pm):
            raise errors.HostException("Can not update host %s"
                                       % config.HOSTS[1])
        logger.info("Start part of vms on host %s and part on host %s",
                    config.HOSTS[0], config.HOSTS[1])
        for i in range(NUM_OF_VM_NAME):
            if i < 2:
                test_host = config.HOSTS[0]
            else:
                test_host = config.HOSTS[1]
                logger.info("Enable HA option on vm %s", config.VM_NAME[i])
                if not vm_api.updateVm(True, config.VM_NAME[i],
                                       highly_available=True):
                    raise errors.VMException("Update of vm %s failed",
                                             config.VM_NAME[i])
            if not vm_api.runVmOnce(True, config.VM_NAME[i], host=test_host):
                raise errors.VMException("Failed to run vm")
        super(HaVmStartOnHostAboveMaxLevel, cls).setup_class()

    @tcms('12212', '338999')
    @bz({'1175824': {'engine': None, 'version': ['3.5']}})
    @istest
    def check_migration(self):
        """
        Kill host_2 with HA vms, vms from host_2 must start on host_1, despite
        max vms count on host_1
        """
        logger.info("Stop network service on host %s", config.HOSTS[1])
        if not host_api.runDelayedControlService(
                True, config.HOSTS[1], config.HOSTS_USER, config.HOSTS_PW,
                service='network', command='stop'
        ):
            raise errors.HostException("Trying to stop network"
                                       " on host %s failed",
                                       config.HOSTS[1])
        logger.info("Wait until host %s in non responsive state",
                    config.HOSTS[1])
        if not host_api.waitForHostsStates(True, config.HOSTS[1],
                                           states=NON_RESPONSIVE):
            raise errors.HostException("Host %s not in non responsive state",
                                       config.HOSTS[1])
        self._check_migration(config.HOSTS[0], NUM_OF_VM_NAME)

    @classmethod
    def teardown_class(cls):
        """
        Disable HA option on vms
        """
        if not host_api.waitForHostsStates(True, config.HOSTS[1]):
            raise errors.HostException("Host %s not in up state",
                                       config.HOSTS[1])
        super(HaVmStartOnHostAboveMaxLevel, cls).teardown_class()
        logger.info("Disable HA option on all vms")
        for vm in config.VM_NAME:
            if not vm_api.updateVm(True, vm,
                                   highly_available=False):
                raise errors.VMException("Update of vm %s failed", vm)
        logger.info("Disable power management on host %s", config.HOSTS[1])
        if not host_api.updateHost(True, config.HOSTS[1], pm=False):
            raise errors.HostException("Can not update host %s"
                                       % config.HOSTS[1])


class PutHostToMaintenance(EvenVmCountDistribution):
    """
    Positive: Start vms under vm_evenly_distributed cluster policy,
    when on host_1(SPM) two vms and on host_2 three vms, put host_2 to
    maintenance, as result all vms from host_2 must migrate on host_3
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run vms on specific hosts
        """
        cls._start_vms(NUM_OF_VM_NAME, HOST_START_INDEX)
        super(PutHostToMaintenance, cls).setup_class()

    @tcms('12212', '335394')
    @istest
    def check_migration(self):
        """
        Put host_2 to maintenance and check, where migrate vms from host_2
        """
        logger.info("Deactivate host %s", config.HOSTS[1])
        if not host_api.deactivateHost(True, config.HOSTS[1]):
            raise errors.HostException("Deactivate host %s failed"
                                       % config.HOSTS[1])
        self._check_migration(config.HOSTS[2], NUM_OF_VMS_ON_HOST)

    @classmethod
    def teardown_class(cls):
        """
        Activate host_2 and deactivate host_3
        """
        logger.info("Activate host %s", config.HOSTS[1])
        if not host_api.activateHost(True, config.HOSTS[1]):
            raise errors.HostException("Activation of host %s failed",
                                       config.HOSTS[1])
        super(PutHostToMaintenance, cls).teardown_class()


class MigrateVmUnderPolicy(EvenVmCountDistribution):
    """
    Positive: Start vms under vm_evenly_distributed cluster policy,
    when on host_1(SPM) one vm, on host_2 three vms and on host_3 one vm,
    migrate one of vms from host_2, without specify destination host, engine
    must migrate vm on host_3
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run vms on specific hosts
        """
        cls._start_vms(NUM_OF_VM_NAME - 1, HOST_START_INDEX - 1)
        if not vm_api.runVmOnce(True, config.VM_NAME[4], host=config.HOSTS[2]):
            raise errors.VMException("Failed to start vm")
        super(MigrateVmUnderPolicy, cls).setup_class()

    @tcms('12212', '335559')
    @istest
    def check_migration(self):
        """
        Migrate vm from host_2 and check number of vms on host_3
        """
        if not vm_api.migrateVm(True, config.VM_NAME[1]):
            raise errors.VMException("Failed to migrate vm")
        self._check_migration(config.HOSTS[2], NUM_OF_VMS_ON_HOST - 1)
