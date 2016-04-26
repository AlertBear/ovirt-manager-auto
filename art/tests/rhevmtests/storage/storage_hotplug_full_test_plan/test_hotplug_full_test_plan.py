"""
Hotplug full test plan
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import pytest
import time
import tempfile
import os

import config
import helpers
from art.rhevm_api.tests_lib.high_level import (
    disks as hl_disks,
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils as utils
import art.test_handler.exceptions as exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase
from rhevmtests.storage import helpers as storage_helpers
from utilities import machine

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

FILE_WITH_RESULTS = config.FILE_WITH_RESULTS
DISKS_TO_PLUG = config.DISKS_TO_PLUG
UNATTACHED_DISK = config.UNATTACHED_DISKS_PER_STORAGE_TYPE
TEXT = config.TEXT

DISK_INTERFACES = (ENUMS['interface_virtio'],)

VM_NAMES = []
DISK_NAMES = dict()


@pytest.fixture(scope='module')
def initializer_module(request):
    """
    Create VM templates with various disk type combinations
    """
    def finalizer_module():
        """
        clean setup
        """
        test_failed = False
        logger.info("Teardown module")
        helpers.remove_hook_files()
        logger.info("Try to safely remove vms if they exist: %s", VM_NAMES)
        if not ll_vms.safely_remove_vms(VM_NAMES):
            logger.error("Failed to remove vms %s", VM_NAMES)
            test_failed = True

        for disks_to_remove in DISK_NAMES.values():
            logger.info("Removing disks %s", DISK_NAMES.values())
            if not hl_disks.delete_disks(disks_to_remove):
                logger.error("Failed to delete disks %s", disks_to_remove)
                test_failed = True

        disks_to_remove = []
        for unattached_disks_per_storage in (
                config.UNATTACHED_DISKS_PER_STORAGE_TYPE.values()
        ):
            for disk_to_remove in unattached_disks_per_storage:
                if ll_disks.checkDiskExists(True, disk_to_remove):
                    disks_to_remove.append(disk_to_remove)
        for unpluged_disks_per_storage in config.DISKS_TO_PLUG.values():
            for disk_to_remove in unpluged_disks_per_storage:
                if ll_disks.checkDiskExists(True, disk_to_remove):
                    disks_to_remove.append(disk_to_remove)

        logger.info("Removing disks %s", disks_to_remove)
        if not hl_disks.delete_disks(disks_to_remove):
            logger.error("Failed to delete disks %s", disks_to_remove)
            test_failed = True
        if test_failed:
            raise exceptions.TearDownException("Teardown failed")

    request.addfinalizer(finalizer_module)

    global DISK_NAMES
    logger.info("setup_module")
    helpers.create_local_files_with_hooks()
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        VM_NAMES.append(
            helpers.create_vm_with_disks(storage_domain, storage_type)
        )
        DISK_NAMES[storage_type] = (
            storage_helpers.start_creating_disks_for_test(
                False, storage_domain, storage_type
            )
        )
        logger.info("Waiting for vms to be installed")
        utils.wait_for_tasks(
            vdc=config.VDC, vdc_password=config.VDC_PASSWORD,
            datacenter=config.DATA_CENTER_NAME
        )
        logger.info(
            "All vms created successfully for storage type %s", storage_type
        )
    logger.info("Package setup successfully")


class HotplugHookTest(TestCase):
    """
    Basic class for disk hotplug hooks, all tests work as follows:
        * Prepare/clear environment
        * Install hooks
        * Perform an action (attach/activate/deactivate a disk)
        * Check if correct hooks were called
    """
    hook_dir = None
    vm_name = None
    __test__ = False
    active_disk = None
    hooks = {}
    use_disks = []
    action = [lambda a, b, c, wait: True]

    def initializer(self):
        """
        perform actions:
            * Clear all hooks
            * Clear hook result file
            * Put disks in correct state
            * Install new hook(s)
        """
        logger.info("setup function")
        self.use_disks = DISKS_TO_PLUG[self.storage]
        self.vm_name = config.VM_NAME % self.storage
        if ll_vms.get_vm_state(self.vm_name) != config.VM_UP:
            # TODO: Because of BZ1273891 - vm can be down after the hotplug
            ll_vms.startVm(True, self.vm_name)
            ll_vms.waitForVMState(self.vm_name)
        self.host_name = ll_vms.getVmHost(self.vm_name)[1]['vmHoster']
        self.host_address = ll_hosts.getHostIP(self.host_name)
        logger.info("Host: %s" % self.host_address)

        logger.info("Looking for username and password")
        self.user = config.HOSTS_USER
        self.password = config.HOSTS_PW

        logger.info("Creating 'machine' object")
        self.machine = machine.LinuxMachine(
            self.host_address, self.user, self.password, False)

        logger.info("Clearing old hooks")
        self.clear_hooks()

        logger.info("Clearing old hooks results")
        self.clear_file_for_hook_resuls()

        logger.info("Putting disks in correct state")
        self.put_disks_in_correct_state()

        logger.info("Installing hooks")
        self.install_required_hooks()

    def finalizer(self):
        """ Clear hooks and removes hook results """
        logger.info("Teardown function")
        self.run_cmd(['rm', '-f', FILE_WITH_RESULTS])
        self.clear_hooks()
        ll_vms.stop_vms_safely([self.vm_name])

    @pytest.fixture(scope='function')
    def initializer_hotplug_hook(self, request, initializer_module):
        request.addfinalizer(self.finalizer)
        self.initializer()

    def run_cmd(self, cmd):
        rc, out = self.machine.runCmd(cmd)
        self.assertTrue(rc, "Command %s failed: %s" % (cmd, out))
        return out

    def create_hook_file(self, local_hook, remote_hook):
        """ Copies a local hook file to a remote location """
        logger.info("Hook file: %s" % remote_hook)
        assert self.machine.copyTo(local_hook, remote_hook)
        logger.info("Changing permissions")
        self.run_cmd(["chmod", "775", remote_hook])
        self.run_cmd(["chown", "36:36", remote_hook])

    def put_disks_in_correct_state(self):
        """ Activate/Deactivate disks we will use in the test """
        for disk_name in self.use_disks:
            disk = ll_disks.getVmDisk(self.vm_name, disk_name)
            logger.info("Disk active: %s" % disk.active)
            if disk.get_active() and not self.active_disk:
                assert ll_vms.deactivateVmDisk(True, self.vm_name, disk_name)
            elif not disk.get_active() and self.active_disk:
                assert ll_vms.activateVmDisk(True, self.vm_name, disk_name)

    def clear_hooks(self):
        """ Clear all VDSM hot(un)plug hook directories """
        for hook_dir in config.ALL_AVAILABLE_HOOKS:
            remote_hooks = os.path.join(config.MAIN_HOOK_DIR, hook_dir, '*')
            self.run_cmd(['rm', '-f', remote_hooks])

    def clear_file_for_hook_resuls(self):
        """ Removes old hook result file, creates an empty result file """
        logger.info("Removing old results")
        self.run_cmd(['rm', '-f', FILE_WITH_RESULTS])
        logger.info("Touching result file")
        self.run_cmd(['touch', FILE_WITH_RESULTS])
        logger.info("Changing permissions of results")
        self.run_cmd(['chown', 'vdsm:kvm', FILE_WITH_RESULTS])

    def install_required_hooks(self):
        """ Install all the hooks required for the tests """
        for hook_dir, hooks in self.hooks.iteritems():
            for hook in hooks:
                remote_hook = os.path.join(
                    config.MAIN_HOOK_DIR, hook_dir, os.path.basename(hook))
                self.create_hook_file(hook, remote_hook)

    def get_hooks_result_file(self):
        """ Reads hook result file """
        _, tmpfile = tempfile.mkstemp()
        logger.info("temp: %s" % tmpfile)
        try:
            self.machine.copyFrom(FILE_WITH_RESULTS, tmpfile)
            with open(tmpfile) as handle:
                result = handle.readlines()
            logger.debug("Hook result: %s", "".join(result))
            return result
        finally:
            os.remove(tmpfile)

    def verify_hook_called(self):
        """
        verify if the correct hooks were called, ensuring that the hook result
        file is not empty
        """
        assert self.get_hooks_result_file()

    def perform_action(self):
        """
        Perform defined action (plug/unplug disk) on given disks and checks
        whether action was successful
        """
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_results = dict(
                (executor.submit(
                    self.action[0], True, self.vm_name, disk_name,
                ), disk_name) for disk_name in self.use_disks
            )
        for future in as_completed(future_to_results):
            disk_name = future_to_results[future]
            self.assertTrue(
                future.result(), "Failed to perform action %s on %s" % (
                    self.action[0].__name__, disk_name),
            )

    def perform_action_and_verify_hook_called(self):
        """
        Calls defined action (activate/deactivate disk) and checks if hooks
        were called
        """
        self.perform_action()
        self.verify_hook_called()


@attr(tier=1)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5033(HotplugHookTest):
    """
    Check if before_disk_hotplug is called

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = [ll_vms.activateVmDisk]
    hooks = {'before_disk_hotplug': [config.HOOKFILENAME]}

    @polarion("RHEVM3-5033")
    def test_before_disk_hotplug(self):
        """ Check if before_disk_hotplug is called """
        self.use_disks = DISKS_TO_PLUG[self.storage][0:1]
        self.perform_action_and_verify_hook_called()


