"""
Hosted Engine - HA Test
Check behaviour of ovirt-ha-agent under different conditions
"""
import re
import socket
import logging

import config as conf
from art.test_handler import tools
import art.unittest_lib as test_libs
import art.core_api.apis_utils as utils
import art.test_handler.exceptions as errors
import art.core_api.apis_exceptions as core_errors
import art.rhevm_api.tests_lib.low_level.sla as ll_sla

logger = logging.getLogger(__name__)

#############################################################################
#                       Base classes to inherit from it                     #
#############################################################################


class HostedEngineTest(test_libs.SlaTest):
    """
    Base class that include basic functions for whole test
    """
    __test__ = False

    @classmethod
    def _get_resource_by_name(cls, host_name):
        """
        Get VDS object by name

        :param host_name: host fqdn or ip
        :type host_name: str
        :returns: host resource or None
        :rtype: instance of VDS or None
        """
        for vds_resource in conf.VDS_HOSTS:
            logger.debug(
                "Host to search: %s; Host FQDN: %s",
                host_name, vds_resource.fqdn
            )
            if host_name in (vds_resource.ip, vds_resource.fqdn):
                return vds_resource
        return None

    @classmethod
    def _get_output_from_run_cmd(cls, executor, cmd, negative=False):
        """
        Run command on host and get output from it

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param cmd: command to run
        :type cmd: list
        :returns: output of command
        :rtype: str
        :raises: socket.timeout
        """
        logger.info("Run command: %s", cmd)
        try:
            rc, out, err = executor.run_cmd(
                cmd, tcp_timeout=conf.TCP_TIMEOUT, io_timeout=conf.IO_TIMEOUT
            )
        except socket.timeout as e:
            if negative:
                logger.debug("Socket timeout: %s", e)
                return ""
            else:
                raise
        else:
            if rc and not negative:
                raise errors.HostException(
                    "Failed to run command, err: %s; out: %s" % (err, out)
                )
            return out

    @classmethod
    def get_he_stats(cls, executor):
        """
        Get output of stats script and generate
        dictionary, where key is hostname

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :returns: dictionary of HE parameters
        :rtype: dict
        :raises: HostException
        """
        cmd = ["python", conf.SCRIPT_DEST_PATH]
        status_dict = eval(cls._get_output_from_run_cmd(executor, cmd))
        stat_d = {}
        for host_d in status_dict.itervalues():
            if conf.HOSTNAME in host_d:
                if conf.ENGINE_STATUS in host_d:
                    host_d[conf.ENGINE_STATUS] = eval(
                        host_d[conf.ENGINE_STATUS]
                    )
                stat_d[host_d.pop("hostname")] = host_d
        logger.debug("HE Dictionary: %s", stat_d)
        return stat_d

    @classmethod
    def _get_host_score(cls, executor, host_resource):
        """
        Get host HE score

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :returns: host score
        :rtype: int
        """
        return int(
            cls.get_he_stats(executor).get(host_resource.fqdn).get(conf.SCORE)
        )

    @classmethod
    def _get_host_up_to_date_status(cls, executor, host_resource):
        """
        Get host is up-to-date state

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :returns: host up-to-date state
        :rtype: str
        """
        return cls.get_he_stats(
            executor
        ).get(host_resource.fqdn).get(conf.UP_TO_DATE)

    @classmethod
    def _get_host_vm_state(cls, executor, host_resource):
        """
        Get host vm state

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :returns: host vm state
        :rtype: str
        """
        return cls.get_he_stats(
            executor
        ).get(host_resource.fqdn).get(conf.ENGINE_STATUS).get(conf.VM_STATE)

    @classmethod
    def _get_host_vm_health(cls, executor, host_resource):
        """
        Get host vm health

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :returns: host vm health
        :rtype: str
        """
        return cls.get_he_stats(
            executor
        ).get(
            host_resource.fqdn
        ).get(conf.ENGINE_STATUS).get(conf.ENGINE_HEALTH)

    @classmethod
    def _set_maintenance_mode(cls, executor, host_resource, mode):
        """
        Set global/local maintenance

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param mode: global, local or none
        :type mode: str
        """
        cmd = [conf.HOSTED_ENGINE_CMD, "--set-maintenance", "--mode=%s" % mode]
        logger.info(
            "Set maintenance mode of host %s to %s", host_resource, mode
        )
        cls._get_output_from_run_cmd(executor, cmd)

    @classmethod
    def _run_power_management_command(
            cls, host_resource, resource_to_fence, command
    ):
        """
        Run power management command via vdsClient

        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param resource_to_fence: resource to fence
        :type resource_to_fence: instance of VDS
        :param command: command to send(status, on, off, reboot)
        :type command: str
        :returns: True if action success, False otherwise
        :rtype: bool
        """
        host_pm = conf.pm_mapping.get(resource_to_fence.fqdn)
        if not host_pm:
            return False
        cmd = [
            "vdsClient", "-s", "0", "fenceNode",
            host_pm.get(conf.PM_ADDRESS),
            host_pm.get(conf.PM_SLOT, "0"),
            host_pm.get(conf.PM_TYPE),
            host_pm.get(conf.PM_USERNAME),
            host_pm.get(conf.PM_PASSWORD),
            command
        ]
        out = cls._get_output_from_run_cmd(
            host_resource.executor(), cmd
        )
        return out.strip() != "unknown"

    @classmethod
    def _check_host_power_management(cls, host_resource, resource_to_fence):
        """
        Check if host has power management

        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param resource_to_fence: resource to fence
        :type resource_to_fence: instance of VDS
        :returns: True if action success, False otherwise
        :rtype: bool
        """
        command = "status"
        return cls._run_power_management_command(
            host_resource, resource_to_fence, command
        )

    @classmethod
    def _restart_host_via_power_management(
            cls, host_resource, resource_to_fence
    ):
        """
        Restart host via power management from another host

        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param resource_to_fence: resource to fence
        :type resource_to_fence: instance of VDS
        :returns: True if action success, False otherwise
        :rtype: bool
        """
        command = "reboot"
        return cls._run_power_management_command(
            host_resource, resource_to_fence, command
        )

    @classmethod
    def _wait_for_parameter(
        cls, executor, host_resource, func, timeout, **kwargs
    ):
        """
        Wait until specific parameter appears for some host

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param func: function to send to TimeoutingSampler
        :type func: func
        :param timeout: sample until timeout pass
        :type timeout: int
        :param kwargs: parameters to wait
        :type kwargs: dict
        :returns: True, if parameter appear in given timeout, otherwise False
        :rtype: bool
        """
        sampler = utils.TimeoutingSampler(
            timeout, conf.SAMPLER_SLEEP, func, executor, host_resource
        )
        for key, value in kwargs.iteritems():
            try:
                for sample in sampler:
                    logger.info(
                        "Wait until host %s will has %s equal to %s, "
                        "now host have %s equal to %s",
                        host_resource, key, value, key, sample
                    )
                    if sample == kwargs.get(key):
                        return True
            except core_errors.APITimeout:
                logger.error(
                    "Timeout when waiting for host %s "
                    "to have parameter %s equal to %s",
                    host_resource, key, value
                )
                return False

    @classmethod
    def _wait_for_host_up_to_date_status(
        cls, executor, host_resource, timeout=conf.SAMPLER_TIMEOUT,
    ):
        """
        Wait until host is up-to-date

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param timeout: sampler timeout
        :type timeout: int
        :returns: True, if host is up-to-date appear in given timeout,
         otherwise False
        :rtype: bool
        """
        return cls._wait_for_parameter(
            executor,
            host_resource,
            cls._get_host_up_to_date_status,
            timeout,
            up_to_date=True
        )

    @classmethod
    def _wait_for_host_score(
        cls, executor, host_resource, score, timeout=conf.SAMPLER_TIMEOUT
    ):
        """
        Wait until host receive certain score

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param score: wait for score
        :type score: str
        :param timeout: sampler timeout
        :type timeout: int
        :returns: True, if host receive certain score in given timeout,
         otherwise False
        :rtype: bool
        """
        return cls._wait_for_parameter(
            executor,
            host_resource,
            cls._get_host_score,
            timeout,
            score=score
        )

    @classmethod
    def _wait_for_host_vm_state(
        cls, executor, host_resource, vm_state, timeout=conf.SAMPLER_TIMEOUT
    ):
        """
        Wait until host have certain vm state

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param vm_state: wait for vm state
        :type vm_state: str
        :param timeout: sampler timeout
        :type timeout: int
        :returns: True, if host receive certain vm state in given timeout,
         otherwise False
        :rtype: bool
        """
        return cls._wait_for_parameter(
            executor,
            host_resource,
            cls._get_host_vm_state,
            timeout,
            vm_state=vm_state
        )

    @classmethod
    def _wait_for_host_vm_health(
        cls, executor, host_resource, vm_health, timeout=conf.SAMPLER_TIMEOUT
    ):
        """
        Wait until host have certain vm health

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param vm_health: wait for vm health
        :type vm_health: str
        :param timeout: sampler timeout
        :type timeout: int
        :returns: True, if host receive certain vm state in given timeout,
         otherwise False
        :rtype: bool
        """
        return cls._wait_for_parameter(
            executor,
            host_resource,
            cls._get_host_vm_health,
            timeout,
            vm_health=vm_health
        )

    @classmethod
    def _drop_host_score_to_max(cls, executor, host_resource):
        """
        Put host to local maintenance and put it back to normal state
        to drop host score to maximal value(3400)

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :param host_resource: host resource
        :type host_resource: VDS
        """
        logger.info("Put host %s to local maintenance state", host_resource)
        cls._set_maintenance_mode(
            executor, host_resource, conf.MAINTENANCE_LOCAL
        )
        if not cls._wait_for_host_score(
                executor, host_resource, conf.ZERO_SCORE
        ):
            raise errors.HostException("Host not in local maintenance")
        logger.info("Put host %s to 'none' maintenance state", host_resource)
        cls._set_maintenance_mode(
            executor, host_resource, conf.MAINTENANCE_NONE
        )
        logger.info(
            "Check if host %s has maximal score %s",
            host_resource, conf.MAX_SCORE
        )
        if not cls._wait_for_host_score(
            executor, host_resource, conf.MAX_SCORE
        ):
            raise errors.HostException("Host not have maximal score")

    @classmethod
    def _is_sanlock_share(cls, executor):
        """
        Parse sanlock command "sanlock client status" and
        check if sanlock has share status

        :param executor: host executor
        :type executor: instance of RemoteExecutor
        :returns: True, if sanlock shared, otherwise False
        :rtype: bool
        """
        cmd = ["sanlock", "client", "status"]
        out = cls._get_output_from_run_cmd(executor, cmd)
        for line in out.splitlines():
            line_arr = line.strip().split()
            if line_arr[0].strip() == "r":
                return True
        return False


