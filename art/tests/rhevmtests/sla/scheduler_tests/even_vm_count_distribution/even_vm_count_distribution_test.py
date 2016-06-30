"""
Scheduler - Even Vm Count Distribution Test
Check different cases for start, migration and balancing when cluster policy
is Vm_Evenly_Distribute
"""
import logging
import socket

from unittest2 import SkipTest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import art.unittest_lib as u_libs
import config as conf
import rhevmtests.helpers as rhevm_helper
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from art.test_handler.tools import polarion

logger = logging.getLogger(__name__)


def setup_module(module):
    """
    1) Choose first host as SPM
    """
    assert ll_hosts.select_host_as_spm(
        positive=True,
        host=conf.HOSTS[0],
        data_center=conf.DC_NAME[0]
    )

########################################################################
#                             Test Cases                               #
########################################################################


@u_libs.attr(tier=2)
class EvenVmCountDistribution(u_libs.SlaTest):
    """
    Base class for EvenVmCountDistribution policy
    """
    @classmethod
    def setup_class(cls):
        """
        Set cluster policies to Evenly Vm Count Distributed
        with default parameters
        """
        assert ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_EVEN_VM_DISTRIBUTION,
            properties=conf.EVEN_VM_COUNT_DISTRIBUTION_PARAMS
        )

    @classmethod
    def teardown_class(cls):
        """
        Stop vms and change cluster policy to 'None'
        """
        ll_vms.stop_vms_safely(conf.VM_NAME)
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )

    @classmethod
    def _start_vms(cls, num_of_vms, index_host_2):
        """
        Start given number of vms, when vms from 0 to index_host_2, starts on
        host_1 and other vms starts on host_2
        """
        logger.info(
            "Start part of vms on host %s and part on host %s",
            conf.HOSTS[0], conf.HOSTS[1]
        )
        vm_host_d = {}
        for i in range(num_of_vms):
            if i < index_host_2:
                test_host = conf.HOSTS[0]
            else:
                test_host = conf.HOSTS[1]
            vm_host_d[conf.VM_NAME[i]] = {"host": test_host}

        ll_vms.run_vms_once(vm_host_d.keys(), **vm_host_d)


