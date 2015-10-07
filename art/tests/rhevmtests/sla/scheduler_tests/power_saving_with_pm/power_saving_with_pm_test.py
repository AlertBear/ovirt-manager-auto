"""
Scheduler - Power Saving with PM Test
Check different cases for power on and shutdown hosts when cluster policy
is Power Saving with power management enable
"""

import time
import socket
import logging
from art.unittest_lib import attr
from art.unittest_lib import SlaTest as TestCase

from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.sla as sla_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
from art.rhevm_api.tests_lib.low_level.clusters import updateCluster
from rhevmtests.sla.scheduler_tests.power_saving_with_pm import config


logger = logging.getLogger(__name__)

# Load parameters
AVERAGE_CPU_LOAD = 50
# Timeout and sleep parameters
UPDATE_STATS = 30
WAIT_FOR_MIGRATION = 600
SAMPLE_TIME = 10
SLEEP_TIME = 300
# Cluster policy parameters
HIGH_UTILIZATION = 80
LOW_UTILIZATION = 20
DURATION = 1
CLUSTER_POLICY_NONE = 'none'
CLUSTER_POLICY_PS = config.ENUMS['scheduling_policy_power_saving']


########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=4)
class PowerSavingWithPM(TestCase):
    """
    Base class for power saving with power management test
    """
    __test__ = False
    vms_to_start = None
    hosts_to_load = None
    host_down = None

    @classmethod
    def setup_class(cls):
        """
        Start vms, update cluster policy to Power_Saving
        with default parameters and load host CPU
        """
        if not config.HOST_VM_MAP:
            raise errors.SkipTest("Number of hosts not enough to run test")
        logger.info("Start vms")
        for vm in cls.vms_to_start:
            logger.info("Run vm %s on host %s", vm, config.HOST_VM_MAP[vm])
            if not vm_api.runVmOnce(True, vm, host=config.HOST_VM_MAP[vm]):
                raise errors.VMException("Failed to run vm")
        if cls.hosts_to_load:
            if not sla_api.start_cpu_loading_on_resources(
                cls.hosts_to_load, AVERAGE_CPU_LOAD
            ):
                raise errors.HostException(
                    "Failed to load CPU on hosts %s" % cls.hosts_to_load
                )
        cls._update_hosts_in_reserve(1)

    @classmethod
    def teardown_class(cls):
        """
        Stop vms and update cluster policy to None
        """
        if cls.hosts_to_load:
            sla_api.stop_cpu_loading_on_resources(cls.hosts_to_load)
        logger.info("Stopping vms")
        vm_api.stop_vms_safely(cls.vms_to_start)
        logger.info("Update cluster policy to none")
        if not updateCluster(
            True,
            config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICY_NONE
        ):
            logger.error(
                "Update cluster %s failed", config.CLUSTER_NAME[0]
            )
        if cls.host_down:
            logger.info(
                "Wait %d seconds between fence operations",
                config.FENCE_TIMEOUT
            )
            time.sleep(config.FENCE_TIMEOUT)
            logger.info("Start host %s", cls.host_down)
            if not host_api.fenceHost(True, cls.host_down, 'start'):
                logger.error("Failed to start host %s", cls.host_down)

    @classmethod
    def _check_hosts_num_with_status(cls, num_of_hosts, hosts_state):
        """
        Check that given number of hosts are in given state

        :param num_of_hosts: number of hosts
        :type num_of_hosts: int
        :param hosts_state: hosts state
        :type hosts_state: str
        :returns: True, if given number of hosts has correct state,
        otherwise False
        :rtype: bool
        """
        cluster = config.CLUSTER_NAME[0]
        return host_api.wait_until_num_of_hosts_in_state(
            num_of_hosts,
            WAIT_FOR_MIGRATION,
            SAMPLE_TIME,
            cluster,
            state=hosts_state
        )

    @classmethod
    def _check_host_status(cls, host, state):
        """
        Check that given host in given state

        :param host: host name
        :type host: str
        :param state: host state
        :type state: str
        :return: True, if host is in correct state, otherwise False
        :rtype: bool
        """
        return host_api.getHostState(host).lower() == state

    @classmethod
    def _policy_control_flag(cls, host_name, flag):
        """
        Enable/Disable Policy Control Flag on host

        :param host_name: host name
        :type host_name: str
        :param flag: policy control flag
        :type flag: bool
        """
        logger.info("Set host %s policy control flag to %s", host_name, flag)
        if not host_api.updateHost(
            True,
            host_name,
            pm=True,
            pm_automatic=flag
        ):
            logger.error("Failed to update host %s", host_name)

    @classmethod
    def _update_hosts_in_reserve(cls, hosts_in_reserve):
        """
        Update cluster policy hosts in reserve parameter
        """
        properties = {
            'HighUtilization': HIGH_UTILIZATION,
            'LowUtilization': LOW_UTILIZATION,
            'CpuOverCommitDurationMinutes': DURATION,
            'HostsInReserve': hosts_in_reserve,
            'EnableAutomaticHostPowerManagement': 'true'
        }
        logger.info("Update cluster policy hosts in reserve")
        if not updateCluster(
            True,
            config.CLUSTER_NAME[0],
            scheduling_policy=CLUSTER_POLICY_PS,
            properties=properties
        ):
            logger.error(
                "Failed to update cluster %s", config.CLUSTER_NAME[0]
            )