class GeneralSetupTeardownClass(HostedEngineTest):
    """
    General class to setup and teardown tests
    """
    __test__ = False
    engine_vm_host = None
    second_host = None
    engine_vm_host_executor = None
    second_host_executor = None
    engine_vm_executor = None

    def _is_vm_and_engine_run_on_second_host(
        self, timeout=conf.SAMPLER_TIMEOUT
    ):
        """
        Check if vm and engine succeed to run on second host

        :param timeout: sampler timeout
        :type timeout: int
        """
        logger.info("Check if vm started on host %s", self.second_host)
        self.assertTrue(
            self._wait_for_host_vm_state(
                executor=self.second_host_executor,
                host_resource=self.second_host,
                timeout=timeout,
                vm_state=conf.VM_STATE_UP
            ),
            conf.VM_NOT_STARTED_ON_SECOND_HOST
        )
        logger.info("Check if engine started on host %s", self.second_host)
        self.assertTrue(
            self._wait_for_host_vm_health(
                executor=self.second_host_executor,
                host_resource=self.second_host,
                timeout=timeout,
                vm_health=conf.ENGINE_HEALTH_GOOD
            ),
            conf.ENGINE_NOT_STARTED_ON_SECOND_HOST
        )

    @classmethod
    def setup_class(cls):
        """
        Check on what host run vm
        """
        logger.info("Check where run engine-vm")
        he_stats = cls.get_he_stats(conf.VDS_HOSTS[0].executor())
        for host_name, host_d in he_stats.iteritems():
            host_res = cls._get_resource_by_name(host_name)
            if host_d.get(
                conf.ENGINE_STATUS
            ).get(conf.VM_STATE) == conf.VM_STATE_UP:
                cls.engine_vm_host = host_res
            else:
                cls.second_host = host_res
        logger.info("HE vm run on host %s", cls.engine_vm_host)
        logger.info("No HE vm on host %s", cls.second_host)
        if not cls.engine_vm_host or not cls.second_host:
            raise errors.HostException(
                "Failed to receive information about one of hosts"
            )
        cls.engine_vm_host_executor = cls.engine_vm_host.executor()
        cls.engine_vm_executor = conf.ENGINE_HOST.executor()
        cls.second_host_executor = cls.second_host.executor()

    @classmethod
    def teardown_class(cls):
        """
        Drop host HE score
        """
        for host_resource in (cls.engine_vm_host, cls.second_host):
            logger.info("Check if host %s is up to date", host_resource)
            for host_executor in (
                cls.second_host_executor, cls.engine_vm_host_executor
            ):
                if not cls._get_host_up_to_date_status(
                    host_executor, host_resource
                ) and not cls._wait_for_host_up_to_date_status(
                    executor=host_executor,
                    host_resource=host_resource,
                    timeout=conf.WAIT_FOR_STATE_TIMEOUT
                ):
                    logger.error("Host %s still not up to date", host_resource)
            logger.info("Check host %s HE score", host_resource)
            if cls._get_host_score(
                cls.second_host_executor, host_resource
            ) < conf.MAX_SCORE:
                logger.info("Drop host %s HE score", host_resource)
                cls._drop_host_score_to_max(
                    host_resource.executor(), host_resource
                )

    @classmethod
    def _is_engine_vm_restarted(cls):
        """
        Check if vm is restarted

        :return: True, if vm success to run on one of hosts, otherwise False
        :rtype: bool
        """
        he_stats = cls.get_he_stats(cls.second_host_executor)
        for host_d in he_stats.values():
            engine_status = host_d.get(conf.ENGINE_STATUS)
            if (
                engine_status.get(conf.VM_STATE) == conf.VM_STATE_UP and
                engine_status.get(
                    conf.ENGINE_HEALTH
                ) == conf.ENGINE_HEALTH_GOOD
            ):
                return True
        return False

    @classmethod
    def _is_engine_down(cls):
        """
        Check if engine is down

        :return: True, if engine is down, otherwise False
        :rtype: bool
        """
        he_stats = cls.get_he_stats(cls.second_host_executor)
        for host_d in he_stats.values():
            engine_status = host_d.get(conf.ENGINE_STATUS)
            if engine_status.get(conf.ENGINE_HEALTH) != conf.ENGINE_HEALTH_BAD:
                return False
        return True

    @classmethod
    def _wait_for_vm_and_engine_state(cls, func):
        """
        Wait for specific engine and vm state

        :param func: state function
        :type func: function
        :return: True, if vm and engine have specific state in given timeout,
         otherwise False
        :rtype: bool
        """
        sampler = utils.TimeoutingSampler(
            conf.WAIT_FOR_STATE_TIMEOUT, conf.SAMPLER_SLEEP, func
        )
        try:
            for sample in sampler:
                logger.info(
                    "Wait until method %s return True", func.__name__
                )
                if sample:
                    return True
        except core_errors.APITimeout:
            logger.error(
                "Timeout: after %d seconds method %s return False",
                conf.SAMPLER_TIMEOUT, func.__name__
            )
            return False

    @classmethod
    def _wait_until_engine_vm_restarted(cls):
        """
        Wait until engine vm will start on one of hosts

        :return: True, if vm restarted, otherwise False
        :rtype: bool
        """
        return cls._wait_for_vm_and_engine_state(cls._is_engine_vm_restarted)

    @classmethod
    def _wait_until_engine_down(cls):
        """
        Wait until engine is down

        :return: True, if engine is down, otherwise False
        :rtype: bool
        """
        return cls._wait_for_vm_and_engine_state(cls._is_engine_down)

    @classmethod
    def _check_vm_status_via_vdsClient(cls, host, status=None):
        """
        Check if VM up on host via vdsClient

        :param host: host resource
        :type host: VDS
        :returns: True, if VM up on host, otherwise False
        :rtype: bool
        """
        cmd = ["vdsClient", "-s", "0", "list", "table"]
        out = cls._get_output_from_run_cmd(host.executor(), cmd)
        try:
            if out == "" or (status and out.split()[3].lower() != status):
                return False
        except IndexError:
            logger.error("Not expected output of command: %s", out)
            return False
        return True

    @classmethod
    def _check_he_vm_via_vdsClient(cls, host, status=None):
        """
        Check that HE vm stay on the same host via vdsClient

        :param host: host resource
        :type host: VDS
        :returns: True, if VM stay on the same host, otherwise False
        :rtype: bool
        """
        logger.info("Check that HE vm not start on host %s", host)
        sampler = utils.TimeoutingSampler(
            conf.WAIT_TIMEOUT,
            conf.SAMPLER_SLEEP,
            cls._check_vm_status_via_vdsClient,
            host,
            status
        )
        try:
            for sample in sampler:
                if sample:
                    return False
        except core_errors.APITimeout:
            logger.info("HE vm still run on host %s", host)
            return True


