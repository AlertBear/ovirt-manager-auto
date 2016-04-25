"""
Scheduler - Power Saving with PM Test
Check different cases for power on and shutdown hosts when cluster policy
is Power Saving with power management enable
"""

import logging
import socket
import time

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import art.unittest_lib as u_lib
import rhevmtests.helpers as rhevm_helper
import rhevmtests.sla.config as conf
import rhevmtests.sla.helpers as sla_helpers
from art.test_handler.tools import polarion  # pylint: disable=E0611

logger = logging.getLogger(__name__)


def setup_module(module):
    """
    1) Select first host as SPM
    2) Configure power management on hosts
    """
    assert ll_hosts.select_host_as_spm(
        positive=True,
        host=conf.HOSTS[0],
        data_center=conf.DC_NAME[0]
    )
    hosts_resource = dict(zip(conf.HOSTS[:3], conf.VDS_HOSTS[:3]))
    for host_name, host_resource in hosts_resource.iteritems():
        host_fqdn = host_resource.fqdn
        host_pm = rhevm_helper.get_pm_details(host_fqdn).get(host_fqdn)
        if not host_pm:
            pytest.skip("Host %s does not have PM" % host_name)
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
            host_name=host_name,
            pm_automatic=True,
            pm_agents=[agent]
        )


def teardown_module(module):
    """
    1) Fence hosts, if needed
    2) Release hosts CPU
    """
    for host_name in conf.HOSTS[:3]:
        logger.info("Check if host %s has state down", host_name)
        host_status = ll_hosts.getHostState(host_name) == conf.HOST_DOWN
        if host_status:
            logger.info(
                "Wait %d seconds between fence operations",
                conf.FENCE_TIMEOUT
            )
            time.sleep(conf.FENCE_TIMEOUT)
            logger.info("Start host %s", host_name)
            if not ll_hosts.fenceHost(True, host_name, 'start'):
                logger.error("Failed to start host %s", host_name)
        hl_hosts.remove_power_management(host_name=host_name)
    logger.info("Free all host CPU's from loading")
    sla_helpers.stop_load_on_resources(
        hosts_and_resources_l=[
            {conf.RESOURCE: conf.VDS_HOSTS[:3], conf.HOST: conf.HOSTS[:3]}
        ]
    )

########################################################################
#                             Test Cases                               #
########################################################################


@u_lib.attr(tier=4)
class PowerSavingWithPM(u_lib.SlaTest):
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
        cls.vm_host_d = dict(
            (vm_name, {"host": host_name})
            for vm_name, host_name in zip(conf.VM_NAME[:3], conf.HOSTS[:3])
        )
        ll_vms.run_vms_once(vms=cls.vms_to_start, **cls.vm_host_d)
        if cls.hosts_to_load:
            sla_helpers.start_and_wait_for_cpu_load_on_resources(
                load_to_host_d={conf.CPU_LOAD_50: cls.hosts_to_load}
            )
        cls._update_hosts_in_reserve(1)

    @classmethod
    def teardown_class(cls):
        """
        Stop vms and update cluster policy to None
        """
        if cls.hosts_to_load:
            sla_helpers.stop_load_on_resources(
                hosts_and_resources_l=[cls.hosts_to_load]
            )
        ll_vms.stop_vms_safely(vms_list=cls.vms_to_start)
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )
        if cls.host_down:
            logger.info(
                "Wait %d seconds between fence operations",
                conf.FENCE_TIMEOUT
            )
            time.sleep(conf.FENCE_TIMEOUT)
            logger.info("Start host %s", cls.host_down)
            if not ll_hosts.fenceHost(
                positive=True, host=cls.host_down, fence_type="start"
            ):
                logger.error("Failed to start host %s", cls.host_down)

    @classmethod
    def _check_hosts_num_with_status(
        cls,
        num_of_hosts,
        hosts_state,
        timeout=conf.LONG_BALANCE_TIMEOUT,
        negative=False
    ):
        """
        Check that given number of hosts are in given state

        :param num_of_hosts: number of hosts
        :type num_of_hosts: int
        :param hosts_state: hosts state
        :type hosts_state: str
        :param timeout: sampler timeout
        :type timeout: int
        :returns: True, if given number of hosts has correct state,
        otherwise False
        :rtype: bool
        """
        return sla_helpers.wait_for_hosts_state_in_cluster(
            num_of_hosts=num_of_hosts,
            timeout=timeout,
            sleep=conf.SAMPLER_SLEEP,
            cluster_name=conf.CLUSTER_NAME[0],
            state=hosts_state,
            negative=negative
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
        return ll_hosts.getHostState(host).lower() == state

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
        if not ll_hosts.updateHost(
            positive=True,
            host=host_name,
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
            conf.HIGH_UTILIZATION: conf.HIGH_UTILIZATION_VALUE,
            conf.LOW_UTILIZATION: conf.LOW_UTILIZATION_VALUE,
            conf.OVER_COMMITMENT_DURATION: conf.OVER_COMMITMENT_DURATION_VALUE,
            'HostsInReserve': hosts_in_reserve,
            'EnableAutomaticHostPowerManagement': 'true'
        }
        logger.info("Update cluster policy hosts in reserve")
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_POWER_SAVING,
            properties=properties
        ):
            logger.error(
                "Failed to update cluster %s", conf.CLUSTER_NAME[0]
            )