class TestSPMHostNotKilledByPolicy(PowerSavingWithPM):
    """
    Check that SPM host not killed by policy
    """
    __test__ = True
    vms_to_start = config.VM_NAME[1:3]
    hosts_to_load = [config.VDS_HOSTS_WITH_DUMMY[1]]
    host_down = config.HOSTS_WITH_DUMMY[2]

    @polarion("RHEVM3-5572")
    def test_check_spm(self):
        """
        Positive: Check that SPM host not turned off by cluster policy with
        enable_automatic_host_power_management=true, also when no vms on it
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, config.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(config.HOSTS[0], config.HOST_UP) and result
        )


class TestHostWithoutCPULoadingShutdownByPolicy(PowerSavingWithPM):
    """
    Check that host without cpu loading shutdown by policy
    """
    __test__ = True
    vms_to_start = config.VM_NAME[1:3]
    hosts_to_load = [config.VDS_HOSTS_WITH_DUMMY[1]]
    host_down = config.HOSTS_WITH_DUMMY[2]

    @polarion("RHEVM3-5580")
    def test_check_host_with_loading(self):
        """
        Positive: Check that host without CPU loading turned off by cluster
        policy with enable_automatic_host_power_management=true
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, config.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(
                config.HOSTS[2], config.HOST_DOWN
            ) and result
        )


class TestHostStartedByPowerManagement(PowerSavingWithPM):
    """
    Host started by power management
    """
    __test__ = True
    vms_to_start = config.VM_NAME[:2]
    hosts_to_load = [config.VDS_HOSTS_WITH_DUMMY[1]]

    @polarion("RHEVM3-5577")
    def test_start_host(self):
        """
        Positive: Change cluster policy to Power_Saving with default
        parameters and wait until one of hosts turned off.
        After change HostsInReserve=2 and check if policy start host
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, config.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(
                config.HOSTS[2], config.HOST_DOWN
            ) and result
        )
        self._update_hosts_in_reserve(2)
        self.assertTrue(self._check_hosts_num_with_status(3, config.HOST_UP))


class TestCheckPolicyControlOfPowerManagementFlag(PowerSavingWithPM):
    """
    Check policy control of power management flag
    """
    __test__ = True
    vms_to_start = [config.VM_NAME[0]]
    host_down = config.HOSTS_WITH_DUMMY[2]

    @classmethod
    def setup_class(cls):
        """
        Disable host policy_control_flag
        """
        cls._policy_control_flag(config.HOSTS[1], False)
        super(TestCheckPolicyControlOfPowerManagementFlag, cls).setup_class()

    @polarion("RHEVM3-5579")
    def test_disable_policy_control_flag(self):
        """
        Positive: Disable host_1 policy_control_flag, wait until
        one host will power off by policy, it must be host_2
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, config.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(config.HOSTS[1], config.HOST_UP) and result
        )

    @classmethod
    def teardown_class(cls):
        """
        Enable host policy_control_flag
        """
        cls._policy_control_flag(config.HOSTS[1], True)
        super(
            TestCheckPolicyControlOfPowerManagementFlag, cls
        ).teardown_class()


