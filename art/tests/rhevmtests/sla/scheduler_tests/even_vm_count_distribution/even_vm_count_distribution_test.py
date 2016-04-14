"""
Scheduler - Even Vm Count Distribution Test
Check different cases for start, migration and balancing when cluster policy
is Vm_Evenly_Distribute
"""

import time
import logging

from unittest2 import SkipTest
from rhevmtests.sla import config
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
from art.unittest_lib import SlaTest as TestCase
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_cluster


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


def setup_module(module):
    """
    1) Choose first host as SPM
    """
    if not ll_hosts.select_host_as_spm(
        positive=True,
        host=config.HOSTS[0],
        data_center=config.DC_NAME[0]
    ):
        raise errors.HostException()

# BUGS:
# 1) Bug 1175824 - [JSON RPC] shutdown/reboot a host on state 'up'
#    result in fault behaviour which is resolved only by engine restart

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=2)
class EvenVmCountDistribution(TestCase):
    """Base test class"""
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Evenly Vm Count Distributed
        with default parameters
        """
        if not ll_cluster.updateCluster(
            positive=True,
            cluster=config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICIES[0],
            properties=PROPERTIES
        ):
            raise errors.ClusterException(
                "Update cluster %s failed" % config.CLUSTER_NAME[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop vms and change cluster policy to 'None'
        """
        logger.info("Stop all vms")
        ll_vms.stop_vms_safely(config.VM_NAME)
        logger.info("Update cluster policy to none")
        if not ll_cluster.updateCluster(
            positive=True,
            cluster=config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICIES[1]
        ):
            logger.error(
                "Update cluster %s failed", config.CLUSTER_NAME[0]
            )

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
            if not ll_vms.runVmOnce(True, config.VM_NAME[i], host=test_host):
                raise errors.VMException("Vm exception")

    def _check_migration(self, migration_host, num_of_vms):
        """
        Check number of vms on given host
        """
        logger.info(
            "Wait until %d vms will be run on host %s",
            num_of_vms, migration_host
        )
        self.assertTrue(
            ll_hosts.wait_for_active_vms_on_host(
                migration_host, num_of_vms, WAIT_FOR_MIGRATION, SLEEP_TIME
            )
        )


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
        if not ll_hosts.deactivateHost(True, config.HOSTS[2]):
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
        if not ll_hosts.activateHost(True, config.HOSTS[2]):
            logger.error("Activation of host %s failed", config.HOSTS[2])


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

    @polarion("RHEVM3-5565")
    def test_check_migration(self):
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

    @polarion("RHEVM3-5566")
    def test_check_migration(self):
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

    @polarion("RHEVM3-5568")
    def test_check_migration(self):
        """
        Host_1 and host_2 have equal number of vms, but host_1 also SPM, so
        scheduling must choose host_2 to start vm on it
        """
        test_vm = config.VM_NAME[NUM_OF_VM_NAME - 1]
        logger.info("Start vm %s", test_vm)
        if not ll_vms.startVm(True, test_vm):
            raise errors.VMException("Failed to start vm")
        self._check_migration(config.HOSTS[1], NUM_OF_VMS_ON_HOST)


