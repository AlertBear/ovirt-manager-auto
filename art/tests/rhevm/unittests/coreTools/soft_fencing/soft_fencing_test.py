"""
Soft Fencing Test
Check different cases when host need to do soft fencing or hard fencing,
on host with pm and without,
"""

from art.rhevm_api.tests_lib.low_level.hosts import \
    runDelayedControlService, waitForHostsStates,\
    deactivateHost, removeHost, addHost
from art.rhevm_api.tests_lib.low_level.jobs import check_recent_job
from art.rhevm_api.tests_lib.low_level.vms import checkVmState
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from unittest import TestCase
from nose.tools import istest
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.test_handler.exceptions as errors
import config
import logging
import datetime


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
DISK_SIZE = 3 * 1024 * 1024 * 1024
ENUMS = opts['elements_conf']['RHEVM Enums']
PINNED = ENUMS['vm_affinity_pinned']
HOST_CONNECTING = ENUMS['host_state_connecting']
VM_DOWN = ENUMS['vm_state_down']


logger = logging.getLogger(__package__ + __name__)

########################################################################
#                             Test Cases                               #
########################################################################


class SoftFencing(TestCase):

    __test__ = False

    def _check_host_state(self, host, service, job_status):
        ts = datetime.datetime.now()
        logger.info("Stop %s to host %s", service, host)
        if not runDelayedControlService(True, host, config.host_user,
                                        config.host_password,
                                        service=service, command='stop'):#STOPS SERVICE e.g vdsmd ON HOST
            raise errors.HostException("Trying to stop %s "
                                       "on host %s failed", service, host)
        logger.info("Check if host %s in connecting state", host)
        if not waitForHostsStates(True, host, states=HOST_CONNECTING):#checks if host in state connecting
            raise errors.HostException("Host %s not in connecting state",
                                       host)
        if not waitForHostsStates(True, host):#checks if host in state up
            raise errors.HostException("Host %s not in up state", host)
        status, job, job_time = check_recent_job(True,
                                                 description=config.
                                                 job_description,
                                                 job_status=job_status)#check if ssh soft fencing job was created and return the last job
        if not status:
            raise errors.JobException("No job with given description")
        self.assertTrue(job_time[0] >= ts.hour
                        and job_time[1] >= ts.minute
                        and job_time[2] >= ts.second)
        logger.info("Ssh soft fencing to host %s %s", host, job_status)


class SoftFencingPassedWithoutPM(SoftFencing):
    """
    Positive: Soft fencing success on host without PM
    """
    __test__ = True

    @tcms('9867', '289205')
    @istest
    def check_host_state(self):
        """
        Check if engine do soft fencing to host with stopped vdsm
        """
        self._check_host_state(config.host_without_pm, 'vdsmd', 'finished')


class SoftFencingFailedWithPM(SoftFencing):
    """
    Positive: After soft fencing via ssh failed, do fence via pm
    """

    __test__ = True

    @tcms('9867', '285811')
    @istest
    def check_host_state(self):
        """
        Check if job sshSoftFencing appear after timestamp,
        and job status FAILED
        """
        self._check_host_state(config.host_with_pm, 'network', 'failed')


class SoftFencingPassedWithPM(SoftFencing):
    """
    Positive: Soft fencing success on host with PM
    """

    __test__ = True

    @tcms('9867', '285782')
    @istest
    def check_host_state(self):
        """
        Check if engine do soft fencing to host with stopped vdsm
        """
        self._check_host_state(config.host_with_pm, 'vdsmd', 'finished')


class CheckVmAfterSoftFencing(TestCase):
    """
    Positive: Check vm after soft fencing
    """

    __test__ = True

    vm_test = "vm_test"

    @classmethod
    def setup_class(cls):
        '''
        Add vm to host
        '''
        logger.info("Create new vm")
        if not vms.createVm(positive=True, vmName=cls.vm_test,
                            vmDescription="Test VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
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

    @tcms('9867', '295256')
    @istest
    def check_vm_state(self):
        """
        Check that after soft fencing vm up
        """
        ts = datetime.datetime.now()
        logger.info("Stop vdsm to host %s", config.host_with_pm)
        if not runDelayedControlService(True, config.host_with_pm,
                                        config.host_user,
                                        config.host_password,
                                        service='vdsmd',
                                        command='stop'):
            raise errors.HostException("Trying to stop vdsm on host %s failed"
                                       % config.host_with_pm)
        logger.info("Check if host %s in connecting state",
                    config.host_with_pm)
        if not waitForHostsStates(True, config.host_with_pm,
                                  states=HOST_CONNECTING):
            raise errors.HostException("Host %s not in connecting state"
                                       % config.host_with_pm)
        if not waitForHostsStates(True, config.host_with_pm):
            raise errors.HostException("Host %s not in up state"
                                       % config.host_with_pm)
        status, job, job_time = check_recent_job(True,
                                                 description=config.
                                                 job_description,
                                                 job_status='finished')
        if not (status and
                job_time[0] >= ts.hour and
                job_time[1] >= ts.minute and
                job_time[2] >= ts.second):
            raise errors.JobException("No job with given "
                                       "description in recent time")
        logger.info("Check VM state")
        self.assertTrue(checkVmState(True, self.vm_test,
                                     ENUMS['vm_state_up']))
        logger.info("Vm state up")


class SoftFencingToHostNoProxies(SoftFencing):
    """
    Positive: Soft fencing to host with power management without proxies
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Remove another host in cluster
        '''
        logger.info("Put another host in cluster to maintenance")
        if not deactivateHost(True, config.host_without_pm):
            raise errors.HostException("Attempt to put host %s"
                                       " to maintenance state failed"
                                       % config.host_without_pm)
        logger.info("Attempt to remove host")
        if not removeHost(True, config.host_without_pm):
            raise errors.HostException("Attempt to remove host %s failed"
                                       % config.host_without_pm)

    @tcms('9867', '289208')
    @istest
    def check_soft_fencing_without_proxies(self):
        """
        Check that host do soft fencing with out proxies
        """
        self._check_host_state(config.host_with_pm, 'vdsmd', 'finished')

    @classmethod
    def teardown_class(cls):
        logger.info("Add host that was removed")
        if not addHost(True, config.host_without_pm,
                       root_password=config.host_password,
                       cluster=config.cluster_name):
            raise errors.HostException("Add host %s was failed"
                                       % config.host_without_pm)
        logger.info("Wait for host %s", config.host_without_pm)
        if not waitForHostsStates(True, config.host_with_pm):
            raise errors.HostException("Host %s not in up state"
                                       % config.host_without_pm)
        logger.info("Host %s Up", config.host_without_pm)