class TwoHostsTests(EvenVmCountDistribution):
    """
    Test cases with 2 hosts, so in setup need to deactivate third host
    """
    @classmethod
    def setup_class(cls):
        """
        Deactivate third host
        """
        assert ll_hosts.deactivateHost(positive=True, host=conf.HOSTS[2])
        super(TwoHostsTests, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Activate third host
        """
        super(TwoHostsTests, cls).teardown_class()
        ll_hosts.activateHost(True, conf.HOSTS[2])


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
        logger.info("Start all vms on host %s", conf.HOSTS[0])
        cls._start_vms(conf.NUM_OF_VM_NAME, 5)
        super(BalancingWithDefaultParameters, cls).setup_class()

    @polarion("RHEVM3-5565")
    def test_check_migration(self):
        """
        All vms runs on host_1 and three of them must migrate to host_2,
        because balancing policy
        """
        self.assertTrue(
            sch_helpers.is_balancing_happen(
                host_name=conf.HOSTS[1],
                expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
                sampler_timeout=conf.LONG_BALANCE_TIMEOUT
            )
        )


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
        cls._start_vms(conf.NUM_OF_VM_NAME, conf.HOST_START_INDEX)
        super(NoHostForMigration, cls).setup_class()

    @polarion("RHEVM3-5566")
    def test_check_migration(self):
        """
        Vms 1 and 2 runs on host_1 and 3,4 and 5 on host_2,
        so migration must not appear, because it's no hosts for balancing
        """
        self.assertFalse(
            sch_helpers.is_balancing_happen(
                host_name=conf.HOSTS[0],
                expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST - 1,
                negative=True
            )
        )


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
        cls._start_vms(conf.NUM_OF_VM_NAME - 1, conf.HOST_START_INDEX)
        super(StartVmUnderClusterPolicy, cls).setup_class()

    @polarion("RHEVM3-5568")
    def test_check_migration(self):
        """
        Host_1 and host_2 have equal number of vms, but host_1 also SPM, so
        scheduling must choose host_2 to start vm on it
        """
        test_vm = conf.VM_NAME[conf.NUM_OF_VM_NAME - 1]
        assert ll_vms.startVm(positive=True, vm=test_vm)
        self.assertTrue(
            sch_helpers.is_balancing_happen(
                host_name=conf.HOSTS[1],
                expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
                sampler_timeout=conf.LONG_BALANCE_TIMEOUT
            )
        )


@u_libs.attr(tier=4)
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
        host_fqdn = conf.VDS_HOSTS[1].fqdn
        host_pm = rhevm_helper.get_pm_details(host_fqdn).get(host_fqdn)
        if not host_pm:
            raise SkipTest("Host %s don't have power management" % host_fqdn)
        agent_option = {
            "slot": host_pm[conf.PM_SLOT]
        } if conf.PM_SLOT in host_pm else None
        agent = {
            "agent_type": host_pm.get(conf.PM_TYPE),
            "agent_address": host_pm.get(conf.PM_ADDRESS),
            "agent_username": host_pm.get(conf.PM_USERNAME),
            "agent_password": host_pm.get(conf.PM_PASSWORD),
            "concurrent": False,
            "order": 1,
            "options": agent_option
        }

        assert hl_hosts.add_power_management(
            host_name=conf.HOSTS[1],
            pm_automatic=True,
            pm_agents=[agent],
            **host_pm
        )
        logger.info(
            "Start part of vms on host %s and part on host %s",
            conf.HOSTS[0], conf.HOSTS[1]
        )
        vm_host_d = {}
        for i in range(conf.NUM_OF_VM_NAME):
            if i < 2:
                test_host = conf.HOSTS[0]
            else:
                test_host = conf.HOSTS[1]
                assert ll_vms.updateVm(
                    positive=True, vm=conf.VM_NAME[i], highly_available=True
                )
            vm_host_d[conf.VM_NAME[i]] = {"host": test_host}
        ll_vms.run_vms_once(vm_host_d.keys(), **vm_host_d)
        super(HaVmStartOnHostAboveMaxLevel, cls).setup_class()

    @polarion("RHEVM3-5570")
    def test_check_migration(self):
        """
        Kill host_2 with HA vms, vms from host_2 must start on host_1, despite
        max vms count on host_1
        """
        logger.info("Stop network service on host %s", conf.HOSTS[1])
        try:
            conf.VDS_HOSTS[1].service("network").stop()
        except socket.timeout as ex:
            logger.warning("Host unreachable, %s", ex)
        assert ll_hosts.waitForHostsStates(
            positive=True, names=conf.HOSTS[1], states=conf.HOST_NONRESPONSIVE
        )
        self.assertTrue(
            sch_helpers.is_balancing_happen(
                host_name=conf.HOSTS[0],
                expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
                sampler_timeout=conf.LONG_BALANCE_TIMEOUT
            )
        )

    @classmethod
    def teardown_class(cls):
        """
        Disable HA option on vms
        """
        ll_hosts.waitForHostsStates(True, conf.HOSTS[1])
        super(HaVmStartOnHostAboveMaxLevel, cls).teardown_class()
        for vm in conf.VM_NAME:
            ll_vms.updateVm(
                positive=True, vm=vm, highly_available=False
            )
        hl_hosts.remove_power_management(hostname=conf.HOSTS[1])


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
        cls._start_vms(conf.NUM_OF_VM_NAME, conf.HOST_START_INDEX)
        super(PutHostToMaintenance, cls).setup_class()

    @polarion("RHEVM3-5567")
    def test_check_migration(self):
        """
        Put host_2 to maintenance and check, where migrate vms from host_2
        """
        assert ll_hosts.deactivateHost(True, conf.HOSTS[1])
        self.assertTrue(
            sch_helpers.is_balancing_happen(
                host_name=conf.HOSTS[2],
                expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST,
                sampler_timeout=conf.LONG_BALANCE_TIMEOUT
            )
        )
        assert ll_hosts.activateHost(True, conf.HOSTS[1])


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
        cls._start_vms(conf.NUM_OF_VM_NAME - 1, conf.HOST_START_INDEX - 1)
        if not ll_vms.runVmOnce(True, conf.VM_NAME[4], host=conf.HOSTS[2]):
            raise errors.VMException("Failed to start vm")
        super(MigrateVmUnderPolicy, cls).setup_class()

    @polarion("RHEVM3-5569")
    def test_check_migration(self):
        """
        Migrate vm from host_2 and check number of vms on host_3
        """
        if not ll_vms.migrateVm(True, conf.VM_NAME[1]):
            raise errors.VMException(
                "Failed to migrate vm %s" % conf.VM_NAME[1]
            )
        self.assertTrue(
            sch_helpers.is_balancing_happen(
                host_name=conf.HOSTS[2],
                expected_num_of_vms=conf.NUM_OF_VMS_ON_HOST - 1,
                sampler_timeout=conf.LONG_BALANCE_TIMEOUT
            )
        )
