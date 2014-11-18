"""
Hosted Engine - HA Test
Check behaviour of ovirt-ha-agent under different conditions
"""
import socket
import logging

import config as conf
import art.unittest_lib as test_libs
import art.core_api.apis_utils as utils
import art.test_handler.exceptions as errors
import art.core_api.apis_exceptions as core_errors

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
    def _get_out_from_run_cmd(cls, executor, cmd, negative=False):
        """
        Run command on host

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
        status_dict = eval(cls._get_out_from_run_cmd(executor, cmd))
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
        :rtype: str
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
        cls._get_out_from_run_cmd(executor, cmd)

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
        out = cls._get_out_from_run_cmd(
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
        to drop host score to maximal value(2400)

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
        out = cls._get_out_from_run_cmd(executor, cmd)
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
            logger.info("Check if host is %s up to date", host_resource)
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
        Check if vm restarted

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
        Check if engine down

        :return: True, if engine down, otherwise False
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
        Wait until engine down

        :return: True, if engine down, otherwise False
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
        out = cls._get_out_from_run_cmd(host.executor(), cmd)
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
