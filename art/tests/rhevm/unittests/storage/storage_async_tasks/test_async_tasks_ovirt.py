from art.unittest_lib import StorageTest as TestCase
import logging
import time

from concurrent.futures import ThreadPoolExecutor

from art.rhevm_api.utils import log_listener
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.tools import tcms
from nose.plugins.attrib import attr

import config
import common

LOGGER = logging.getLogger(__name__)
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
VDSM_LOG = '/var/log/vdsm/vdsm.log'
ALL_TASKS_FINISHED = 'Number of running tasks: 0'

OPERATION_FINISHED = False


@attr(tier=2)
class RestartOvirt(TestCase):
    __test__ = False
    ovirt_host = test_utils.Machine(
        config.VDC, 'root', config.VDC_PASSWORD).util('linux')

    def tearDown(self):
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def restart_before_tasks_start(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self.perform_action)
            executor.submit(
                test_utils.restartOvirtEngine, self.ovirt_host, 10, 30, 75)
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        LOGGER.info("checking if action failed")
        self.check_action_failed()

    def _wait_for_first_sent_and_restart_ovirt(self, action_name):
        global OPERATION_FINISHED
        OPERATION_FINISHED = False
        LOGGER.info("Waiting for the first task to be sent")
        regex = "Adding task .*Parent Command %s.*" % action_name
        cmd = ':'
        log_listener.watch_logs(
            ENGINE_LOG, regex, cmd, ip_for_files=config.VDC,
            username='root', password=config.VDC_PASSWORD)
        OPERATION_FINISHED = True
        test_utils.restartOvirtEngine(self.ovirt_host, 10, 30, 75)
        LOGGER.info("ovirt-engine restarted")

    def _timeouting_thread(self, operation, timeout=300):
        time.sleep(timeout)
        if not OPERATION_FINISHED:
            raise Exception(
                "Operation %s hasn't finished in %s seconds" % (
                    operation, timeout))

    def restart_during_tasks(self, action_name):
        operation_info = "'waiting for logs'"
        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.submit(self.perform_action)
            executor.submit(
                self._wait_for_first_sent_and_restart_ovirt, action_name)
            executor.submit(self._timeouting_thread, operation_info)

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        self.check_action_failed()

    def restart_after_finish_before_notified(self):
        self.perform_action()
        LOGGER.info("Waiting for function to finish")
        regex = ALL_TASKS_FINISHED
        cmd = ':'
        log_listener.watch_logs(
            VDSM_LOG, regex, cmd, ip_for_files=config.HOSTS[0],
            username='root', password=config.PASSWORDS[0], time_out=300)
        test_utils.restartOvirtEngine(self.ovirt_host, 10, 30, 75)
        LOGGER.info("ovirt-engine restarted")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        self.check_action_failed()


class TestCase288728(RestartOvirt):
    """
    Restart ovirt-engine during creation of a snapshot

    https://tcms.engineering.redhat.com/case/288728/?from_plan=10029
    """
    __test__ = True
    tcms_plan_id = '10029'
    tcms_test_case = '288728'
    snapshot_name = "snap_%s" % tcms_test_case

    def tearDown(self):
        super(TestCase288728, self).tearDown()
        if vms.validateSnapshot(True, config.VM_NAME, self.snapshot_name):
            vms.stopVm(True, config.VM_NAME)
            self.assertTrue(
                vms.removeSnapshot(True, config.VM_NAME, self.snapshot_name),
                "Removing snapshot %s failed" % self.snapshot_name)
            vms.startVm(True, config.VM_NAME, config.ENUMS['vm_state_up'])
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def perform_action(self):
        self.assertTrue(
            vms.addSnapshot(True, config.VM_NAME, self.snapshot_name, False),
            "Adding snapshot %s failed" % self.snapshot_name)

    def check_action_failed(self):
        self.assertFalse(
            vms.validateSnapshot(True, config.VM_NAME, self.snapshot_name),
            "Snapshot %s exists!" % self.snapshot_name)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_before_tasks_start(self):
        """
        Restart ovirt engine before it gets info about tasks from UI
        - snapshot creation
        """
        self.restart_before_tasks_start()

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_during_tasks(self):
        """
        Restart ovirt engine when only part of the tasks were sent
        - snapshot creation
        """
        self.restart_during_tasks('CreateAllSnapshotsFromVm')

