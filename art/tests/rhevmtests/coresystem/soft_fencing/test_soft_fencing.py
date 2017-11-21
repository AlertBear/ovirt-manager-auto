"""
Soft Fencing Test
Check different cases when host need to do soft fencing or hard fencing,
on host with pm and without,
"""

import logging
import pytest
from socket import timeout

from art.rhevm_api.tests_lib.low_level.hosts import (
    wait_for_hosts_states, remove_host, add_host, is_host_up,
    activate_host, select_host_as_spm, wait_for_spm, fence_host
)
from art.rhevm_api.tests_lib.low_level.jobs import (
    check_recent_job, wait_for_jobs
)
from art.rhevm_api.tests_lib.low_level.vms import waitForVMState
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.utils.test_utils import get_api, wait_for_tasks
from art.test_handler.tools import polarion, bz
from art.unittest_lib import tier2
from art.unittest_lib import testflow, CoreSystemTest as TestCase
from rhevmtests.helpers import get_pm_details

from rhevmtests.coresystem.soft_fencing import config

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
DISK_SIZE = 3 * 1024 * 1024 * 1024
PINNED = config.ENUMS['vm_affinity_pinned']
VM_DOWN = config.ENUMS['vm_state_down']
JOB = 'VdsNotRespondingTreatment'
sql = '%s FROM job WHERE action_type=\'VdsNotRespondingTreatment\''

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def module_setup(request):
    """
    Prepare environment for Soft Fencing tests
    """
    def fin():
        testflow.teardown("Check if host %s is up", config.host_with_pm)
        if not is_host_up(True, config.host_with_pm):
            testflow.teardown("Fence host %s to clean up", config.host_with_pm)
            fence_host(
                host=config.host_with_pm,
                fence_type=config.ENUMS['fence_type_restart']
            )
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
    try:
        config.VDS_HOSTS[host_num].service(service).stop()
    except timeout as err:
        logger.info(err)

    testflow.step(
        "Check if %s job was invoked for host: %s",
        JOB, config.HOSTS[host_num]
    )
    if not wait_for_hosts_states(
            True, config.HOSTS[host_num],
            states=[
                config.HOST_CONNECTING,
                config.HOST_NONRESPONSIVE
            ]
    ):
        assert config.ENGINE.db.psql(sql, 'SELECT *')
    wait_for_hosts_states(True, config.HOSTS[host_num])
    wait_for_jobs()

    testflow.step("Check recent jobs for job %s", config.job_description)
    assert check_recent_job(
        description=config.job_description, job_status=job_status
    ), "No job with given description"
    logger.info(
        "SSH soft fencing to host %s %s", config.HOSTS[host_num], job_status
    )


@tier2
@bz({"1508023": {}})
class SoftFencing(TestCase):
    """
    Soft fencing base class
    """
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
            if not is_host_up(True, host=host):
                testflow.setup("Activate host %s", host)
                assert activate_host(True, host=host)


class TestSoftFencingPassedWithoutPM(SoftFencing):
    """
    Positive: Soft fencing success on host without PM
    """
    @polarion("RHEVM3-8403")
    def test_check_host_state(self):
        """
        Check if engine does soft fencing to host when vdsm is stopped
        """
        _check_host_state(
            config.host_without_pm_num, config.service_vdsmd,
            config.job_finished
        )


class TestSoftFencingFailedWithPM(SoftFencing):
    """
    Positive: After soft fencing failed, fence with power management
    """
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


class TestSoftFencingPassedWithPM(SoftFencing):
    """
    Positive: Soft fencing success on host with PM
    """
    @polarion("RHEVM3-8407")
    def test_check_host_state(self):
        """
        Check if engine does soft fencing to host when vdsm is stopped
        """
        _check_host_state(
            config.host_with_pm_num, config.service_vdsmd, config.job_finished
        )


class TestCheckVmAfterSoftFencing(SoftFencing):
    """
    Positive: Check vm after soft fencing
    """
    vm_test = "sf_test_vm"

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def class_setup(cls, request):
        def fin():
            testflow.teardown("Delete VM %s", cls.vm_test)
            assert vms.removeVm(True, cls.vm_test, stopVM='true')
        request.addfinalizer(fin)

        testflow.setup("Create VM %s", cls.vm_test)
        assert vms.createVm(
            positive=True, vmName=cls.vm_test, vmDescription="Test VM",
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=DISK_SIZE, nic='nic1',
            diskInterface=config.ENUMS['interface_virtio'],
            placement_host=config.host_with_pm, placement_affinity=PINNED,
            network=config.MGMT_BRIDGE
        )
        testflow.setup("Start VM %s", cls.vm_test)
        assert vms.startVm(
            positive=True, vm=cls.vm_test, wait_for_status=config.VM_UP
        )

    @polarion("RHEVM3-8406")
    def test_check_vm_state(self):
        """
        Check that vm is up after soft fencing
        """
        _check_host_state(
            config.host_with_pm_num, config.service_vdsmd, config.job_finished
        )
        testflow.step("Check VM state")
        assert waitForVMState(self.vm_test)


class TestSoftFencingToHostNoProxies(SoftFencing):
    """
    Positive: Soft fencing to host with power management without proxies
    """
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
                    cluster=config.CLUSTER_NAME[0],
                    comment=config.VDS_HOSTS[host_num].ip
                )
                testflow.teardown("Wait for host %s", config.HOSTS[host_num])
                assert wait_for_hosts_states(True, config.HOSTS[host_num])
        request.addfinalizer(fin)

        wait_for_tasks(config.ENGINE, config.DC_NAME[0])
        select_host_as_spm(True, config.host_with_pm, config.DC_NAME[0])
        wait_for_spm(
            config.DC_NAME[0], config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP
        )
        for host_num in 1, 2:
            testflow.setup("Remove host %s", config.HOSTS[host_num])
            assert remove_host(
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