class TestSPMHostNotKilledByPolicy(PowerSavingWithPM):
    """
    Check that SPM host not killed by policy
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.vms_to_start = conf.VM_NAME[1:3]
        cls.hosts_to_load = {
            conf.RESOURCE: [conf.VDS_HOSTS[1]],
            conf.HOST: [conf.HOSTS[1]]
        }
        cls.host_down = conf.HOSTS[2]
        super(TestSPMHostNotKilledByPolicy, cls).setup_class()

    @polarion("RHEVM3-5572")
    def test_check_spm(self):
        """
        Positive: Check that SPM host not turned off by cluster policy with
        enable_automatic_host_power_management=true, also when no vms on it
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, conf.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(conf.HOSTS[0], conf.HOST_UP) and result
        )


class TestHostWithoutCPULoadingShutdownByPolicy(PowerSavingWithPM):
    """
    Check that host without cpu loading shutdown by policy
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.vms_to_start = conf.VM_NAME[1:3]
        cls.hosts_to_load = {
            conf.RESOURCE: [conf.VDS_HOSTS[1]],
            conf.HOST: [conf.HOSTS[1]]
        }
        cls.host_down = conf.HOSTS[2]
        super(TestHostWithoutCPULoadingShutdownByPolicy, cls).setup_class()

    @polarion("RHEVM3-5580")
    def test_check_host_with_loading(self):
        """
        Positive: Check that host without CPU loading turned off by cluster
        policy with enable_automatic_host_power_management=true
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, conf.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(
                conf.HOSTS[2], conf.HOST_DOWN
            ) and result
        )


class TestHostStartedByPowerManagement(PowerSavingWithPM):
    """
    Host started by power management
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.vms_to_start = conf.VM_NAME[:2]
        cls.hosts_to_load = {
            conf.RESOURCE: [conf.VDS_HOSTS[1]],
            conf.HOST: [conf.HOSTS[1]]
        }
        super(TestHostStartedByPowerManagement, cls).setup_class()

    @polarion("RHEVM3-5577")
    def test_start_host(self):
        """
        Positive: Change cluster policy to Power_Saving with default
        parameters and wait until one of hosts turned off.
        After change HostsInReserve=2 and check if policy start host
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, conf.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(
                conf.HOSTS[2], conf.HOST_DOWN
            ) and result
        )
        self._update_hosts_in_reserve(2)
        self.assertTrue(self._check_hosts_num_with_status(3, conf.HOST_UP))


