"""
Soft Fencing Test
Check different cases when host need to do soft fencing or hard fencing,
on host with pm and without,
"""

import logging
import pytest

from art.rhevm_api.tests_lib.low_level.hosts import (
    runDelayedControlService, waitForHostsStates, removeHost,
    add_host, isHostUp, activate_host, select_host_as_spm, waitForSPM
)
from art.rhevm_api.tests_lib.low_level.jobs import check_recent_job
from art.rhevm_api.tests_lib.low_level.vms import checkVmState
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, testflow, CoreSystemTest as TestCase
from rhevmtests.helpers import get_pm_details

from rhevmtests.system.soft_fencing import config

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
DISK_SIZE = 3 * 1024 * 1024 * 1024
ENUMS = opts['elements_conf']['RHEVM Enums']
PINNED = ENUMS['vm_affinity_pinned']
HOST_CONNECTING = ENUMS['host_state_connecting']
VM_DOWN = ENUMS['vm_state_down']
JOB = 'VdsNotRespondingTreatment'
sql = '%s FROM job WHERE action_type=\'VdsNotRespondingTreatment\''

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def module_setup(request):
    """
    Prepare environment for Soft Fencing tests
    """
    def fin():
        testflow.teardown(
            "Remove power management of host %s", config.host_with_pm
        )
        assert hl_hosts.remove_power_management(host_name=config.host_with_pm)
    request.addfinalizer(fin)

    config.host_with_pm = config.HOSTS[0]
    config.host_with_pm_num = 0
    config.host_without_pm = config.HOSTS[1]
    config.host_without_pm_num = 1
    hostname = config.VDS_HOSTS[0].fqdn
    testflow.setup("Get power management details of host %s", hostname)
    host_pm = get_pm_details(hostname).get(hostname)
    if not host_pm:
        pytest.skip("The host %s does not have power management" % hostname)
    agent = {
        "agent_type": host_pm.get("pm_type"),
        "agent_address": host_pm.get("pm_address"),
        "agent_username": host_pm.get("pm_username"),
        "agent_password": host_pm.get("pm_password"),
        "concurrent": False,
        "order": 1
    }
    testflow.setup("Add power management to host %s", config.host_with_pm)
    assert hl_hosts.add_power_management(
        host_name=config.host_with_pm, pm_agents=[agent]
    )


def _check_host_state(host_num, service, job_status):
    testflow.step(
        "Check if service %s on host %s is in state %s",
        service, config.HOSTS[host_num], job_status
    )
    testflow.step("Stop %s on host %s", service, config.HOSTS[host_num])
    assert runDelayedControlService(
            True, config.VDS_HOSTS[host_num].fqdn, config.HOSTS_USER,
            config.HOSTS_PW, service=service, command='stop'
    )
    testflow.step(
        "Check if %s job was invoked for host: %s",
        JOB, config.HOSTS[host_num]
    )
    if not waitForHostsStates(
            True, config.HOSTS[host_num], states=HOST_CONNECTING
    ):
        assert config.ENGINE.db.psql(sql, 'SELECT *')
    assert waitForHostsStates(True, config.HOSTS[host_num])
    testflow.step("Check recent jobs for job %s", config.job_description)
    assert check_recent_job(
        True, description=config.job_description, job_status=job_status
    ), "No job with given description"
    logger.info(
        "SSH soft fencing to host %s %s", config.HOSTS[host_num], job_status
    )


@attr(tier=2)
class SoftFencing(TestCase):
    """
    Soft fencing base class
    """
    __test__ = False

    @pytest.fixture(scope="class", autouse=True)
    def base_class_setup(self, request):
        def fin():
            testflow.teardown("Delete job %s from DB", JOB)
            if config.ENGINE.db.psql(sql, 'SELECT *'):
                config.ENGINE.db.psql(sql, 'DELETE')
            if config.ENGINE.db.psql(sql, 'SELECT *'):
                logger.info("Deleting job %s from DB failed", JOB)
        request.addfinalizer(fin)

        for host in config.host_with_pm, config.host_without_pm:
            if not isHostUp(True, host=host):
                testflow.setup("Activate host %s", host)
                assert activate_host(True, host=host)


