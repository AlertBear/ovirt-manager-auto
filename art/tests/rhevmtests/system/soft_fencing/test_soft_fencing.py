"""
Soft Fencing Test
Check different cases when host need to do soft fencing or hard fencing,
on host with pm and without,
"""

from art.rhevm_api.tests_lib.low_level.hosts import \
    runDelayedControlService, waitForHostsStates,\
    deactivateHost, removeHost, addHost, isHostUp, activateHost
from art.rhevm_api.tests_lib.low_level.jobs import check_recent_job
from art.rhevm_api.tests_lib.low_level.vms import checkVmState
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import CoreSystemTest as TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level import vms
from art.unittest_lib import attr
import art.test_handler.exceptions as errors
from rhevmtests.system.soft_fencing import config
import logging

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
DISK_SIZE = 3 * 1024 * 1024 * 1024
ENUMS = opts['elements_conf']['RHEVM Enums']
PINNED = ENUMS['vm_affinity_pinned']
HOST_CONNECTING = ENUMS['host_state_connecting']
VM_DOWN = ENUMS['vm_state_down']
JOB = 'SshSoftFencing'
sql = '%s FROM job WHERE action_type=\'SshSoftFencing\''
PM_TYPE = config.PM_TYPE_IPMILAN

logger = logging.getLogger(__name__)

########################################################################
#                             Test Cases                               #
########################################################################


def _check_host_state(host, service, job_status):
    logger.info("Stop %s on host %s", service, host)
    if not runDelayedControlService(True, host, config.HOSTS_USER,
                                    config.HOSTS_PW,
                                    service=service, command='stop'):
        raise errors.HostException("Trying to stop %s "
                                   "on host %s failed" % (service, host))
    logger.info("Check if %s job was invoked for host: %s", JOB, host)
    if not waitForHostsStates(True, host, states=HOST_CONNECTING):
        if not config.ENGINE.db.psql(sql, 'SELECT *'):
            raise errors.HostException("%s job failed to start on host: %s"
                                       % (JOB, host))
    if not waitForHostsStates(True, host):
        raise errors.HostException("Host %s is not in up state" % host)
    status = check_recent_job(True, description=config.job_description,
                              job_status=job_status)
    if not status:
        raise errors.JobException("No job with given description")
    logger.info("Ssh soft fencing to host %s %s", host, job_status)


def _delete_job_from_db():
    if config.ENGINE.db.psql(sql, 'SELECT *'):
        config.ENGINE.db.psql(sql, 'DELETE')
    if config.ENGINE.db.psql(sql, 'SELECT *'):
        logger.info("Deleting %s job from db failed", JOB)


def _activate_both_hosts():
    for host in config.host_with_pm, config.host_without_pm:
        if not isHostUp(True, host=host):
            if not activateHost(True, host=host):
                raise errors.HostException("cannot activate host: %s" % host)


@attr(tier=2, extra_reqs={'pm': PM_TYPE})
class SoftFencing(TestCase):

    __test__ = False

    @classmethod
    def setup_class(cls):
        _activate_both_hosts()

    @classmethod
    def teardown_class(cls):
        _delete_job_from_db()


class SoftFencingPassedWithoutPM(SoftFencing):
    """
    Positive: Soft fencing success on host without PM
    """
    __test__ = True

    @polarion("RHEVM3-8403")
    @istest
    def check_host_state(self):
        """
        Check if engine does soft fencing to host when vdsm is stopped
        """
        _check_host_state(config.host_without_pm, config.service_vdsmd,
                          config.job_finished)


class SoftFencingFailedWithPM(SoftFencing):
    """
    Positive: After soft fencing failed, fence with power management
    """

    __test__ = True

    @polarion("RHEVM3-8402")
    @istest
    def check_host_state(self):
        """
        Check if job sshSoftFencing appear after timestamp,
        and job status FAILED
        """
        _check_host_state(config.host_with_pm, config.service_network,
                          config.job_failed)


class SoftFencingPassedWithPM(SoftFencing):
    """
    Positive: Soft fencing success on host with PM
    """

    __test__ = True

    @polarion("RHEVM3-8407")
    @istest
    def check_host_state(self):
        """
        Check if engine does soft fencing to host when vdsm is stopped
        """
        _check_host_state(config.host_with_pm, config.service_vdsmd,
                          config.job_finished)


class CheckVmAfterSoftFencing(SoftFencing):
    """
    Positive: Check vm after soft fencing
    """

    __test__ = True

    vm_test = "vm_test"

    @classmethod
    def setup_class(cls):
        super(CheckVmAfterSoftFencing, cls).setup_class()
        logger.info("Create new vm")
        if not vms.createVm(positive=True, vmName=cls.vm_test,
                            vmDescription="Test VM",
                            cluster=config.CLUSTER_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            size=DISK_SIZE, nic='nic1',
                            diskInterface=ENUMS['interface_virtio'],
                            placement_host=config.host_with_pm,
                            placement_affinity=PINNED,
                            network=config.MGMT_BRIDGE):
            raise errors.VMException("Cannot create vm")
        logger.info("Successfully created a simple VM.")
        logger.info("Start Vm")
        if not vms.startVm(positive=True, vm=cls.vm_test):
            raise errors.VMException("VM failed change state to UP")
        logger.info("Vm started")

    @polarion("RHEVM3-8406")
    @istest
    def check_vm_state(self):
        """
        Check that vm is up after soft fencing
        """
        _check_host_state(config.host_with_pm, config.service_vdsmd,
                          config.job_finished)
        logger.info("Check VM state")
        self.assertTrue(checkVmState(True, self.vm_test,
                                     ENUMS['vm_state_up']))
        logger.info("Vm state up")

    @classmethod
    def teardown_class(cls):
        super(CheckVmAfterSoftFencing, cls).teardown_class()
        logger.info("Deleting vm: %s", cls.vm_test)
        if not vms.removeVms(True, cls.vm_test, stop='true'):
            raise errors.VMException("cannot remove vm: %s" % cls.vm_test)


class SoftFencingToHostNoProxies(SoftFencing):
    """
    Positive: Soft fencing to host with power management without proxies
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Remove another host in cluster
        """
        super(SoftFencingToHostNoProxies, cls).setup_class()
        logger.info("Put another host in cluster to maintenance")
        if not deactivateHost(True, config.host_without_pm):
            raise errors.HostException("Attempt to put host %s"
                                       " to maintenance state failed"
                                       % config.host_without_pm)
        logger.info("Attempt to remove host")
        if not removeHost(True, config.host_without_pm):
            raise errors.HostException("Attempt to remove host %s failed"
                                       % config.host_without_pm)

    @polarion("RHEVM3-8405")
    @istest
    def check_soft_fencing_without_proxies(self):
        """
        Check that host do soft fencing with out proxies
        """
        _check_host_state(config.host_with_pm, config.service_vdsmd,
                          config.job_finished)

    @classmethod
    def teardown_class(cls):
        super(SoftFencingToHostNoProxies, cls).teardown_class()
        logger.info("Add host that was removed")
        if not addHost(True, config.host_without_pm,
                       root_password=config.HOSTS_PW,
                       cluster=config.CLUSTER_NAME[0]):
            raise errors.HostException("Add host %s was failed"
                                       % config.host_without_pm)
        logger.info("Wait for host %s", config.host_without_pm)
        if not waitForHostsStates(True, config.host_with_pm):
            raise errors.HostException("Host %s not in up state"
                                       % config.host_without_pm)
        logger.info("Host %s Up", config.host_without_pm)
