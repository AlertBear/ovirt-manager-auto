"""
Hotplug disk hooks
TCMS plan: https://tcms.engineering.redhat.com/plan/9940
"""

import logging
from concurrent.futures import ThreadPoolExecutor
import time

from art.test_handler.tools import bz, tcms

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains

import config
import helpers

LOGGER = logging.getLogger(__name__)

FILE_WITH_RESULTS = helpers.FILE_WITH_RESULTS
VM_NAME = helpers.VM_NAME
DISKS_TO_PLUG = helpers.DISKS_TO_PLUG
UNATTACHED_DISK = helpers.UNATTACHED_DISK
TEXT = helpers.TEXT


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)
    helpers.create_local_files_with_hooks()
    helpers.create_vm_with_disks()


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    helpers.remove_hook_files()
    storagedomains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


class TestCase286224(helpers.HotplugHookTest):
    """
    Check if before_disk_hotplug is called

    https://tcms.engineering.redhat.com/case/286224/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG[0:1]
    hooks = {'before_disk_hotplug': [helpers.HOOKFILENAME]}

    @tcms(9940, 286224)
    def test_before_disk_hotplug(self):
        """ Check if before_disk_hotplug is called
        """
        self.perform_action_and_verify_hook_called()


class TestCase286365(helpers.HotplugHookTest):
    """
    Check if after_disk_hotplug is called

    https://tcms.engineering.redhat.com/case/286365/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG[1:2]
    hooks = {'after_disk_hotplug': [helpers.HOOKFILENAME]}

    @tcms(9940, 286365)
    def test_after_disk_hotplug(self):
        """ Check if after_disk_hotplug is called
        """
        self.perform_action_and_verify_hook_called()


class TestCase286366(helpers.HotplugHookTest):
    """
    Check if before_disk_hotunplug is called

    https://tcms.engineering.redhat.com/case/286366/?from_plan=9940
    """
    __test__ = True
    active_disk = True
    action = [vms.deactivateVmDisk]
    use_disks = DISKS_TO_PLUG[2:3]
    hooks = {'before_disk_hotunplug': [helpers.HOOKFILENAME]}

    @tcms(9940, 286366)
    def test_before_disk_hotunplug(self):
        """ Check if before_disk_hotunplug is called
        """
        self.perform_action_and_verify_hook_called()


class TestCase286368(helpers.HotplugHookTest):
    """
    Check if after_disk_hotunplug is called

    https://tcms.engineering.redhat.com/case/286368/?from_plan=9940
    """
    __test__ = True
    active_disk = True
    action = [vms.deactivateVmDisk]
    use_disks = DISKS_TO_PLUG[3:4]
    hooks = {'after_disk_hotunplug': [helpers.HOOKFILENAME]}

    @tcms(9940, 286368)
    def test_after_disk_hotunplug(self):
        """ Check if after_disk_hotunplug is called
        """
        self.perform_action_and_verify_hook_called()


class TestCase286226(helpers.HotplugHookTest):
    """
    Check after_disk_hotplug for plugging 10 disks concurrently

    https://tcms.engineering.redhat.com/case/286226/?from_plan=9940
    """
    __test__ = True
    tcms_test_case = '286226'
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG
    hooks = {'after_disk_hotplug': [helpers.HOOKWITHSLEEPFILENAME]}

    @bz(991742)
    @tcms(9940, 286226)
    def test_after_disk_hotplug_10_disks_concurrently(self):
        """ try to hotplug 10 tests concurrently and check that all hooks
        were called
        """
        self.perform_action_and_verify_hook_called()

    def verify_hook_called(self):
        result = self.get_hooks_result_file()
        LOGGER.info(
            "Hook should have been called %s times" % len(DISKS_TO_PLUG))
        self.assertEqual(len(result), len(DISKS_TO_PLUG), result)


class TestCase287480(helpers.HotplugHookTest):
    """
    Check after_disk_hotunplug for unplugging 10 disks concurrently

    https://tcms.engineering.redhat.com/case/287480/?from_plan=9940
    """
    __test__ = True
    active_disk = True
    action = [vms.deactivateVmDisk]
    use_disks = DISKS_TO_PLUG
    hooks = {'after_disk_hotunplug': [helpers.HOOKWITHSLEEPFILENAME]}

    @bz(991742)
    @tcms(9940, 287480)
    def test_after_disk_hotunplug_10_disks_concurrently(self):
        """ Unplug concurrently 10 disks and check if after_unplug hook
            were called 10 times
        """
        self.perform_action_and_verify_hook_called()

    def verify_hook_called(self):
        result = self.get_hooks_result_file()
        LOGGER.info(
            "Hook should have been called %s times" % len(DISKS_TO_PLUG))
        self.assertEqual(len(result), len(DISKS_TO_PLUG), result)