class TestStartHostWhenNoReservedHostLeft(PowerSavingWithPM):
    """
    Start host when no reserved host left
    """
    __test__ = True
    vms_to_start = [config.VM_NAME[0]]
    additional_vm = None

    @polarion("RHEVM3-5576")
    def test_no_reserve_left(self):
        """
        Positive: Run vm on host with zero vms, policy must power on host,
        because no hosts in reserve remain.
        """
        logger.info("Wait until one host turned off")
        self.assertTrue(
            self._check_hosts_num_with_status(1, config.HOST_DOWN),
            "Still no host in state DOWN"
        )
        logger.info("Check what host have state DOWN")
        host_status = host_api.getHostState(config.HOSTS[1]) == config.HOST_UP
        host_up = config.HOSTS[1] if host_status else config.HOSTS[2]
        additional_vm = None
        for vm, host in config.HOST_VM_MAP.iteritems():
            if host == host_up:
                logger.info("Run vm %s on host %s", vm, host)
                self.assertTrue(
                    vm_api.runVmOnce(True, vm, host=host),
                    "Failed to run vm %s" % vm
                )
                additional_vm = vm
                break
        self.assertTrue(self._check_hosts_num_with_status(3, config.HOST_UP))
        logger.info("Stop additional vm %s", additional_vm)
        vm_api.stop_vms_safely([additional_vm])


class TestNoExcessHosts(PowerSavingWithPM):
    """
    Check that host not turned off by power management,
    when is not enough hosts
    """
    __test__ = True
    vms_to_start = config.VM_NAME[0:2]

    @polarion("RHEVM3-5575")
    def test_reserved_equal_to_up_hosts(self):
        """
        Positive: Vms runs on host_0 and host_1, wait some time and check that
        engine not power off host without vm, because it must have one host in
        reserve.
        """
        time.sleep(SLEEP_TIME)
        self.assertTrue(self._check_hosts_num_with_status(3, config.HOST_UP))


class TestHostStoppedUnexpectedly(PowerSavingWithPM):
    """
    Check that if host stopped unexpectedly, cluster policy start another host
    """
    __test__ = True
    vms_to_start = [config.VM_NAME[0]]

    @classmethod
    def setup_class(cls):
        """
        Disable host policy_control_flag
        """
        cls._policy_control_flag(config.HOSTS[1], False)
        super(TestHostStoppedUnexpectedly, cls).setup_class()

    @polarion("RHEVM3-5573")
    def test_host_stopped_unexpectedly(self):
        """
        Positive: Kill not SPM host network, engine must power on another
        host, because it not have hosts in reserve.
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, config.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(
                config.HOSTS[2], config.HOST_DOWN
            ) and result
        )
        logger.info("Stop network on host %s", config.HOSTS[1])
        try:
            config.VDS_HOSTS[1].service('network').stop()
        except socket.timeout as ex:
            logger.warning("Host unreachable, %s", ex)
        logger.info(
            "Check if host %s in non-responsive state", config.HOSTS[1]
        )
        self.assertTrue(
            host_api.waitForHostsStates(
                True,
                config.HOSTS[1],
                states=config.HOST_NONRESPONSIVE
            ),
            "Host %s not in non-responsive state" % config.HOSTS[1]
        )
        logger.info("Wait until another host up")
        self.assertTrue(
            self._check_hosts_num_with_status(2, config.HOST_UP)
        )

    @classmethod
    def teardown_class(cls):
        """
        Check that all hosts up
        """
        cls._update_hosts_in_reserve(2)
        cls._check_hosts_num_with_status(3, config.HOST_UP)
        cls._policy_control_flag(config.HOSTS[1], True)
        super(TestHostStoppedUnexpectedly, cls).teardown_class()


class TestHostStoppedByUser(PowerSavingWithPM):
    """
    Check that host shutdown by user not started by power management
    """
    __test__ = True
    vms_to_start = [config.VM_NAME[0]]
    host_down = config.HOSTS_WITH_DUMMY[1]

    @classmethod
    def setup_class(cls):
        """
        Deactivate and stop host
        """
        super(TestHostStoppedByUser, cls).setup_class()
        cls._update_hosts_in_reserve(2)
        logger.info("Deactivate host %s", config.HOSTS[1])
        if not host_api.deactivateHost(True, config.HOSTS[1]):
            raise errors.HostException("Fail to deactivate host")
        logger.info("Stop host %s via power management", config.HOSTS[1])
        if not host_api.fenceHost(True, config.HOSTS[1], 'stop'):
            raise errors.HostException("Fail to stop host")

    @polarion("RHEVM3-5574")
    def test_host_stopped_by_user(self):
        """
        Positive: User manually stop host, and this host must not be started
        by engine, also when no reserve hosts.
        """
        logger.info("Wait %s seconds", SLEEP_TIME)
        time.sleep(SLEEP_TIME)
        self.assertTrue(
            self._check_host_status(config.HOSTS[1], config.HOST_DOWN)
        )