#############################################################################
#                         Problems on host with HE vm                       #
#############################################################################


class TestHostWithVmLostConnection(GeneralSetupTeardownClass):
    """
    Stop network on host where engine-vm runs and
    check if it started on second host
    """
    __test__ = True
    skip = False

    @tools.polarion("RHEVM3-5536")
    def test_check_migration_of_he_vm(self):
        """
        Check that there is a PM on the host where the engine VM runs
        If there is PM then stop the network service on host and check that
        the engine VM starts on the second host, otherwise skip the test
        """
        logger.info(
            "Check if host %s has power management", self.engine_vm_host.fqdn
        )
        if not self._check_host_power_management(
            self.second_host, self.engine_vm_host
        ):
            self.__class__.skip = True
            raise errors.SkipTest("Host doesn't have power management")
        logger.info("Stop network on host %s", self.engine_vm_host)
        try:
            self.engine_vm_host.service("network").stop()
        except socket.timeout as ex:
            logger.warning("Host unreachable, %s", ex)
        logger.info("Check if vm started on host %s", self.second_host)
        self.assertTrue(
            self._wait_for_host_vm_state(
                executor=self.second_host_executor,
                host_resource=self.second_host,
                vm_state=conf.VM_STATE_UP
            ),
            conf.VM_NOT_STARTED_ON_SECOND_HOST
        )

    @classmethod
    def teardown_class(cls):
        """
        Restart first host via power management and
        wait until host is up with state ENGINE_DOWN
        """
        if not cls.skip:
            logger.info(
                "Restart host %s via power management", cls.engine_vm_host
            )
            status = cls._restart_host_via_power_management(
                cls.second_host, cls.engine_vm_host
            )
            if not status:
                logger.error(
                    "Failed to restart host %s via power management",
                    cls.engine_vm_host
                )
            logger.info(
                "Wait until host %s has up to date data", cls.engine_vm_host
            )
            if not cls._wait_for_host_up_to_date_status(
                cls.second_host_executor,
                cls.engine_vm_host,
                timeout=conf.POWER_MANAGEMENT_TIMEOUT
            ):
                logger.error(
                    "Host %s still not have update status", cls.engine_vm_host
                )
            super(TestHostWithVmLostConnection, cls).teardown_class()
        else:
            cls.skip = False


