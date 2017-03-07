import config
import common
import logging
import time
from art.unittest_lib import StorageTest as TestCase, attr
from concurrent.futures import ThreadPoolExecutor
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, addSnapshot, removeSnapshot,
    validateSnapshot, startVm, suspendVm, wait_for_vm_states, get_vm_state,
    VM_API, waitForVmsGone, cloneVmFromTemplate, removeVm,
)
from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.utils.test_utils import wait_for_tasks, restart_engine
from art.rhevm_api.tests_lib.low_level.hosts import wait_for_hosts_states

logger = logging.getLogger(__name__)
VDSM_LOG = '/var/log/vdsm/vdsm.log'
ALL_TASKS_FINISHED = 'Number of running tasks: 0'
TIMEOUT = 300

OPERATION_FINISHED = False


@attr(tier=config.DO_NOT_RUN)
class RestartOvirt(TestCase):
    __test__ = False

    def tearDown(self):
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)

    def restart_before_tasks_start(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self.perform_action)
            executor.submit(
                restart_engine, config.ENGINE, 10, 75)
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)
        logger.info("checking if action failed")
        self.check_action_failed()

    def _wait_for_first_sent_and_restart_ovirt(self, action_name):
        global OPERATION_FINISHED
        OPERATION_FINISHED = False
        logger.info("Waiting for the first task to be sent")
        regex = "Adding task .*Parent Command %s.*" % action_name
        watch_logs(
            files_to_watch=config.ENGINE_LOG, regex=regex,
            ip_for_files=config.VDC, username=config.VDC_ROOT_USER,
            password=config.VDC_PASSWORD
        )
        OPERATION_FINISHED = True
        restart_engine(config.ENGINE, 10, 75)
        logger.info("ovirt-engine restarted")

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

        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)
        self.check_action_failed()

    def restart_after_finish_before_notified(self):
        self.perform_action()
        logger.info("Waiting for function to finish")
        regex = ALL_TASKS_FINISHED
        watch_logs(
            files_to_watch=VDSM_LOG, regex=regex,
            ip_for_files=config.HOSTS[0], username=config.HOSTS_USER,
            password=config.HOSTS_PW, time_out=TIMEOUT
        )
        restart_engine(config.ENGINE, 10, 75)
        logger.info("ovirt-engine restarted")
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)
        self.check_action_failed()

    def check_action_failed(self):
        pass

    def perform_action(self):
        pass


class TestCase6160(RestartOvirt):
    """
    Restart ovirt-engine during creation of a snapshot

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki
    /Storage/3_3_Storage_Async_Tasks
    """
    __test__ = True
    polarion_test_case = '6160'
    snapshot_name = "snap_%s" % polarion_test_case

    def tearDown(self):
        super(TestCase6160, self).tearDown()
        if validateSnapshot(True, config.VM_NAME[0], self.snapshot_name):
            logger.info("Stopping vm %s", config.VM_NAME[0])
            stop_vms_safely([config.VM_NAME[0]])
            waitForVMState(config.VM_NAME[0], config.VM_DOWN)

            logger.info("Removing snapshot %s", self.snapshot_name)
            assert removeSnapshot(
                True, config.VM_NAME[0], self.snapshot_name
            ), "Removing snapshot %s failed" % self.snapshot_name

            logger.info("Starting vm %s", config.VM_NAME[0])
            startVm(True, config.VM_NAME[0], config.VM_UP)

        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)
        assert wait_for_hosts_states(True, config.HOSTS[0])

    def perform_action(self):
        logger.info("Create snapshot %s", self.snapshot_name)
        assert addSnapshot(
            True, config.VM_NAME[0], self.snapshot_name, False
        ), "Adding snapshot %s failed" % self.snapshot_name

    def check_action_failed(self):
        assert not validateSnapshot(
            True, config.VM_NAME[0], self.snapshot_name
        ), "Snapshot %s exists!" % self.snapshot_name

    @polarion("RHEVM3-6160")
    def test_restart_before_tasks_start(self):
        """
        Restart ovirt engine before it gets info about tasks from UI
        - snapshot creation
        """
        stop_vms_safely([config.VM_NAME[0]])
        waitForVMState(config.VM_NAME[0], config.VM_DOWN)

        self.restart_before_tasks_start()

    @polarion("RHEVM3-6160")
    def test_restart_during_tasks(self):
        """
        Restart ovirt engine when only part of the tasks were sent
        - snapshot creation
        """
        stop_vms_safely([config.VM_NAME[0]])
        waitForVMState(config.VM_NAME[0], config.VM_DOWN)

        self.restart_during_tasks('CreateAllSnapshotsFromVm')