class TestCheckPolicyControlOfPowerManagementFlag(PowerSavingWithPM):
    """
    Check policy control of power management flag
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Disable host policy_control_flag
        """
        cls._policy_control_flag(conf.HOSTS[1], False)
        cls.vms_to_start = [conf.VM_NAME[0]]
        cls.host_down = conf.HOSTS[2]
        super(TestCheckPolicyControlOfPowerManagementFlag, cls).setup_class()

    @polarion("RHEVM3-5579")
    def test_disable_policy_control_flag(self):
        """
        Positive: Disable host_1 policy_control_flag, wait until
        one host will power off by policy, it must be host_2
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, conf.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(conf.HOSTS[1], conf.HOST_UP) and result
        )

    @classmethod
    def teardown_class(cls):
        """
        Enable host policy_control_flag
        """
        cls._policy_control_flag(conf.HOSTS[1], True)
        super(
            TestCheckPolicyControlOfPowerManagementFlag, cls
        ).teardown_class()


class TestStartHostWhenNoReservedHostLeft(PowerSavingWithPM):
    """
    Start host when no reserved host left
    """
    __test__ = True
    vms_to_start = [conf.VM_NAME[0]]
    additional_vm = None

    @polarion("RHEVM3-5576")
    def test_no_reserve_left(self):
        """
        Positive: Run vm on host with zero vms, policy must power on host,
        because no hosts in reserve remain.
        """
        logger.info("Wait until one host turned off")
        self.assertTrue(
            self._check_hosts_num_with_status(1, conf.HOST_DOWN),
            "Still no host in state DOWN"
        )
        logger.info("Check what host have state DOWN")
        host_status = ll_hosts.getHostState(conf.HOSTS[1]) == conf.HOST_UP
        host_up = conf.HOSTS[1] if host_status else conf.HOSTS[2]
        additional_vm = None
        for vm_name, vm_params in self.vm_host_d.iteritems():
            if vm_params["host"] == host_up:
                logger.info("Run vm %s on host %s", vm_name, vm_params["host"])
                self.assertTrue(
                    ll_vms.runVmOnce(
                        positive=True, vm=vm_name, host=vm_params["host"]
                    ),
                    "Failed to run vm %s" % vm_name
                )
                additional_vm = vm_name
                break
        self.assertTrue(self._check_hosts_num_with_status(3, conf.HOST_UP))
        logger.info("Stop additional vm %s", additional_vm)
        ll_vms.stop_vms_safely([additional_vm])


class TestNoExcessHosts(PowerSavingWithPM):
    """
    Check that host not turned off by power management,
    when is not enough hosts
    """
    __test__ = True
    vms_to_start = conf.VM_NAME[:2]

    @polarion("RHEVM3-5575")
    def test_reserved_equal_to_up_hosts(self):
        """
        Positive: Vms runs on host_0 and host_1, wait some time and check that
        engine not power off host without vm, because it must have one host in
        reserve.
        """
        self.assertFalse(
            self._check_hosts_num_with_status(
                num_of_hosts=3,
                hosts_state=conf.HOST_UP,
                negative=True,
                timeout=conf.SHORT_BALANCE_TIMEOUT
            )
        )


class TestHostStoppedUnexpectedly(PowerSavingWithPM):
    """
    Check that if host stopped unexpectedly, cluster policy start another host
    """
    __test__ = True
    vms_to_start = [conf.VM_NAME[0]]

    @classmethod
    def setup_class(cls):
        """
        Disable host policy_control_flag
        """
        cls._policy_control_flag(conf.HOSTS[1], False)
        super(TestHostStoppedUnexpectedly, cls).setup_class()

    @polarion("RHEVM3-5573")
    def test_host_stopped_unexpectedly(self):
        """
        Positive: Kill not SPM host network, engine must power on another
        host, because it not have hosts in reserve.
        """
        logger.info("Wait until one host turned off")
        result = self._check_hosts_num_with_status(1, conf.HOST_DOWN)
        self.assertTrue(
            self._check_host_status(
                conf.HOSTS[2], conf.HOST_DOWN
            ) and result
        )
        logger.info("Stop network on host %s", conf.HOSTS[1])
        try:
            conf.VDS_HOSTS[1].service('network').stop()
        except socket.timeout as ex:
            logger.warning("Host unreachable, %s", ex)
        logger.info(
            "Check if host %s in non-responsive state", conf.HOSTS[1]
        )
        self.assertTrue(
            ll_hosts.waitForHostsStates(
                True,
                conf.HOSTS[1],
                states=conf.HOST_NONRESPONSIVE
            ),
            "Host %s not in non-responsive state" % conf.HOSTS[1]
        )
        logger.info("Wait until another host up")
        self.assertTrue(
            self._check_hosts_num_with_status(2, conf.HOST_UP)
        )

    @classmethod
    def teardown_class(cls):
        """
        Check that all hosts up
        """
        cls._update_hosts_in_reserve(2)
        cls._check_hosts_num_with_status(3, conf.HOST_UP)
        cls._policy_control_flag(conf.HOSTS[1], True)
        super(TestHostStoppedUnexpectedly, cls).teardown_class()


class TestHostStoppedByUser(PowerSavingWithPM):
    """
    Check that host shutdown by user not started by power management
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Deactivate and stop host
        """
        cls.vms_to_start = [conf.VM_NAME[0]]
        cls.host_down = conf.HOSTS[1]
        super(TestHostStoppedByUser, cls).setup_class()
        cls._update_hosts_in_reserve(2)
        logger.info("Deactivate host %s", conf.HOSTS[1])
        if not ll_hosts.deactivateHost(True, conf.HOSTS[1]):
            raise errors.HostException("Fail to deactivate host")
        logger.info("Stop host %s via power management", conf.HOSTS[1])
        if not ll_hosts.fenceHost(
            positive=True, host=conf.HOSTS[1], fence_type="stop"
        ):
            raise errors.HostException(
                "Failed to stop host %s" % conf.HOSTS[1]
            )

    @polarion("RHEVM3-5574")
    def test_host_stopped_by_user(self):
        """
        Positive: User manually stop host, and this host must not be started
        by engine, also when no reserve hosts.
        """
        self.assertFalse(
            self._check_hosts_num_with_status(
                num_of_hosts=1,
                hosts_state=conf.HOST_DOWN,
                negative=True,
                timeout=conf.SHORT_BALANCE_TIMEOUT
            )
        )