@attr(tier=4)
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
            raise SkipTest(
                "Host %s with fqdn don't have power management" %
                config.HOSTS[1], host_pm
            )
        agent_option = {
            "slot": host_pm[config.PM_SLOT]
        } if config.PM_SLOT in host_pm else None
        agent = {
            "agent_type": host_pm.get(config.PM_TYPE),
            "agent_address": host_pm.get(config.PM_ADDRESS),
            "agent_username": host_pm.get(config.PM_USERNAME),
            "agent_password": host_pm.get(config.PM_PASSWORD),
            "concurrent": False,
            "order": 1,
            "options": agent_option
        }

        if not hl_hosts.add_power_management(
            host_name=config.HOSTS[1],
            pm_automatic=True,
            pm_agents=[agent],
            **host_pm
        ):
            raise errors.HostException(
                "Can not update host %s" % config.HOSTS[1]
            )
        logger.info("Start part of vms on host %s and part on host %s",
                    config.HOSTS[0], config.HOSTS[1])
        for i in range(NUM_OF_VM_NAME):
            if i < 2:
                test_host = config.HOSTS[0]
            else:
                test_host = config.HOSTS[1]
                logger.info("Enable HA option on vm %s", config.VM_NAME[i])
                if not ll_vms.updateVm(True, config.VM_NAME[i],
                                       highly_available=True):
                    raise errors.VMException("Update of vm %s failed",
                                             config.VM_NAME[i])
            if not ll_vms.runVmOnce(True, config.VM_NAME[i], host=test_host):
                raise errors.VMException("Failed to run vm")
        super(HaVmStartOnHostAboveMaxLevel, cls).setup_class()

    @polarion("RHEVM3-5570")
    def test_check_migration(self):
        """
        Kill host_2 with HA vms, vms from host_2 must start on host_1, despite
        max vms count on host_1
        """
        logger.info("Stop network service on host %s", config.HOSTS[1])
        if not ll_hosts.runDelayedControlService(
                True, config.HOSTS[1], config.HOSTS_USER, config.HOSTS_PW,
                service='network', command='stop'
        ):
            raise errors.HostException("Trying to stop network"
                                       " on host %s failed",
                                       config.HOSTS[1])
        logger.info("Wait until host %s in non responsive state",
                    config.HOSTS[1])
        if not ll_hosts.waitForHostsStates(True, config.HOSTS[1],
                                           states=NON_RESPONSIVE):
            raise errors.HostException("Host %s not in non responsive state",
                                       config.HOSTS[1])
        self._check_migration(config.HOSTS[0], NUM_OF_VM_NAME)

    @classmethod
    def teardown_class(cls):
        """
        Disable HA option on vms
        """
        if not ll_hosts.waitForHostsStates(True, config.HOSTS[1]):
            logger.error(
                "Host %s not in up state", config.HOSTS[1]
            )
        super(HaVmStartOnHostAboveMaxLevel, cls).teardown_class()
        logger.info("Disable HA option on all vms")
        for vm in config.VM_NAME:
            if not ll_vms.updateVm(
                positive=True, vm=vm, highly_available=False
            ):
                logger.error("Update of vm %s failed", vm)
        logger.info("Disable power management on host %s", config.HOSTS[1])
        if not ll_hosts.updateHost(
            positive=True, host=config.HOSTS[1], pm=False
        ):
            logger.error("Can not update host %s", config.HOSTS[1])


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

    @polarion("RHEVM3-5567")
    def test_check_migration(self):
        """
        Put host_2 to maintenance and check, where migrate vms from host_2
        """
        logger.info("Deactivate host %s", config.HOSTS[1])
        if not ll_hosts.deactivateHost(True, config.HOSTS[1]):
            raise errors.HostException(
                "Deactivate host %s failed" % config.HOSTS[1]
            )
        self._check_migration(config.HOSTS[2], NUM_OF_VMS_ON_HOST)
        logger.info("Activate host %s", config.HOSTS[1])
        if not ll_hosts.activateHost(True, config.HOSTS[1]):
            raise errors.HostException(
                "Activation of host %s failed", config.HOSTS[1]
            )


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
        if not ll_vms.runVmOnce(True, config.VM_NAME[4], host=config.HOSTS[2]):
            raise errors.VMException("Failed to start vm")
        super(MigrateVmUnderPolicy, cls).setup_class()

    @polarion("RHEVM3-5569")
    def test_check_migration(self):
        """
        Migrate vm from host_2 and check number of vms on host_3
        """
        if not ll_vms.migrateVm(True, config.VM_NAME[1]):
            raise errors.VMException("Failed to migrate vm")
        self._check_migration(config.HOSTS[2], NUM_OF_VMS_ON_HOST - 1)