# commented out as it is failing
#    @tcms(tcms_plan_id, tcms_test_case)
#    def test_restart_after_finish_before_notified(self):
#        """
#        Restart ovirt engine when tasks were finished but engine weren't
#        notified - snapshot creation
#        """
#        self.restart_after_finish_before_notified()


class TestCase288964(RestartOvirt):
    """
    Restart ovirt-engine during hibernate a VM

    https://tcms.engineering.redhat.com/case/288964/?from_plan=10029
    """
    __test__ = True
    tcms_plan_id = '10029'
    tcms_test_case = '288964'

    def setUp(self):
        common.start_vm()

    def tearDown(self):
        super(TestCase288964, self).tearDown()
        common.start_vm()
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def perform_action(self):
        assert vms.suspendVm(True, config.VM_NAME, False)

    def check_action_failed(self):
        vms.wait_for_vm_states(
            config.VM_NAME,
            [config.ENUMS['vm_state_up'], config.ENUMS['vm_state_down'],
             config.ENUMS['vm_state_suspended']])
        status = vms.VM_API.find(config.VM_NAME).get_status().get_state()
        self.assertEqual(
            status, config.ENUMS['vm_state_up'],
            "VM %s status incorrect, is: %s, should be: %s" % (
                config.VM_NAME, status, config.ENUMS['vm_state_up']))

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_before_tasks_start(self):
        """ r
        Restart ovirt engine before it gets info about tasks from UI
        - pausing vm
        """
        self.restart_before_tasks_start()

# commented out as it is failing
#    @tcms(tcms_plan_id, tcms_test_case)
#    def test_restart_during_tasks(self):
#        """ restart ovirt engine when only part of the tasks were sent
#            - pausing vm
#        """
#        self.restart_during_tasks('HibernateVm')

# commented out as it is failing
#    @tcms(tcms_plan_id, tcms_test_case)
#    def test_restart_after_finish_before_notified(self):
#        """ restart ovirt engine when tasks were finished
#            but engine weren't notified - pausing vm
#        """
#        self.restart_after_finish_before_notified()


class TestCase288972(RestartOvirt):
    """
    Restart ovirt-engine during cloning a VM from a template

    https://tcms.engineering.redhat.com/case/288972/?from_plan=10029
    """
    __test__ = True
    tcms_plan_id = '10029'
    tcms_test_case = '288972'
    cloned_vm = "vm_%s" % tcms_test_case

    def tearDown(self):
        """
        Just in case: if one of the tests failed and vm was created - remove it
        """
        super(TestCase288972, self).tearDown()
        if vms.VM_API.query("name=%s" % self.cloned_vm):
            vms.removeVm(True, self.cloned_vm)
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def check_action_failed(self):
        assert vms.waitForVmsGone(True, self.cloned_vm, 600)

    def perform_action(self):
        return vms.cloneVmFromTemplate(
            True, self.cloned_vm, config.TEMPLATE_NAME, config.CLUSTER_NAME,
            wait=False)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_before_tasks_start(self):
        """
        Restart ovirt engine before it gets info about tasks from UI
        - cloning vm from template
        """
        self.restart_before_tasks_start()

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_during_tasks(self):
        """
        Restart ovirt engine when only part of the tasks were sent
        - cloning vm from template
        """
        self.restart_during_tasks('AddVmFromTemplate')

# commented out as it is failing
#    @tcms(tcms_plan_id, tcms_test_case)
#    def test_restart_after_finish_before_notified(self):
#        """ restart ovirt engine when tasks were finished
#            but engine weren't notified - cloning vm from template
#        """
#        self.restart_after_finish_before_notified()