class TestCase287249(helpers.HotplugHookTest):
    """
    Check if before_disk_hotplug is called when attaching & activating
    new disk

    https://tcms.engineering.redhat.com/case/286224/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = [UNATTACHED_DISK]
    hooks = {'before_disk_hotplug': [helpers.HOOKFILENAME]}

    def perform_action(self):
        assert disks.attachDisk(True, self.use_disks[0], VM_NAME)

    def put_disks_in_correct_state(self):
        pass

    @tcms(9940, 287249)
    def test_before_disk_hotplug_attaching_new_disk(self):
        """ Check if after_disk_hotunplug is called
        """
        self.perform_action_and_verify_hook_called()

    def tearDown(self):
        super(TestCase287249, self).tearDown()
        if self.use_disks[0] in vms.getVmDisks(VM_NAME):
            disks.detachDisk(True, self.use_disks[0], VM_NAME)


class TestCase287481(helpers.HotplugHookTest):
    """
    Check that activation will fail if after_disk_hotplug is a binary,
    executable file. Check that after removing the hook it will be possible
    to activate the disk.

    https://tcms.engineering.redhat.com/case/287481/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG[4:5]
    hooks = {'after_disk_hotplug': [helpers.HOOKJPEG]}

    def perform_action(self):
        LOGGER.info("Activate should fail")
        assert not vms.activateVmDisk(True, VM_NAME, self.use_disks[0])
        self.clear_hooks()
        assert vms.activateVmDisk(True, VM_NAME, self.use_disks[0])

    def verify_hook_called(self):
        LOGGER.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @tcms(9940, 287481)
    @bz(1015171)
    def test_after_disk_hotplug_binary_executable_hook_file(self):
        """ check that activate fail if hook is binary executable file
            check that after removing the hook file activation works
        """
        self.perform_action_and_verify_hook_called()


class TestCase286369(helpers.HotplugHookTest):
    """
    Check that non-executable hooks will not be called

    https://tcms.engineering.redhat.com/case/286369/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = None
    use_disks = DISKS_TO_PLUG[5:6]
    hooks = {'after_disk_hotunplug': [helpers.HOOKFILENAME],
             'after_disk_hotplug': [helpers.HOOKFILENAME]}

    def perform_action(self):
        assert vms.activateVmDisk(True, VM_NAME, self.use_disks[0])
        assert vms.deactivateVmDisk(True, VM_NAME, self.use_disks[0])

    def create_hook_file(self, local_hook, remote_hook):
        LOGGER.info("Hook file: %s" % remote_hook)
        assert self.machine.copyTo(local_hook, remote_hook)
        LOGGER.info("Don't change permissions to file")

    def verify_hook_called(self):
        LOGGER.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @tcms(9940, 286369)
    def test_non_executable_hooks(self):
        """ check that vdsm skip a hook file if it is non-executable
        """
        self.perform_action_and_verify_hook_called()


class TestCase286243(helpers.HotplugHookTest):
    """
    Multiple hooks for one action, checks that all will be called

    https://tcms.engineering.redhat.com/case/286243/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = None
    use_disks = DISKS_TO_PLUG[6:7]
    hooks = {
        'after_disk_hotplug': [
            helpers.HOOKFILENAME, helpers.HOOKPRINTFILENAME],
        'after_disk_hotunplug': [
            helpers.HOOKFILENAME, helpers.HOOKPRINTFILENAME]}

    def perform_action(self):
        assert vms.activateVmDisk(True, VM_NAME, self.use_disks[0])
        assert vms.deactivateVmDisk(True, VM_NAME, self.use_disks[0])

    def verify_hook_called(self):
        LOGGER.info("Verifying hook files...")
        result = self.get_hooks_result_file()
        self.assertEqual(
            len(result), 4, "There should have been 4 hooks called!")
        self.assertEqual(
            len([x for x in result if x.strip() == TEXT]), 2,
            "'%s' should appear twice!" % TEXT)

    @tcms(9940, 286243)
    def test_multiple_hooks(self):
        """ Multiple hooks for one action, checks that all will be called
        """
        self.perform_action_and_verify_hook_called()


class TestCase286861(helpers.HotplugHookTest):
    """
    Restart vdsm during before_disk_hotplug, action should fail

    https://tcms.engineering.redhat.com/case/286861/?from_plan=9940
    """
    __test__ = True
    tcms_test_case = '286861'
    active_disk = False
    action = None
    use_disks = DISKS_TO_PLUG[7:8]
    hooks = {'before_disk_hotplug': [helpers.HOOKWITHSLEEPFILENAME]}

    def perform_action(self):
        def func():
            time.sleep(5)
            test_utils.restartVdsmd(self.address, self.password)

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            attach = executor.submit(
                vms.activateVmDisk, False, VM_NAME, self.use_disks[0])
            executor.submit(func)

        self.assertTrue(attach.result(), "Activate should have failed")

    def verify_hook_called(self):
        LOGGER.info("File should be empty")
        assert not self.get_hooks_result_file()

    @tcms(9940, 286861)
    def test_multiple_hooks(self):
        """ Restart vdsm during before_disk_hotplug, action should fail
        """
        self.perform_action_and_verify_hook_called()

    def tearDown(self):
        # give vdsm time to restart
        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        super(TestCase286861, self).tearDown()
