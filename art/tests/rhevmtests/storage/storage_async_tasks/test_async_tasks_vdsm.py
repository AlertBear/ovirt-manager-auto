from art.unittest_lib import StorageTest as TestCase
import logging
import time
from threading import Thread
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from nose.plugins.attrib import attr

import config
import common

from art.rhevm_api.tests_lib.low_level.vms import (
    validateSnapshot, removeSnapshot,
    addSnapshot, startVm, stop_vms_safely, waitForVMState, waitForVmsGone,
    cloneVmFromTemplate, removeVm, VM_API,
)

from art.rhevm_api.tests_lib.low_level.vms import (
    suspendVm, wait_for_vm_states, get_vm_state,
)

from art.rhevm_api.utils.test_utils import wait_for_tasks, restartVdsmd
from art.rhevm_api.tests_lib.low_level.datacenters import (
    wait_for_datacenter_state_api,
)

LOGGER = logging.getLogger(__name__)
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
SPM_TIMEOUT = 1200
TIMEOUT = 300
DATA_CENTER_INIT_TIMEOUT = 1200


@attr(tier=3)
class RestartVDSM(TestCase):
    __test__ = False

    def tearDown(self):
        wait_for_datacenter_state_api(config.DATA_CENTER_NAME,
                                      timeout=DATA_CENTER_INIT_TIMEOUT)
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def restart_before_tasks_start(self):
        self.perform_action()
        LOGGER.info("Restarting VDSM")
        assert restartVdsmd(
            config.HOSTS[0], config.HOSTS_PW)
        LOGGER.info("VDSM restarted")

        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        wait_for_datacenter_state_api(config.DATA_CENTER_NAME,
                                      timeout=DATA_CENTER_INIT_TIMEOUT)
        self.check_action_failed()

    def restart_during_tasks(self, action_name):
        """
        We are waiting for the first task to finish and then restart VDSM
        """
        LOGGER.info("Waiting for the first task to finish")
        regex = 'Parent Command %s.*ended successfully' % action_name
        cmd = 'service vdsmd restart'

        t = Thread(target=log_listener.watch_logs, args=(
            ENGINE_LOG, regex, cmd, TIMEOUT, config.VDC,
            config.VDC_ROOT_USER, config.VDC_PASSWORD,
            config.HOSTS[0], config.HOSTS_USER, config.HOSTS_PW)
        )
        t.start()

        time.sleep(5)

        self.perform_action()

        LOGGER.info("VDSM restarted")

        t.join()
        wait_for_datacenter_state_api(config.DATA_CENTER_NAME,
                                      timeout=DATA_CENTER_INIT_TIMEOUT)
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        self.check_action_failed()

    def check_action_failed(self):
        pass

    def perform_action(self):
        pass