@attr(tier=1)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5034(HotplugHookTest):
    """
    Check if after_disk_hotplug is called

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = [ll_vms.activateVmDisk]
    hooks = {'after_disk_hotplug': [config.HOOKFILENAME]}

    @polarion("RHEVM3-5034")
    def test_after_disk_hotplug(self):
        """ Check if after_disk_hotplug is called """
        self.use_disks = DISKS_TO_PLUG[self.storage][1:2]
        self.perform_action_and_verify_hook_called()


@attr(tier=1)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5035(HotplugHookTest):
    """
    Check if before_disk_hotunplug is called

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = True
    action = [ll_vms.deactivateVmDisk]
    hooks = {'before_disk_hotunplug': [config.HOOKFILENAME]}

    @polarion("RHEVM3-5035")
    def test_before_disk_hotunplug(self):
        """ Check if before_disk_hotunplug is called """
        self.use_disks = DISKS_TO_PLUG[self.storage][2:3]
        self.perform_action_and_verify_hook_called()


@attr(tier=1)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5036(HotplugHookTest):
    """
    Check if after_disk_hotunplug is called

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = True
    action = [ll_vms.deactivateVmDisk]
    hooks = {'after_disk_hotunplug': [config.HOOKFILENAME]}

    @polarion("RHEVM3-5036")
    def test_after_disk_hotunplug(self):
        """ Check if after_disk_hotunplug is called """
        self.use_disks = DISKS_TO_PLUG[self.storage][3:4]
        self.perform_action_and_verify_hook_called()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5037(HotplugHookTest):
    """
    Check after_disk_hotplug for plugging 7 disks concurrently

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = [ll_vms.activateVmDisk]
    hooks = {'after_disk_hotplug': [config.HOOKWITHSLEEPFILENAME]}

    @polarion("RHEVM3-5037")
    def test_after_disk_hotplug_5_disks_concurrently(self):
        """
        Try to hotplug 7 tests concurrently and check that all hooks were
        called
        """
        self.use_disks = DISKS_TO_PLUG[self.storage]
        self.perform_action_and_verify_hook_called()

    def verify_hook_called(self):
        result = self.get_hooks_result_file()
        logger.info(
            "Hook should have been called %s times", len(
                DISKS_TO_PLUG[self.storage]
            )
        )
        self.assertEqual(len(result), len(DISKS_TO_PLUG[self.storage]), result)