class TestBlockAccessToStorageDomainFromHost(GeneralSetupTeardownClass):
    """
    Block access to storage on host where HE runs and
    check if VM migrated to the second host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Block access to storage via iptables
        """
        super(TestBlockAccessToStorageDomainFromHost, cls).setup_class()
        logger.info(
            "Save iptables on host %s to file %s",
            cls.engine_vm_host, conf.IPTABLES_BACKUP_FILE
        )
        cls._get_output_from_run_cmd(
            cls.engine_vm_host_executor,
            ['iptables-save', '>>', conf.IPTABLES_BACKUP_FILE]
        )
        logger.info(
            "Block connection from host %s to storage", cls.engine_vm_host
        )
        cmd = ["grep", "storage=", conf.HOSTED_ENGINE_CONF_FILE]
        out = cls._get_output_from_run_cmd(
            cls.engine_vm_host_executor, cmd
        )
        ip_to_block = out.split("=")[1].split(":")[0].strip('\n')
        cmd = ["iptables", "-I", "INPUT", "-s", ip_to_block, "-j", "DROP"]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)

    @tools.polarion("RHEVM3-5514")
    def test_check_migration_of_ha_vm(self):
        """
        Check if HE vm was migrated to another host
        """
        self._is_vm_and_engine_run_on_second_host()

    @classmethod
    def teardown_class(cls):
        """
        Accept access to storage from host
        """
        logger.info(
            "Restore iptables on host %s from file %s",
            cls.engine_vm_host, conf.IPTABLES_BACKUP_FILE
        )
        cls._get_output_from_run_cmd(
            cls.engine_vm_host_executor,
            ['iptables-restore', conf.IPTABLES_BACKUP_FILE]
        )
        logger.info("Check if %s service up", conf.AGENT_SERVICE)
        service_executor = cls.engine_vm_host.service(conf.AGENT_SERVICE)
        if not service_executor.status():
            logger.info(
                "Start service %s on host %s",
                service_executor, cls.engine_vm_host
            )
            service_executor.start()
        super(TestBlockAccessToStorageDomainFromHost, cls).teardown_class()


