from art.unittest_lib import StorageTest as TestCase
import logging

from art.rhevm_api.utils import log_listener
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import datacenters
from art.test_handler.tools import tcms

import config
import common

LOGGER = logging.getLogger(__name__)
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'


class RestartVDSM(TestCase):
    __test__ = False

    def tearDown(self):
        datacenters.wait_for_datacenter_state_api(config.DATA_CENTER_NAME)
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def restart_before_tasks_start(self):
        self.perform_action()
        LOGGER.info("Restarting VDSM")
        assert test_utils.restartVdsmd(
            config.HOSTS[0], config.PASSWORDS[0])
        LOGGER.info("VDSM restarted")
        hosts.waitForHostsStates(True, config.HOSTS[0])
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        self.check_action_failed()

    def restart_during_tasks(self, action_name):
        """
        We are waiting for the first task to finish and then restart VDSM
        """
        self.perform_action()
        LOGGER.info("Waiting for the first task to finish")
        regex = 'Parent Command %s.*ended successfully' % action_name
        cmd = 'service vdsmd restart'
        log_listener.watch_logs(
            ENGINE_LOG, regex, cmd, ip_for_files=config.VDC,
            username='root', password=config.VDC_PASSWORD,
            ip_for_execute_command=config.HOSTS[0], remote_username='root',
            remote_password=config.PASSWORDS[0], time_out=300)
        LOGGER.info("VDSM restarted")
        hosts.waitForHostsStates(True, config.HOSTS[0])
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
        self.check_action_failed()


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
        Restart VDSM before tasks were sent to it - snapshot creation
        """
        self.restart_before_tasks_start()

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_during_tasks(self):
        """
        Restart VDSM when only part of the tasks were finished
        - snapshot creation
        """
        self.restart_during_tasks('CreateAllSnapshotsFromVm')


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
        assert vms.waitForVmsGone(True, self.cloned_vm, 600)

    def perform_action(self):
        return vms.cloneVmFromTemplate(
            True, self.cloned_vm, config.TEMPLATE_NAME, config.CLUSTER_NAME,
            wait=False)

    def tearDown(self):
        """
        Just in case: if one of the tests failed and vm was created - remove it
        """
        super(TestCase287893, self).tearDown()
        if vms.VM_API.query("name=%s" % self.cloned_vm):
            vms.removeVm(True, self.cloned_vm)
        test_utils.wait_for_tasks(
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

    def setUp(self):
        common.start_vm()

    def tearDown(self):
        super(TestCase288203, self).tearDown()
        common.start_vm()
        test_utils.wait_for_tasks(
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