@attr(tier=2)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5038(HotplugHookTest):
    """
    Check after_disk_hotunplug for unplugging 7 disks concurrently

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = True
    action = [ll_vms.deactivateVmDisk]
    hooks = {'after_disk_hotunplug': [config.HOOKWITHSLEEPFILENAME]}

    @polarion("RHEVM3-5038")
    def test_after_disk_hotunplug_5_disks_concurrently(self):
        """
        Concurrently unplug 7 disks and check if after_unplug hook were
        called 7 times
        """
        self.use_disks = DISKS_TO_PLUG[self.storage]
        self.perform_action_and_verify_hook_called()

    def verify_hook_called(self):
        result = self.get_hooks_result_file()
        logger.info(
            "Hook should have been called %s times", len(
                DISKS_TO_PLUG[self.storage]
            )
        )
        self.assertEqual(len(result), len(DISKS_TO_PLUG[self.storage]), result)


@attr(tier=2)
class TestCase5039(HotplugHookTest):
    """
    Check if before_disk_hotplug is called when attaching & activating
    new disk

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = [ll_vms.activateVmDisk]
    hooks = {'before_disk_hotplug': [config.HOOKFILENAME]}

    @pytest.fixture(scope='function')
    def initializer_TestCase5039(self, request, initializer_module):
        def finalizer_TestCase5039():
            self.finalizer()
            vm_disks = ll_vms.getVmDisks(self.vm_name)
            disk_names = [disk.get_name() for disk in vm_disks]
            if self.use_disks[0] in disk_names:
                ll_disks.detachDisk(True, self.use_disks[0], self.vm_name)
        request.addfinalizer(finalizer_TestCase5039)
        self.initializer()

    def perform_action(self):
        if ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME):
            vm_disks = ll_vms.getVmDisks(self.vm_name)
            disk_names = [disk.get_name() for disk in vm_disks]
            if not self.use_disks[0] in disk_names:
                self.assertTrue(
                    ll_disks.attachDisk(True, self.use_disks[0], self.vm_name),
                    "Failed to attach disk %s to vm %s" % (
                        self.use_disks[0], self.vm_name
                    )
                )

    def put_disks_in_correct_state(self):
        pass

    @polarion("RHEVM3-5039")
    @pytest.mark.usefixtures("initializer_TestCase5039")
    def test_before_disk_hotplug_attaching_new_disk(self):
        """ Check if after_disk_hotunplug is called """
        self.use_disks = UNATTACHED_DISK[self.storage]
        self.perform_action_and_verify_hook_called()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5044(HotplugHookTest):
    """
    Check that activation will succeed and the hook will fail if
    after_disk_hotplug is a binary, executable file.
    Check that after removing the hook everything act normal

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = [ll_vms.activateVmDisk]
    hooks = {'after_disk_hotplug': [config.HOOKJPEG]}

    def perform_action(self):
        logger.info("Activating new HW - %s", self.use_disks[0])

        vm_disks = ll_vms.getVmDisks(self.vm_name)
        disk_names = [disk.get_name() for disk in vm_disks]

        logger.info("Attached disks - %s", disk_names)
        if not self.use_disks[0] in disk_names:
            self.assertTrue(
                ll_disks.attachDisk(
                    True, self.use_disks[0], self.vm_name, False
                ), "Failed to attach disk %s to vm %s" %
                   (self.use_disks[0], self.vm_name)
            )

        self.assertTrue(
            ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0]),
            "Activation of VM disk %s should have succeed" % self.use_disks[0])

        ll_vms.deactivateVmDisk(True, self.vm_name, self.use_disks[0])

        self.clear_hooks()
        assert ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0])

    def verify_hook_called(self):
        logger.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @polarion("RHEVM3-5044")
    def test_after_disk_hotplug_binary_executable_hook_file(self):
        """
        Check that activate succeed and hook fails if hook is binary
        executable file
        """
        self.use_disks = DISKS_TO_PLUG[self.storage][4:5]
        self.perform_action_and_verify_hook_called()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5041(HotplugHookTest):
    """
    Check that non-executable hooks will not be called

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = None
    hooks = {'after_disk_hotunplug': [config.HOOKFILENAME],
             'after_disk_hotplug': [config.HOOKFILENAME]}

    def perform_action(self):
        assert ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0])
        assert ll_vms.deactivateVmDisk(True, self.vm_name, self.use_disks[0])

    def create_hook_file(self, local_hook, remote_hook):
        logger.info("Hook file: %s", remote_hook)
        assert self.machine.copyTo(local_hook, remote_hook)
        logger.info("Don't change permissions to file")

    def verify_hook_called(self):
        logger.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @polarion("RHEVM3-5041")
    def test_non_executable_hooks(self):
        """ Check that vdsm skips a hook file if it is non-executable """
        self.use_disks = DISKS_TO_PLUG[self.storage][5:6]
        self.perform_action_and_verify_hook_called()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_hotplug_hook")