#############################################################################
#     HA agent must migrate engine VM, if it enter to problematic state     #
#############################################################################


class TestShutdownEngineMachine(GeneralSetupTeardownClass):
    """
    Shutdown HE vm and check if vm restarted on one of hosts
    """
    __test__ = True

    @tools.polarion("RHEVM3-5528")
    def test_check_hosted_engine_vm(self):
        """
        Shutdown HE vm and check if vm restarted on one of hosts
        """
        cmd = ["shutdown", "-h", "now"]
        self._get_output_from_run_cmd(
            executor=self.engine_vm_executor, cmd=cmd, negative=True
        )
        self._is_vm_and_engine_run_on_second_host()


class TestStopEngineService(GeneralSetupTeardownClass):
    """
    Stop ovirt-engine service on HE vm and
    check if vm restarted on one of hosts
    """
    __test__ = True

    @tools.polarion("RHEVM3-5533")
    def test_check_hosted_engine_vm(self):
        """
        Stop ovirt-engine service on HE vm and
        check if vm restarted on one of hosts
        """
        cmd = ["service", "ovirt-engine", "stop"]
        self._get_output_from_run_cmd(self.engine_vm_executor, cmd)
        self.assertTrue(
            self._wait_until_engine_down(), conf.ENGINE_UP
        )
        self.assertTrue(
            self._wait_until_engine_vm_restarted(), conf.HE_VM_NOT_STARTED
        )


class TestStopPostgresqlService(GeneralSetupTeardownClass):
    """
    Stop postgresql service on HE vm and check if vm restarted on one of hosts
    """
    __test__ = True

    @tools.polarion("RHEVM3-5520")
    def test_check_hosted_engine_vm(self):
        """
        Stop postrgresql service on HE vm and
        check if vm restarted on one of hosts
        """
        cmd = ["service", "postgresql", "stop"]
        self._get_output_from_run_cmd(self.engine_vm_executor, cmd)
        self.assertTrue(
            self._wait_until_engine_down(), conf.ENGINE_UP
        )
        self.assertTrue(
            self._wait_until_engine_vm_restarted(), conf.HE_VM_NOT_STARTED
        )


class TestKernelPanicOnEngineVm(GeneralSetupTeardownClass):
    """
    Simulate kernel panic on engine vm and
    check if it restarted on one of hosts
    """
    __test__ = True

    @tools.polarion("RHEVM3-5527")
    def test_check_hosted_engine_vm(self):
        """
        Simulate kernel panic on engine vm and
        check if it restarted on one of hosts
        """
        cmd = ["echo", "c", ">", "/proc/sysrq-trigger"]
        self._get_output_from_run_cmd(
            executor=self.engine_vm_executor, cmd=cmd, negative=True
        )
        self.assertTrue(
            self._wait_until_engine_down(), conf.ENGINE_UP
        )
        self.assertTrue(
            self._wait_until_engine_vm_restarted(), conf.HE_VM_NOT_STARTED
        )

#############################################################################