# TODO: commented out as it is failing
#    @polarion("RHEVM3-")
#    def test_restart_after_finish_before_notified(self):
#        """
#        Restart ovirt engine when tasks were finished but engine weren't
#        notified - snapshot creation
#        """
#        self.restart_after_finish_before_notified()


class TestCase6161(RestartOvirt):
    """
    Restart ovirt-engine during hibernate a VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki
    /Storage/3_3_Storage_Async_Tasks
    """
    __test__ = True
    polarion_test_case = '6161'

    def setUp(self):
        common.start_vm()

    def tearDown(self):
        super(TestCase6161, self).tearDown()
        common.start_vm()
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)

    def perform_action(self):
        logger.info("Suspending vm %s", config.VM_NAME[0])
        assert suspendVm(True, config.VM_NAME[0], False)

    def check_action_failed(self):
        wait_for_vm_states(config.VM_NAME[0],
                           [config.VM_UP, config.VM_DOWN, config.VM_SUSPENDED])
        status = get_vm_state(config.VM_NAME[0])
        assert status == config.VM_UP, (
            "VM %s status incorrect, is: %s, should be: %s" %
            (config.VM_NAME[0], status, config.VM_UP)
        )

    @polarion("RHEVM3-6161")
    def test_restart_before_tasks_start(self):
        """
        Restart ovirt engine before it gets info about tasks from UI
        - pausing vm
        """
        self.restart_before_tasks_start()

# TODO: commented out as it is failing
#    @polarion("RHEVM3-")
#    def test_restart_during_tasks(self):
#        """ restart ovirt engine when only part of the tasks were sent
#            - pausing vm
#        """
#        self.restart_during_tasks('HibernateVm')

# TODO: commented out as it is failing
#    @polarion("RHEVM3-")
#    def test_restart_after_finish_before_notified(self):
#        """ restart ovirt engine when tasks were finished
#            but engine weren't notified - pausing vm
#        """
#        self.restart_after_finish_before_notified()


class TestCase6162(RestartOvirt):
    """
    Restart ovirt-engine during cloning a VM from a template

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki
    /Storage/3_3_Storage_Async_Tasks
    """
    __test__ = True
    polarion_test_case = '6162'
    cloned_vm = "vm_%s" % polarion_test_case

    def tearDown(self):
        """
        Just in case: if one of the tests failed and vm was created - remove it
        """
        super(TestCase6162, self).tearDown()
        if VM_API.query("name=%s" % self.cloned_vm):
            removeVm(True, self.cloned_vm)
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME)

    def check_action_failed(self):
        assert waitForVmsGone(True, self.cloned_vm, 600)

    def perform_action(self):
        logger.info("Cloning vm %s from template %s", self.cloned_vm,
                    config.TEMPLATE_NAME)

        return cloneVmFromTemplate(
            True, self.cloned_vm, config.TEMPLATE_NAME, config.CLUSTER_NAME,
            wait=False)

    @polarion("RHEVM3-6162")
    def test_restart_before_tasks_start(self):
        """
        Restart ovirt engine before it gets info about tasks from UI
        - cloning vm from template
        """
        self.restart_before_tasks_start()

    @polarion("RHEVM3-6162")
    def test_restart_during_tasks(self):
        """
        Restart ovirt engine when only part of the tasks were sent
        - cloning vm from template
        """
        self.restart_during_tasks('AddVmFromTemplate')

# TODO: commented out as it is failing
#    @polarion("RHEVM3-")
#    def test_restart_after_finish_before_notified(self):
#        """ restart ovirt engine when tasks were finished
#            but engine weren't notified - cloning vm from template
#        """
#        self.restart_after_finish_before_notified()