class TestCase5040(HotplugHookTest):
    """
    Multiple hooks for one action, checks that all will be called

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    active_disk = False
    action = None
    hooks = {
        'after_disk_hotplug': [config.HOOKFILENAME, config.HOOKPRINTFILENAME],
        'after_disk_hotunplug': [config.HOOKFILENAME, config.HOOKPRINTFILENAME]
    }

    def perform_action(self):
        assert ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0])
        assert ll_vms.deactivateVmDisk(True, self.vm_name, self.use_disks[0])

    def verify_hook_called(self):
        logger.info("Verifying hook files...")
        result = self.get_hooks_result_file()
        self.assertEqual(
            len(result), 4, "There should have been 4 hooks called!")
        self.assertEqual(
            len([x for x in result if x.strip() == TEXT]), 2,
            "'%s' should have appeared twice!" % TEXT
        )

    @polarion("RHEVM3-5040")
    def test_multiple_hooks(self):
        """ Multiple hooks for one action, checks that all will be called """
        self.use_disks = DISKS_TO_PLUG[self.storage][6:7]
        self.perform_action_and_verify_hook_called()


@attr(tier=4)
class TestCase5042(HotplugHookTest):
    """
    Restart vdsm during before_disk_hotplug, action should fail

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_HotPlug_Hooks
    """
    __test__ = True
    polarion_test_case = '5042'
    active_disk = False
    action = None
    hooks = {'before_disk_hotplug': [config.HOOKWITHSLEEPFILENAME]}

    @pytest.fixture(scope='function')
    def initializer_TestCase5042(self, request, initializer_module):
        def finalizer_TestCase5042():
            """
            Give VDSM time to restart and clean the environment
            """
            ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
            ll_hosts.waitForHostsStates(True, [self.host_name])
            self.finalizer()
        request.addfinalizer(finalizer_TestCase5042)

    def perform_action(self):
        def func():
            time.sleep(5)
            utils.restartVdsmd(self.host_address, self.password)

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            attach = executor.submit(
                ll_vms.activateVmDisk, False, self.vm_name, self.use_disks[0]
            )
            executor.submit(func)

        self.assertTrue(attach.result(), "Activate should have failed")

    def verify_hook_called(self):
        logger.info("File should be empty")
        assert not self.get_hooks_result_file()

    @polarion("RHEVM3-5042")
    @pytest.mark.usefixtures("initializer_TestCase5042")
    def test_multiple_hooks(self):
        """ Restart VDSM during before_disk_hotplug, action should fail """
        self.use_disks = DISKS_TO_PLUG[self.storage][7:8]
        self.perform_action_and_verify_hook_called()


class BasePlugDiskTest(TestCase):

    __test__ = False

    @pytest.fixture(scope='class')
    def initializer_plug_disk(self, request, initializer_module):
        """
        Clone a vm of each supported OS type and wait for VM boot to complete
        """
        def finalizer_plug_disk():
            """
            Powers off and removes the created VMs, removes disks created
            """
            if not ll_vms.stop_vms_safely(self.vm_names):
                logger.error(
                    "Failed to power off VMs '%s'", ', '.join(self.vm_names)
                )
                self.test_failed = True
            hl_disks.delete_disks(
                filter(lambda w: ll_disks.checkDiskExists(True, w), self.disks)
            )
            if not ll_vms.safely_remove_vms(self.vm_names):
                logger.error(
                    "Failed to remove VMs '%s'", ', '.join(self.vm_names)
                )
                self.test_failed = True
            self.teardown_exception()

        request.addfinalizer(finalizer_plug_disk)
        logger.info("setup class %s", self.__name__)

        self.disks = []
        self.vm_names = []
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        def _create_and_start_vm():
            """ Clones and starts a single vm from template """
            vm_name = helpers.create_vm_from_template(
                self.__name__, self.storage_domain,
                self.storage
            )
            logger.info("Starting VM %s", vm_name)
            ll_vms.startVm(True, vm_name, wait_for_ip=True)
            logger.info("VM %s started successfully", vm_name)
            self.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            results.append(executor.submit(_create_and_start_vm))

        utils.raise_if_exception(results)


@attr(tier=1)
@pytest.mark.usefixtures("initializer_plug_disk")
class TestCase6231(BasePlugDiskTest):
    """
    Activate/Deactivate an already attached disk on a running VM with
    supported OS
    """
    __test__ = True

    polarion_test_case = '6231'
    interfaces = [config.VIRTIO, config.VIRTIO_SCSI]

    @pytest.fixture(scope='class')
    def initializer_TestCase6231(self, request, initializer_plug_disk):
        """
        Create a VM with 2 disks extra disks - 1 active and 1 inactive
        """
        ll_vms.stop_vms_safely(self.vm_names)
        for vm_name, interface in zip(self.vm_names, self.interfaces):
            # add disk and deactivate it
            logger.info("Adding 2 disks to VM %s", vm_name)
            disk_args = {
                'positive': True,
                'size': 1 * config.GB,
                'sparse': True,
                'wipe_after_delete': self.storage in config.BLOCK_TYPES,
                'storagedomain': self.storage_domain,
                'bootable': False,
                'interface': interface,
                'vm': vm_name,
            }

            # add 2 disks:
            for active in True, False:
                disk_alias = "%s_%s_Disk" % (vm_name, str(active))
                logger.info(
                    "Adding disk to vm %s with %s active disk",
                    vm_name, "not" if not active else ""
                )
                if not ll_vms.addDisk(
                    active=active, alias=disk_alias, **disk_args
                ):
                    raise exceptions.DiskException(
                        "Unable to add disk to VM %s" % vm_name
                    )

                self.disks.append(disk_alias)
            if not ll_vms.startVm(True, vm_name, config.VM_UP, True):
                raise exceptions.VMException(
                    "Unable to power on VM %s" % vm_name
                )

    @polarion("RHEVM3-6231")
    @pytest.mark.usefixtures("initializer_TestCase6231")
    def test_activate_deactivate_disk(self):
        """ Activate an already attached disk on a running VM """
        for vm in self.vm_names:
            inactive_disks = [disk for disk in ll_vms.getVmDisks(vm)
                              if not disk.get_bootable() and
                              not disk.get_active()]
            disk_name = inactive_disks[0].get_name()
            logger.info("Activating disk %s on VM %s", disk_name, vm)
            status = ll_vms.activateVmDisk(True, vm, disk_name)
            logger.info("Finished activating disk %s", disk_name)
            self.assertTrue(status)

            active_disks = [disk for disk in ll_vms.getVmDisks(vm)
                            if not disk.get_bootable() and
                            disk.get_active()]
            disk_name = active_disks[0].get_name()
            logger.info("Deactivating disk %s on VM %s", disk_name, vm)
            status = ll_vms.deactivateVmDisk(True, vm, disk_name)
            logger.info("Finished deactivating disk %s", disk_name)
            self.assertTrue(status)


@attr(tier=2)
@pytest.mark.usefixtures("initializer_plug_disk")
class TestCase6243(BasePlugDiskTest):
    """ Hotplug floating disk (shareable and non-shareable) """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '6243'

    @pytest.fixture(scope='function')
    def initializer_TestCase6243(self, request, initializer_plug_disk):
        """
        Create the required disks for this test
        """
        def finalizer_TestCase6243():
            """ Remove the disks created for this test """
            if not ll_vms.stop_vms_safely([self.vm_names[0]]):
                logger.error("Failed to power off VM '%s'", self.vm_names[0])
                BasePlugDiskTest.test_failed = True
            for disk_alias in self.disk_aliases:
                if not ll_vms.removeDisk(True, self.vm_names[0], disk_alias):
                    logger.error("Failed to remove disk '%s'", disk_alias)
                    BasePlugDiskTest.test_failed = True
            BasePlugDiskTest.teardown_exception()

        request.addfinalizer(finalizer_TestCase6243)
        self.disk_aliases = []
        for disk_interface in DISK_INTERFACES:
            for shareable in (True, False):
                disk_params = config.disk_args.copy()
                disk_params['provisioned_size'] = 1 * config.GB
                disk_params['interface'] = disk_interface
                disk_params['shareable'] = shareable
                # For shareable disks, use Raw/Preallocated disk format
                if shareable:
                    disk_params['format'] = config.DISK_FORMAT_RAW
                    disk_params['sparse'] = False
                disk_params['storagedomain'] = self.storage_domain
                disk_params['alias'] = self.create_unique_object_name(
                    config.OBJECT_TYPE_DISK
                )
                if not ll_disks.addDisk(True, **disk_params):
                    raise exceptions.DiskException(
                        "Can't create disk with params: %s" % disk_params
                    )
                logger.info(
                    "Waiting for disk %s to be OK", disk_params['alias']
                )
                if not ll_disks.wait_for_disks_status(disk_params['alias']):
                    raise exceptions.DiskException(
                        "Disk '%s' has not reached state 'OK'" %
                        disk_params['alias']
                    )
                self.disk_aliases.append(disk_params['alias'])

    @polarion("RHEVM3-6243")
    @pytest.mark.usefixtures("initializer_TestCase6243")
    def test_plug_floating_disk(self):
        """ Hotplug floating disk (shareable/non-shareable) to vm """
        for disk_alias in self.disk_aliases:
            vm_name = self.vm_names[0]
            logger.info(
                "Attempting to plug disk %s to vm %s", disk_alias, vm_name
            )
            if not ll_disks.attachDisk(True, disk_alias, vm_name):
                raise exceptions.DiskException(
                    "Failed to attach disk %s to vm %s" %
                    (disk_alias, vm_name)
                )


@attr(tier=2)
class TestCase6230(TestCase):
    """
    2 vms, 1 shareable disk attached to both of them, ensure hotplug works
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])

    polarion_test_case = '6230'

    disk_count = 2
    first_vm = polarion_test_case + '_first'
    second_vm = polarion_test_case + '_second'
    first_disk_name = polarion_test_case + '_non-shareable_virtio_disk'
    second_disk_name = polarion_test_case + '_shareable_virtio_disk'
    disks_aliases = [first_disk_name, second_disk_name]
    formats = [config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW]
    shareable = [False, True]
    interfaces = [config.VIRTIO, config.VIRTIO_SCSI]

    @pytest.fixture(scope='class')
    def initializer_TestCase6230(self, request, initializer_module):
        """
        Create 2 VMs, 2 virtio disks and one of them is shareable
        """
        def finalizer_TestCase6230():
            """ Remove all vms and disks created for the tests """
            if not ll_vms.stop_vms_safely(self.vm_names):
                logger.error(
                    "Failed to power off VMs '%s'", ', '.join(self.vm_names)
                )
                self.test_failed = True
            logger.info("Removing disks  %s", self.disks_aliases)
            for disk_alias in self.disks_aliases:
                if not ll_disks.deleteDisk(True, disk_alias):
                    logger.error("Failed to delete disk '%s'", disk_alias)
                    self.test_failed = True
            if not ll_vms.safely_remove_vms(self.vm_names):
                logger.error(
                    "Failed to remove VMs '%s'", ', '.join(self.vm_names)
                )
                self.test_failed = True
            self.teardown_exception()

        request.addfinalizer(finalizer_TestCase6230)
        self.vm_names = []
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.first_vm = helpers.create_vm_from_template(
            self.first_vm, self.storage_domain,
            self.storage
        )

        # add disk and attach it
        logger.info("Adding 2 disks to VM %s", self.first_vm)

        for index in range(self.disk_count):
            disk_args = {
                'positive': True,
                'alias': self.disks_aliases[index],
                'provisioned_size': 1 * config.GB,
                'format': self.formats[index],
                'sparse': True,
                'wipe_after_delete': self.storage in config.BLOCK_TYPES,
                'storagedomain': self.storage_domain,
                'bootable': False,
                'interface': self.interfaces[index],
                'shareable': self.shareable[index],
            }
            if self.storage == config.ENUMS['storage_type_iscsi'] and (
                disk_args['format'] == ENUMS['format_raw']
            ):
                disk_args['sparse'] = False

            logger.info("Adding %s disk...", self.disks_aliases[index])
            if not ll_disks.addDisk(**disk_args):
                raise exceptions.DiskException(
                    "Unable to add disk %s" % self.disks_aliases[index]
                )
            ll_vms.wait_for_disks_status([self.disks_aliases[index]])

            if not ll_disks.attachDisk(
                True, self.disks_aliases[index], self.first_vm, False
            ):
                raise exceptions.DiskException(
                    "Unable to attach disk %s to vm %s" %
                    (self.disks_aliases[index], self.first_vm)
                )
            logger.info(
                "%s disk added successfully", self.disks_aliases[index]
            )

        self.second_vm = helpers.create_vm_from_template(
            self.second_vm, self.storage_domain, self.storage
        )

        if not ll_disks.attachDisk(
            True, self.second_disk_name, self.second_vm, False
        ):
            raise exceptions.DiskException(
                "Failed to attach disk %s to vm %s" %
                (self.second_disk_name, self.second_vm)
            )
        self.vm_names = [self.first_vm, self.second_vm]

    @polarion("RHEVM3-6230")
    @pytest.mark.usefixtures("initializer_TestCase6230")
    def test_deactivate_and_activate_disk(self):
        """
        Deactivate an already attached disk on a running VM and then
        activates it
        """
        for vm in self.vm_names:
            self.assertTrue(
                ll_vms.startVm(True, vm), "Unable to power on VM '%s'" % vm
            )

        for vm in self.vm_names:
            active_disks = [disk for disk in ll_vms.getVmDisks(vm)
                            if not disk.get_bootable() and
                            disk.get_active()]
            if len(active_disks) > 0:
                disk_name = active_disks[0].get_name()
                logger.info("Deactivating disk %s on VM %s", disk_name, vm)
                status = ll_vms.deactivateVmDisk(True, vm, disk_name)
                logger.info("Finished deactivating disk %s", disk_name)
                self.assertTrue(status)

        utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )

        for vm in self.vm_names:
            inactive_disks = [disk for disk in ll_vms.getVmDisks(vm)
                              if not disk.get_bootable() and
                              not disk.get_active()]
            if len(inactive_disks) > 0:
                for disk in inactive_disks:
                    disk_name = disk.get_name()
                    logger.info("Activating disk %s on VM %s", disk_name, vm)
                    ll_vms.wait_for_vm_states(vm, [config.VM_UP])
                    status = ll_vms.activateVmDisk(True, vm, disk_name)
                    logger.info("Finished activating disk %s", disk_name)
                    self.assertTrue(status)