class TestSanlockStatusOnHosts(GeneralSetupTeardownClass):
    """
    Check status of sanlock on host with HE vm and without
    """
    __test__ = True

    @tools.polarion("RHEVM3-5531")
    def test_check_sanlock_status_on_host_with_he_vm(self):
        """
        Check if sanlock status equal to shared on host with HE vm
        """
        logger.info("Check status equal to shared on host with HE vm")
        self.assertTrue(
            self._is_sanlock_share(self.engine_vm_host_executor),
            "Host with HE vm has sanlock free, but should be shared"
        )

    @tools.polarion("RHEVM3-5532")
    def test_check_sanlock_status_on_host_without_he_vm(self):
        """
        Check if sanlock status equal to free on host without HE vm
        """
        logger.info("Check status equal to free on host with HE vm")
        self.assertFalse(
            self._is_sanlock_share(self.second_host_executor),
            "Host without HE vm has shared sanlock, but should have it free"
        )


class TestStartTwoEngineVmsOnHost(GeneralSetupTeardownClass):
    """
    Start HE vm on the same or on different host, when it already run
    """
    __test__ = True
    command = [conf.HOSTED_ENGINE_CMD, "--vm-start"]

    @tools.polarion("RHEVM3-5524")
    def test_start_two_he_vms_on_the_same_host(self):
        """
        Negative: Try to start two HE vms on the same host
        and check return message
        """
        correct_message = "VM exists and its status is Up"
        out = self._get_output_from_run_cmd(
            self.engine_vm_host_executor, self.command, negative=True
        )
        logger.info("Command hosted-engine --vm-start output: %s", out)
        self.assertEqual(out.strip('\n'), correct_message)

    @tools.polarion("RHEVM3-5513")
    def test_start_he_vm_on_second_host_when_it_already_run_on_first(self):
        """
        Negative: Try to start HE vm on the second host, when it already
        runs on first host and check return message
        """
        self._get_output_from_run_cmd(self.second_host_executor, self.command)
        self.assertTrue(
            self._check_he_vm_via_vdsClient(
                self.second_host,
                status=conf.VM_UP
            )
        )


class TestSynchronizeStateBetweenHosts(GeneralSetupTeardownClass):
    """
    Check if both hosts in HE environment return
    the same output for "hosted-engine --vm-status"
    """
    __test__ = True

    @tools.polarion("RHEVM3-5534")
    def test_check_he_status_on_hosts(self):
        """
        Check if HE status equals on both hosts
        """
        statuses = []
        cmd = [conf.HOSTED_ENGINE_CMD, "--vm-status"]
        for executor in (
            self.engine_vm_host_executor, self.second_host_executor
        ):
            out = re.sub(
                r'\n.*timestamp.*|\n.*crc32.*', '',
                self._get_output_from_run_cmd(executor, cmd)
            )
            statuses.append(out)
        logger.info("Check if status on both hosts the same")
        self.assertEqual(
            statuses[0], statuses[1],
            "Hosts have different HE status: %s and %s" %
            (statuses[0], statuses[1])
        )

#############################################################################
#                    Check score penalties on hosts                         #
#############################################################################


class TestHostGatewayProblem(GeneralSetupTeardownClass):
    """
    Change gateway address on host where run HE vm and check if vm migrate to
    another host because difference in scores
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Save old gateway address and change to new one
        """
        super(TestHostGatewayProblem, cls).setup_class()
        # Workaround for RHEV-H
        # Can not sed hosted-engine configuration file under original directory
        cmd = [
            conf.COPY_CMD,
            conf.HOSTED_ENGINE_CONF_FILE,
            conf.HOSTED_ENGINE_CONF_FILE_BACKUP
        ]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)
        cmd = [
            conf.COPY_CMD,
            conf.HOSTED_ENGINE_CONF_FILE,
            conf.HOSTED_ENGINE_CONF_FILE_TMP
        ]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)
        cmd = [
            "sed", "-i", "s/^gateway=.*/gateway=1.1.1.1/",
            conf.HOSTED_ENGINE_CONF_FILE_TMP
        ]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)
        cmd = [
            conf.COPY_CMD,
            conf.HOSTED_ENGINE_CONF_FILE_TMP,
            conf.HOSTED_ENGINE_CONF_FILE
        ]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)
        cls.engine_vm_host.service(conf.AGENT_SERVICE).restart()

    @tools.polarion("RHEVM3-5535")
    def test_check_he_vm_and_host_score(self):
        """
        Check that score of host with HE vm dropped to 800 and
        check that vm migrated to second host
        """
        logger.info(
            "Wait util host %s score will dropped to %s",
            self.engine_vm_host, conf.GATEWAY_SCORE
        )
        self.assertTrue(
            self._wait_for_host_score(
                self.second_host_executor,
                self.engine_vm_host,
                conf.GATEWAY_SCORE
            )
        )
        logger.info(
            "Wait until HE vm will migrate to host %s", self.second_host
        )
        self._is_vm_and_engine_run_on_second_host()

    @classmethod
    def teardown_class(cls):
        """
        Update gateway ip to correct one
        """
        cmd = [
            conf.COPY_CMD,
            conf.HOSTED_ENGINE_CONF_FILE_BACKUP,
            conf.HOSTED_ENGINE_CONF_FILE
        ]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)
        cmd = [
            "rm", "-f", conf.HOSTED_ENGINE_CONF_FILE_BACKUP,
            conf.HOSTED_ENGINE_CONF_FILE_TMP
        ]
        cls._get_output_from_run_cmd(cls.engine_vm_host_executor, cmd)
        cls.engine_vm_host.service(conf.AGENT_SERVICE).restart()
        super(TestHostGatewayProblem, cls).teardown_class()