class SoftFencingPassedWithoutPM(SoftFencing):
    """
    Positive: Soft fencing success on host without PM
    """
    __test__ = True

    @polarion("RHEVM3-8403")
    def test_check_host_state(self):
        """
        Check if engine does soft fencing to host when vdsm is stopped
        """
        _check_host_state(
            config.host_without_pm_num, config.service_vdsmd,
            config.job_finished
        )


@bz({'1423657': {}})
class SoftFencingFailedWithPM(SoftFencing):
    """
    Positive: After soft fencing failed, fence with power management
    """
    __test__ = True

    @polarion("RHEVM3-8402")
    def test_check_host_state(self):
        """
        There is no sshSoftFencing in the DB anymore, so just check
        if fencing operation succeeded
        """
        _check_host_state(
            config.host_with_pm_num, config.service_network,
            config.job_finished
        )


class SoftFencingPassedWithPM(SoftFencing):
    """
    Positive: Soft fencing success on host with PM
    """
    __test__ = True

    @polarion("RHEVM3-8407")
    def test_check_host_state(self):
        """
        Check if engine does soft fencing to host when vdsm is stopped
        """
        _check_host_state(
            config.host_with_pm_num, config.service_vdsmd, config.job_finished
        )


class CheckVmAfterSoftFencing(SoftFencing):
    """
    Positive: Check vm after soft fencing
    """
    __test__ = True

    vm_test = "vm_test"

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def class_setup(cls, request):
        def fin():
            testflow.teardown("Delete VM %s", cls.vm_test)
            assert vms.removeVms(True, cls.vm_test, stop='true')
        request.addfinalizer(fin)

        testflow.setup("Create VM %s", cls.vm_test)
        assert vms.createVm(
            positive=True, vmName=cls.vm_test, vmDescription="Test VM",
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=DISK_SIZE, nic='nic1',
            diskInterface=ENUMS['interface_virtio'],
            placement_host=config.host_with_pm, placement_affinity=PINNED,
            network=config.MGMT_BRIDGE
        )
        testflow.setup("Start VM %s", cls.vm_test)
        assert vms.startVm(positive=True, vm=cls.vm_test)

    @polarion("RHEVM3-8406")
    def test_check_vm_state(self):
        """
        Check that vm is up after soft fencing
        """
        _check_host_state(
            config.host_with_pm_num, config.service_vdsmd, config.job_finished
        )
        testflow.step("Check VM state")
        assert checkVmState(True, self.vm_test, ENUMS['vm_state_up'])


class SoftFencingToHostNoProxies(SoftFencing):
    """
    Positive: Soft fencing to host with power management without proxies
    """
    __test__ = True

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def class_setup(cls, request):
        """
        Remove another host in cluster
        """
        def fin():
            for host_num in 1, 2:
                testflow.teardown(
                    "Add host %s that was removed", config.HOSTS[host_num]
                )
                assert add_host(
                    name=config.HOSTS[host_num],
                    address=config.VDS_HOSTS[host_num].fqdn,
                    root_password=config.HOSTS_PW,
                    cluster=config.CLUSTER_NAME[0]
                )
                testflow.teardown("Wait for host %s", config.HOSTS[host_num])
                assert waitForHostsStates(True, config.HOSTS[host_num])
        request.addfinalizer(fin)

        select_host_as_spm(True, config.host_with_pm, config.DC_NAME[0])
        waitForSPM(
            config.DC_NAME[0], config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP
        )
        for host_num in 1, 2:
            testflow.setup("Remove host %s", config.HOSTS[host_num])
            assert removeHost(
                True, config.HOSTS[host_num], deactivate=True
            )

    @polarion("RHEVM3-8405")
    def test_check_soft_fencing_without_proxies(self):
        """
        Check that host do soft fencing with out proxies
        """
        _check_host_state(
            config.host_with_pm_num, config.service_vdsmd, config.job_finished
        )