class TestCase287892(RestartVDSM):
    """
    Restart VDSM during creation of a snapshot

    https://tcms.engineering.redhat.com/case/287892/?from_plan=10029
    """
    __test__ = True
    tcms_plan_id = '10029'
    tcms_test_case = '287892'
    snapshot_name = 'snapshot_%s' % tcms_test_case

    def tearDown(self):
        super(TestCase287892, self).tearDown()
        if validateSnapshot(True, config.VM_NAME[0], self.snapshot_name):
            LOGGER.info("Stopping vm %s", config.VM_NAME[0])
            stop_vms_safely([config.VM_NAME[0]])
            waitForVMState(config.VM_NAME[0], config.VM_DOWN)

            LOGGER.info("Removing snapshot %s", self.snapshot_name)
            self.assertTrue(
                removeSnapshot(True, config.VM_NAME[0], self.snapshot_name),
                "Removing snapshot %s failed" % self.snapshot_name)

            LOGGER.info("Starting vm %s", config.VM_NAME[0])
            startVm(True, config.VM_NAME[0], config.VM_UP)

        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        wait_for_datacenter_state_api(config.DATA_CENTER_NAME,
                                      timeout=DATA_CENTER_INIT_TIMEOUT)

    def perform_action(self):
        addSnapshot(True, config.VM_NAME[0], self.snapshot_name, False)

    def check_action_failed(self):
        self.assertTrue(
            validateSnapshot(True, config.VM_NAME[0], self.snapshot_name),
            "Snapshot %s doesn't exists!" % self.snapshot_name)

    @tcms(tcms_plan_id, tcms_test_case)
    @bz({'1069610': {'engine': ['rest', 'sdk'], 'version': ['3.5']}})
    def test_restart_before_tasks_start(self):
        """
        Restart VDSM before tasks were sent to it - snapshot creation
        """
        stop_vms_safely([config.VM_NAME[0]])
        waitForVMState(config.VM_NAME[0], config.VM_DOWN)

        self.restart_before_tasks_start()

    # TODO: Commented out due to:
    #    https://projects.engineering.redhat.com/browse/RHEVM-1940
    #
    # @tcms(tcms_plan_id, tcms_test_case)
    # def test_restart_during_tasks(self):
    #     """
    #     Restart VDSM when only part of the tasks were finished
    #     - snapshot creation
    #     """
    #     stop_vms_safely([config.VM_NAME[0]])
    #     waitForVMState(config.VM_NAME[0], config.VM_DOWN)
    #
    #     self.restart_during_tasks('CreateAllSnapshotsFromVm')


class TestCase287893(RestartVDSM):
    """
    Restart VDSM during cloning VM from a template

    https://tcms.engineering.redhat.com/case/287893/?from_plan=10029
    """
    __test__ = True
    tcms_plan_id = '10029'
    tcms_test_case = '287893'
    cloned_vm = 'vm_%s' % tcms_test_case

    def check_action_failed(self):
        assert waitForVmsGone(True, self.cloned_vm, 600)

    def perform_action(self):
        return cloneVmFromTemplate(
            True, self.cloned_vm, config.TEMPLATE_NAME, config.CLUSTER_NAME,
            wait=False)

    def tearDown(self):
        """
        Just in case: if one of the tests failed and vm was created - remove it
        """
        super(TestCase287893, self).tearDown()
        if VM_API.query("name=%s" % self.cloned_vm):
            removeVm(True, self.cloned_vm)
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_before_tasks_start(self):
        """
        Restart VDSM before tasks were sent to it - cloning vm from template
        """
        self.restart_before_tasks_start()

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_during_tasks(self):
        """
        Restart VDSM when only part of the tasks were finished
        - cloning vm from template
        """
        self.restart_during_tasks('AddVmFromTemplate')


class TestCase288203(RestartVDSM):
    """
    Restart VDSM during hibernate a VM

    https://tcms.engineering.redhat.com/case/288203/?from_plan=10029
    """
    __test__ = True
    tcms_plan_id = '10029'
    tcms_test_case = '288203'

    def perform_action(self):
        assert suspendVm(True, config.VM_NAME[0], False)

    def check_action_failed(self):
        wait_for_vm_states(
            config.VM_NAME[0],
            [config.VM_UP, config.VM_DOWN, config.VM_SUSPENDED])
        status = get_vm_state(config.VM_NAME[0])

        self.assertEqual(status, config.VM_UP,
                         "VM %s status incorrect, is: %s, should be: %s" %
                         (config.VM_NAME[0], status, config.VM_UP))

    def setUp(self):
        common.start_vm()

    def tearDown(self):
        super(TestCase288203, self).tearDown()
        common.start_vm()
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

# commented out as it is failing
#    @tcms(tcms_plan_id, tcms_test_case)
#    def test_restart_before_tasks_start(self):
#        """ restart VDSM before tasks were sent to it - pausing vm
#        """
#        self.restart_before_tasks_start()

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_during_tasks(self):
        """
        Restart VDSM when only part of the tasks were finished - pausing vm
        """
        self.restart_during_tasks('HibernateVm')