class TestHostCpuLoadProblem(GeneralSetupTeardownClass):
    """
    Load host cpu, where HE vm is running and
    check if vm migrated to the second host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Load cpu on host, where HE vm runs
        """
        super(TestHostCpuLoadProblem, cls).setup_class()
        logger.info("Load host %s cpu up to 100 percent", cls.engine_vm_host)
        ll_sla.start_cpu_loading_on_resources([cls.engine_vm_host], 100)

    @tools.polarion("RHEVM3-5525")
    def test_check_host_score_and_he_vm_migration(self):
        """
        Check that host score dropped to 2400 and
        that vm migrated to second host as a result of difference in scores
        """
        logger.info(
            "Wait util host %s score will drop to %d",
            self.engine_vm_host, conf.CPU_LOAD_SCORE
        )
        self.assertTrue(
            self._wait_for_host_score(
                self.second_host_executor, self.engine_vm_host,
                conf.CPU_LOAD_SCORE, timeout=conf.CPU_SCORE_TIMEOUT
            )
        )
        logger.info(
            "Wait until HE vm will migrate to host %s", self.second_host
        )
        self._is_vm_and_engine_run_on_second_host(
            timeout=conf.CPU_SCORE_TIMEOUT
        )

    @classmethod
    def teardown_class(cls):
        """
        Release host cpu
        """
        logger.info("Release host %s cpu from loading", cls.engine_vm_host)
        ll_sla.stop_cpu_loading_on_resources([cls.engine_vm_host])
        if not cls._wait_for_host_score(
            cls.second_host_executor, cls.engine_vm_host,
            conf.MAX_SCORE, timeout=conf.CPU_SCORE_TIMEOUT
        ):
            logger.error(
                "Host %s still not have maximal score", cls.engine_vm_host
            )

#############################################################################
#                    Maintenance modes for HE environment                   #
#############################################################################


class TestGlobalMaintenance(GeneralSetupTeardownClass):
    """
    Enable global maintenance and kill HE vm
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Enable global maintenance
        """
        super(TestGlobalMaintenance, cls).setup_class()
        logger.info("Enable global maintenance")
        cls._set_maintenance_mode(
            cls.engine_vm_host_executor,
            cls.engine_vm_host,
            conf.MAINTENANCE_GLOBAL
        )

    @tools.polarion("RHEVM3-5516")
    def test_kill_vm_and_check_that_nothing_happen(self):
        """
        Kill HE vm and check that engine doesn't try to start vm on second host
        """
        logger.info("Kill HE vm on host %s", self.engine_vm_host)
        cmd = [conf.HOSTED_ENGINE_CMD, "--vm-poweroff"]
        self._get_output_from_run_cmd(self.engine_vm_host_executor, cmd)
        logger.info("Check if HE vm not start on host %s", self.second_host)
        self.assertFalse(
            self._wait_for_host_vm_state(
                executor=self.second_host_executor,
                host_resource=self.second_host,
                vm_state=conf.VM_STATE_UP
            )
        )

    @classmethod
    def teardown_class(cls):
        """
        Disable global maintenance and wait until HE VM runs on second host
        """
        logger.info("Disable global maintenance")
        cls._set_maintenance_mode(
            cls.engine_vm_host_executor,
            cls.engine_vm_host,
            conf.MAINTENANCE_NONE
        )
        logger.info(
            "Wait until one of hosts will have engine vm %s", conf.VM_STATE_UP
        )
        if not cls._wait_until_engine_vm_restarted():
            logger.error("HE vm still down")
        super(TestGlobalMaintenance, cls).teardown_class()


class TestLocalMaintenance(GeneralSetupTeardownClass):
    """
    Put host with HE vm to local maintenance,
    check if HE vm migrated to second host and
    host score dropped to zero.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Enable local maintenance
        """
        super(TestLocalMaintenance, cls).setup_class()
        logger.info("Enable local maintenance")
        cls._set_maintenance_mode(
            cls.engine_vm_host_executor,
            cls.engine_vm_host,
            conf.MAINTENANCE_LOCAL
        )

    @tools.polarion("RHEVM3-5517")
    def test_check_host_score_and_migration_of_vm(self):
        """
        Check if host under local maintenance have score 0 and
        that HE vm migrated to second host
        """
        logger.info("Check that host %s, have score 0", self.engine_vm_host)
        self.assertTrue(
            self._wait_for_host_score(
                self.second_host_executor, self.engine_vm_host, conf.ZERO_SCORE
            )
        )
        logger.info("Check if HE vm migrated on host %s", self.second_host)
        self._is_vm_and_engine_run_on_second_host()

    @classmethod
    def teardown_class(cls):
        """
        Disable local maintenance
        """
        logger.info("Disable local maintenance")
        cls._set_maintenance_mode(
            cls.engine_vm_host_executor,
            cls.engine_vm_host,
            conf.MAINTENANCE_NONE
        )
        super(TestLocalMaintenance, cls).teardown_class()


#############################################################################
#                       Stop agent, broker or vdsm services                 #
#############################################################################


class StopServices(GeneralSetupTeardownClass):
    """
    Stop HE services and check vm behaviour
    """
    __test__ = False
    stop_services = None
    start_services = None

    @classmethod
    def setup_class(cls):
        """
        Stop services on host with HE vm
        """
        super(StopServices, cls).setup_class()
        for service in cls.stop_services:
            service_executor = cls.engine_vm_host.service(service)
            if service == conf.VDSM_SERVICE:
                cls._mask_specific_service(service_executor)
            cls._stop_specific_service(service_executor)

    @classmethod
    def _stop_specific_service(cls, service_executor):
        """
        Stop specific service on host

        :param service_executor: service provider executor
        :type service_executor: Service
        """
        logger.info(
            "Stop service %s on host %s", service_executor, cls.engine_vm_host
        )
        service_executor.stop()

    @classmethod
    def _start_specific_service(cls, service_executor):
        """
        Start specific service on host

        :param service_executor: service provider executor
        :type service_executor: Service
        """
        logger.info(
            "Start service %s on host %s",
            service_executor, cls.engine_vm_host
        )
        service_executor.start()

    @classmethod
    def _mask_specific_service(cls, service_executor):
        """
        Stop specific service on host

        :param service_executor: service provider executor
        :type service_executor: Service
        """
        if service_executor.__class__.__name__ != conf.SYSTEMD:
            raise errors.SkipTest(
                "Can not mask service %s, because host %s do not have %s" %
                (service_executor, cls.engine_vm_host, conf.SYSTEMD)
            )
        logger.info(
            "Mask service %s on host %s", service_executor, cls.engine_vm_host
        )
        service_executor.mask()

    @classmethod
    def _unmask_specific_service(cls, service_executor):
        """
        Stop specific service on host

        :param service_executor: service provider executor
        :type service_executor: Service
        """
        if service_executor.__class__.__name__ != conf.SYSTEMD:
            logger.error(
                "Can not unmask service %s, because host %s do not have %s",
                service_executor, cls.engine_vm_host, conf.SYSTEMD
            )
        else:
            logger.info(
                "Unmask service %s on host %s",
                service_executor, cls.engine_vm_host
            )
            service_executor.unmask()

    @classmethod
    def teardown_class(cls):
        """
        Drop score to second host
        """
        for service in cls.start_services:
            service_executor = cls.engine_vm_host.service(service)
            if service == conf.VDSM_SERVICE:
                cls._unmask_specific_service(service_executor)
            if not service_executor.status():
                cls._start_specific_service(service_executor)
        super(StopServices, cls).teardown_class()


class TestStopBrokerService(StopServices):
    """
    Stop ovirt-ha-broker service on host with HE vm,
    and check that vm not migrate to second host
    """
    __test__ = True
    stop_services = [conf.BROKER_SERVICE]
    start_services = [conf.BROKER_SERVICE, conf.AGENT_SERVICE]

    @tools.polarion("RHEVM3-5521")
    def test_check_he_vm(self):
        """
        Check that HE vm not started on second host
        """
        self.assertTrue(
            self._check_he_vm_via_vdsClient(
                self.second_host,
                status=conf.VM_UP
            )
        )


class TestStopAgentService(StopServices):
    """
    Stop ovirt-ha-agent service on host with HE vm,
    and check that vm not migrate to second host
    """
    __test__ = True
    stop_services = [conf.AGENT_SERVICE]
    start_services = [conf.AGENT_SERVICE]

    @tools.polarion("RHEVM3-5523")
    def test_check_he_vm(self):
        """
        Check that HE vm not started on second host
        """
        self.assertTrue(
            self._check_he_vm_via_vdsClient(
                self.second_host,
                status=conf.VM_UP
            )
        )


class TestStopAgentAndBrokerServices(StopServices):
    """
    Stop ovirt-ha-broker and ovirt-ha-agent service on host with HE vm,
    and check that vm not migrate to second host
    """
    __test__ = True
    stop_services = [conf.AGENT_SERVICE, conf.BROKER_SERVICE]
    start_services = [conf.AGENT_SERVICE, conf.BROKER_SERVICE]

    @tools.polarion("RHEVM3-5522")
    def test_check_he_vm(self):
        """
        Check that HE vm not started on second host
        """
        self.assertTrue(
            self._check_he_vm_via_vdsClient(
                self.second_host,
                status=conf.VM_UP
            )
        )
