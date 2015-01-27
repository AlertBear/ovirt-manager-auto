"""
Hotplug full test plan
"""

import logging
from concurrent.futures import ThreadPoolExecutor
import time

from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr

from art.rhevm_api.utils import test_utils as utils
import art.test_handler.exceptions as exceptions
from art.rhevm_api.utils.test_utils import wait_for_tasks

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    cleanDataCenter, getStorageDomainNamesForType,
)

from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import vms, disks, templates, hosts
from art.rhevm_api.tests_lib.high_level.disks import delete_disks

import config
import helpers
import common
from art.unittest_lib import StorageTest as TestCase

LOGGER = logging.getLogger(__name__)
ENUMS = config.ENUMS

FILE_WITH_RESULTS = helpers.FILE_WITH_RESULTS
DISKS_TO_PLUG = helpers.DISKS_TO_PLUG
UNATTACHED_DISK = helpers.UNATTACHED_DISK
TEXT = helpers.TEXT

DISK_INTERFACES = (ENUMS['interface_virtio'],)

positive = True
VM_NAMES = []
TEMPLATE_NAMES = []
DISK_NAMES = []


def setup_module():
    """
    Create VM templates with different OSs and all disk type combinations
    """
    global DISK_NAMES
    LOGGER.info("setup_module")
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE)

    helpers.create_local_files_with_hooks()
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]
        block = storage_type in config.BLOCK_TYPES

        VM_NAMES.append(
            helpers.create_vm_with_disks(storage_domain, storage_type))

        disks_tuple = common.start_creating_disks_for_test(
            storage_domain, block, storage_type)

        DISK_NAMES = [disk[0] for disk in disks_tuple]
        disk_results = [disk[1] for disk in disks_tuple]

        TEMPLATE_NAMES.append(
            common.create_vm_and_template(
                config.COBBLER_PROFILE, storage_domain, storage_type))

        LOGGER.info("Ensuring all disks were created successfully")
        for result in disk_results:
            exception = result.exception()
            if exception is not None:
                raise exception
            status, diskIdDict = result.result()
            if not status:
                raise exceptions.DiskException("Unable to create disk")
        LOGGER.info("All disks created successfully")
        LOGGER.info("Waiting for vms to be installed and templates "
                    "to be created")

        if config.VDC is not None and config.VDC_PASSWORD is not None:
            LOGGER.info("Waiting for vms to be installed and "
                        "templates to be created")
            wait_for_tasks(
                vdc=config.VDC, vdc_password=config.VDC_PASSWORD,
                datacenter=config.DATA_CENTER_NAME)
    LOGGER.info("All templates created successfully")
    LOGGER.info("Package setup successfully")


def teardown_module():
    """
    clean setup
    """
    LOGGER.info("Teardown module")
    helpers.remove_hook_files()

    external_vms = ["external-%s" % name for name in VM_NAMES]
    vm_names = external_vms + VM_NAMES
    LOGGER.info("Try to safely remove vms if they exist: %s", vm_names)
    vms.safely_remove_vms(vm_names)

    LOGGER.info("Removing disks %s", DISK_NAMES)
    delete_disks(DISK_NAMES)

    plug_disks = [disk for disk in ([helpers.UNATTACHED_DISK] +
                  helpers.DISKS_TO_PLUG)if disks.checkDiskExists(True, disk)]
    LOGGER.info("Removing disks from plug tests %s", plug_disks)
    delete_disks(plug_disks)

    LOGGER.info("Removing templates %s", TEMPLATE_NAMES)
    for template in TEMPLATE_NAMES:
        templates.removeTemplate(True, template)

    if not config.GOLDEN_ENV:
        cleanDataCenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD)


@attr(tier=0)
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


@attr(tier=0)
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


@attr(tier=0)
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


@attr(tier=0)
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


@attr(tier=2)
class TestCase286226(helpers.HotplugHookTest):
    """
    Check after_disk_hotplug for plugging 10 disks concurrently

    https://tcms.engineering.redhat.com/case/286226/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG
    hooks = {'after_disk_hotplug': [helpers.HOOKWITHSLEEPFILENAME]}

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


@attr(tier=2)
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


@attr(tier=2)
class TestCase287249(helpers.HotplugHookTest):
    """
    Check if before_disk_hotplug is called when attaching & activating
    new disk

    https://tcms.engineering.redhat.com/case/287249/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = [UNATTACHED_DISK]
    hooks = {'before_disk_hotplug': [helpers.HOOKFILENAME]}

    def perform_action(self):
        if ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME):
            vm_disks = vms.getVmDisks(self.vm_name)
            disk_names = [disk.get_name() for disk in vm_disks]
            if not self.use_disks[0] in disk_names:
                self.assertTrue(disks.attachDisk(True, self.use_disks[0],
                                                 self.vm_name),
                                "Failed to attach disk %s to vm %s"
                                % (self.use_disks[0], self.vm_name))

    def put_disks_in_correct_state(self):
        pass

    @tcms(9940, 287249)
    def test_before_disk_hotplug_attaching_new_disk(self):
        """ Check if after_disk_hotunplug is called
        """
        self.perform_action_and_verify_hook_called()

    def tearDown(self):
        super(TestCase287249, self).tearDown()
        vm_disks = vms.getVmDisks(self.vm_name)
        disk_names = [disk.get_name() for disk in vm_disks]
        if self.use_disks[0] in disk_names:
            disks.detachDisk(True, self.use_disks[0], self.vm_name)


@attr(tier=2)
class TestCase287481(helpers.HotplugHookTest):
    """
    Check that activation will succeed and the hook will fail if
    after_disk_hotplug is a binary, executable file.
    Check that after removing the hook everything act normal

    https://tcms.engineering.redhat.com/case/287481/?from_plan=9940
    """
    __test__ = True
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG[4:5]
    hooks = {'after_disk_hotplug': [helpers.HOOKJPEG]}

    def perform_action(self):
        LOGGER.info("Activating new HW - %s", self.use_disks[0])

        vm_disks = vms.getVmDisks(self.vm_name)
        disk_names = [disk.get_name() for disk in vm_disks]

        LOGGER.info("Attached disks - %s", disk_names)
        if not self.use_disks[0] in disk_names:
            self.assertTrue(disks.attachDisk(True, self.use_disks[0],
                                             self.vm_name, False),
                            "Attaching disk %s to vm %s - fails"
                            % (self.use_disks[0], self.vm_name))

        self.assertTrue(
            vms.activateVmDisk(True, self.vm_name, self.use_disks[0]),
            "Activation of VM disk %s should have succeed" % self.use_disks[0])

        vms.deactivateVmDisk(True, self.vm_name, self.use_disks[0])

        self.clear_hooks()
        assert vms.activateVmDisk(True, self.vm_name, self.use_disks[0])

    def verify_hook_called(self):
        LOGGER.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @tcms(9940, 287481)
    def test_after_disk_hotplug_binary_executable_hook_file(self):
        """ check that activate succeed and hook fails if hook is binary
            executable file
        """
        self.perform_action_and_verify_hook_called()


@attr(tier=1)
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
        assert vms.activateVmDisk(True, self.vm_name, self.use_disks[0])
        assert vms.deactivateVmDisk(True, self.vm_name, self.use_disks[0])

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


@attr(tier=2)
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
        assert vms.activateVmDisk(True, self.vm_name, self.use_disks[0])
        assert vms.deactivateVmDisk(True, self.vm_name, self.use_disks[0])

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


@attr(tier=2)
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
            utils.restartVdsmd(self.host_address, self.password)

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            attach = executor.submit(
                vms.activateVmDisk, False, self.vm_name, self.use_disks[0])
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
        """Give vdsm time to restart and clean the environment"""
        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        hosts.waitForHostsStates(True, [self.host_name])
        super(TestCase286861, self).tearDown()


class BasePlugDiskTest(TestCase):

    __test__ = False
    template_name = config.TEMPLATE_NAME % TestCase.storage

    @classmethod
    def setup_class(cls):
        """
        Clone a vm of each supported OS type and wait for VM boot to complete
        """
        LOGGER.info("setup class %s" % cls.__name__)
        cls.disks = []
        cls.vm_names = []
        cls.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]

        def _create_and_start_vm():
            """
            Clones and starts a single vm from template
            """
            vm_name = common.create_vm_from_template(
                cls.template_name, cls.__name__, cls.storage_domain,
                cls.storage)
            LOGGER.info("Starting VM %s" % vm_name)
            vms.startVm(positive, vm=vm_name, wait_for_ip=True)
            LOGGER.info("VM %s started successfully" % vm_name)
            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            results.append(executor.submit(_create_and_start_vm))

        utils.raise_if_exception(results)

    @classmethod
    def teardown_class(cls):
        """
        Shuts down the vm and removes it
        """
        common.shutdown_and_remove_vms(cls.vm_names)
        delete_disks(filter(lambda w: disks.checkDiskExists(True, w),
                     cls.disks))


@attr(tier=1)
class TestCase231521(BasePlugDiskTest):
    """Activate/Deactivate an already attached disk
    on a running VM with support OS"""

    __test__ = True

    tcms_plan_id = '5291'
    tcms_test_case = '231521'

    @classmethod
    def setup_class(cls):
        """Create a VM with 2 disks extra disks - 1 active and 1 inactive"""
        super(TestCase231521, cls).setup_class()
        vms.stop_vms_safely(cls.vm_names)
        for vm_name in cls.vm_names:
            # add disk and deactivate it
            LOGGER.info("Adding 2 disks to VM %s" % vm_name)
            disk_args = {
                'positive': True,
                'size': 2 * config.GB,
                'sparse': True,
                'wipe_after_delete': cls.storage in config.BLOCK_TYPES,
                'storagedomain': cls.storage_domain,
                'bootable': False,
                'interface': ENUMS['interface_virtio'],
                'vm': vm_name,
            }

            # add 2 disks:
            for active in True, False:
                disk_alias = "%s_%s_Disk" % (vm_name, str(active))
                LOGGER.info("Adding disk to vm %s with %s active disk",
                            vm_name, "not" if not active else "")
                if not vms.addDisk(active=active, alias=disk_alias,
                                   **disk_args):
                    raise exceptions.DiskException("Unable to add disk to VM "
                                                   "%s" % vm_name)

                cls.disks.append(disk_alias)
            if not vms.startVm(positive, vm=vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_activate_disk(self):
        """Activate an already attached disk on a running VM"""
        for vm in self.vm_names:
            inactive_disks = [disk for disk in vms.getVmDisks(vm)
                              if not disk.get_bootable() and
                              not disk.get_active()]
            disk_name = inactive_disks[0].get_name()
            LOGGER.info("Activating disk %s on VM %s" % (disk_name, vm))
            status = vms.activateVmDisk(positive,
                                        vm=vm,
                                        diskAlias=disk_name)
            LOGGER.info("Finished activating disk %s" % disk_name)
            self.assertTrue(status)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_deactivate_disk(self):
        """Deactivate an already attached disk on a running VM"""
        for vm in self.vm_names:
            active_disks = [disk for disk in vms.getVmDisks(vm)
                            if not disk.get_bootable() and
                            disk.get_active()]
            disk_name = active_disks[0].get_name()
            LOGGER.info("Deactivating disk %s on VM %s" % (disk_name, vm))
            status = vms.deactivateVmDisk(positive,
                                          vm=vm,
                                          diskAlias=disk_name)
            LOGGER.info("Finished deactivating disk %s" % disk_name)
            self.assertTrue(status)


@attr(tier=1)
class TestCase139348(BasePlugDiskTest):
    """Hotplug floating disk (shareable and non-shareable)"""

    __test__ = True
    tcms_plan_id = '5291'
    tcms_test_case = '139348'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_floating_disk(self):
        """
        Hotplug floating disk (shareable/non-shareable) to vm
        """
        for disk_interface in DISK_INTERFACES:
            for shareable in (True, False):
                disk_name = config.DISK_NAME_FORMAT % (
                    disk_interface,
                    'shareable' if shareable else 'non-shareable',
                    self.storage)

                vm_name = self.vm_names[0]

                LOGGER.info("attempting to plug disk %s to vm %s" %
                            (disk_name, vm_name))
                status = disks.attachDisk(positive,
                                          alias=disk_name,
                                          vmName=vm_name)
                LOGGER.info("Plug disk status is %s" % status)
                self.assertTrue(status)


@attr(tier=1)
class TestCase244310(BasePlugDiskTest):
    """
    Plug shared disks into 2 VMs simultaneously
    """

    __test__ = True
    tcms_plan_id = '5291'
    tcms_test_case = '244310'

    @classmethod
    def setup_class(cls):
        """
        create 2 vms for each template and start them
        """
        super(TestCase244310, cls).setup_class()
        vms.stop_vms_safely(cls.vm_names)
        cls.vm_pairs = []

        def create_two_vms(vm_name):
            new_name = vm_name + "1"
            LOGGER.info("renaming vm %s to %s" % (vm_name, new_name))
            if not vms.updateVm(positive, vm=vm_name, name=new_name):
                raise exceptions.VMException("Unable to rename vm %s to %s" %
                                             (vm_name, new_name))
            vm_name = common.create_vm_from_template(
                cls.template_name, cls.__name__, cls.storage_domain,
                cls.storage)
            vm_pair = (vm_name, new_name)
            for vm in vm_pair:
                LOGGER.info("Starting vm %s" % vm)
                if not vms.startVm(positive, vm, wait_for_ip=True):
                    raise exceptions.VMException("Unable to start VM %s" % vm)
                LOGGER.info("VM %s started successfully" % vm)
            cls.vm_pairs.append(vm_pair)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for vm_name in cls.vm_names:
                results.append(executor.submit(create_two_vms,
                                               vm_name))
        utils.raise_if_exception(results)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_shared_disk_to_2_vms_same(self):
        """
        plug same disk into 2 vms simultaneously
        """
        for first_vm, second_vm in self.vm_pairs:
            LOGGER.info("VMs are: %s, %s" % (first_vm, second_vm))
            disk_name = config.DISK_NAME_FORMAT % (
                ENUMS['interface_virtio'],
                'shareable',
                self.storage,
            )
            LOGGER.info(
                "Plugging disk %s into vm %s (first vm)",
                disk_name,
                first_vm
            )
            first_plug_status = disks.attachDisk(positive,
                                                 alias=disk_name,
                                                 vmName=first_vm)
            LOGGER.info(
                "Plugging disk %s into vm %s (second vm)",
                disk_name,
                second_vm
            )
            second_plug_status = disks.attachDisk(positive,
                                                  alias=disk_name,
                                                  vmName=second_vm)
            self.assertTrue(first_plug_status and second_plug_status)

    @classmethod
    def teardown_class(cls):
        """
        remove and delete vms
        """
        for vm_pair in cls.vm_pairs:
            common.shutdown_and_remove_vms(vm_pair)


@attr(tier=1)
class TestCase244314(TestCase):
    """
    Unplug and detach shared disk from one of the vms
    """

    __test__ = True
    tcms_plan_id = '5291'
    tcms_test_case = '244314'
    template_name = config.TEMPLATE_NAME % TestCase.storage

    @classmethod
    def setup_class(cls):
        """
        create vm pair for each template, plug disk into vms and start them
        """
        cls.vm_pairs = []
        cls.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]

        disk_name = config.DISK_NAME_FORMAT % (
            ENUMS['interface_virtio'],
            'shareable',
            cls.storage,
        )
        vm_name = common.create_vm_from_template(
            cls.template_name, cls.__name__, cls.storage_domain, cls.storage)
        new_name = vm_name + "1"
        LOGGER.info("renaming vm %s to %s", vm_name, new_name)
        if not vms.updateVm(positive, vm=vm_name, name=new_name):
            raise exceptions.VMException("Unable to rename vm %s to %s" %
                                         (vm_name, new_name))
        vm_name = common.create_vm_from_template(
            cls.template_name, cls.__name__, cls.storage_domain, cls.storage)
        vm_pair = (vm_name, new_name)

        for vm in vm_pair:
            LOGGER.info("Plugging and activating disk %s to vm %s" %
                        (disk_name, vm))
            if not disks.attachDisk(positive, alias=disk_name, vmName=vm):
                raise exceptions.DiskException("Unable to plug %s to vm %s"
                                               % (disk_name, vm))
            LOGGER.info("Disk %s plugged to vm %s" % (disk_name, vm))
            LOGGER.info("Starting vm %s" % vm)
            if not vms.startVm(positive, vm, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm)
            LOGGER.info("VM %s started successfully" % vm)
            cls.vm_pairs.append(vm_pair)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_unplug_shared_disk(self):
        """
        Unplug shared disk from a single VM while it is still plugged to
        another vm
        """
        first_vm = self.vm_pairs[0][0]
        disk_name = config.DISK_NAME_FORMAT % (
            ENUMS['interface_virtio'],
            'shareable',
            self.storage,
        )
        LOGGER.info(
            "Unplugging disk %s from vm %s",
            disk_name,
            first_vm
        )
        unplug_status = vms.deactivateVmDisk(positive,
                                             diskAlias=disk_name,
                                             vm=first_vm)
        LOGGER.info("Disk %s unplugged from vm %s", disk_name, first_vm)
        self.assertTrue(unplug_status)

    @classmethod
    def teardown_class(cls):
        """
        Shutdown and remove vms created in test
        """
        for vm_pair in cls.vm_pairs:
            common.shutdown_and_remove_vms(vm_pair)


@attr(tier=0)
class TestCase174616(TestCase):
    """
    2 vms, 1 shareable disk attached to both of them.
    test check if hotplug works fine
    """
    __test__ = True

    tcms_plan_id = '6458'
    tcms_test_case = '174616'

    disk_count = 2
    first_vm = 'first'
    second_vm = 'second'
    template_name = config.TEMPLATE_NAME % TestCase.storage
    first_disk_name = 'non-shareable_virtio_disk'
    second_disk_name = 'shareable_virtio_disk'
    disks_aliases = [first_disk_name, second_disk_name]
    formats = [config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW]
    shareable = [False, True]
    interfaces = [config.VIRTIO, config.VIRTIO_SCSI]

    @classmethod
    def setup_class(cls):
        """
        Create 2 VMs, 2 virtio disks and one of them is shareable
        """
        cls.vm_names = []
        cls.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        cls.first_vm = common.create_vm_from_template(
            cls.template_name, cls.first_vm, cls.storage_domain, cls.storage)

        # add disk and attach it
        LOGGER.info("Adding 2 disks to VM %s" % cls.first_vm)

        for index in range(cls.disk_count):
            disk_args = {
                'positive': True,
                'alias': cls.disks_aliases[index],
                'provisioned_size': 3 * config.GB,
                'format': cls.formats[index],
                'sparse': True,
                'wipe_after_delete': cls.storage in config.BLOCK_TYPES,
                'storagedomain': cls.storage_domain,
                'bootable': False,
                'interface': cls.interfaces[index],
                'shareable': cls.shareable[index],
            }
            if cls.storage == config.ENUMS['storage_type_iscsi'] \
                    and disk_args['format'] == ENUMS['format_raw']:
                disk_args['sparse'] = False

            LOGGER.info("Adding %s disk...", cls.disks_aliases[index])
            if not disks.addDisk(**disk_args):
                raise exceptions.DiskException("Unable to add disk %s"
                                               % cls.disks_aliases[index])
            wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                           config.DATA_CENTER_NAME)

            if not disks.attachDisk(positive, alias=cls.disks_aliases[index],
                                    vmName=cls.first_vm, active=False):

                raise exceptions.DiskException("Unable to plug %s to vm %s"
                                               % (cls.disks_aliases[index],
                                                  cls.first_vm))
            LOGGER.info("%s disk added successfully", cls.disks_aliases[index])

        cls.second_vm = common.create_vm_from_template(
            cls.template_name, cls.second_vm, cls.storage_domain, cls.storage)

        if not disks.attachDisk(positive, alias=cls.second_disk_name,
                                vmName=cls.second_vm, active=False):
                raise exceptions.DiskException("Unable to plug %s to vm %s"
                                               % (cls.second_disk_name,
                                                  cls.second_vm))
        cls.vm_names = [cls.first_vm, cls.second_vm]

        vms.stop_vms_safely(cls.vm_names)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_deactivate_and_activate_disk(self):
        """
            Deactivate an already attached disk on a running VM
            and then Activate them
        """
        for vm in self.vm_names:

            self.assertTrue(vms.startVm(True, vm),
                            "Unable to start vms")

        for vm in self.vm_names:
            active_disks = [disk for disk in vms.getVmDisks(vm)
                            if not disk.get_bootable() and
                            disk.get_active()]
            if len(active_disks) > 0:
                disk_name = active_disks[0].get_name()
                LOGGER.info("Deactivating disk %s on VM %s" % (disk_name, vm))
                status = vms.deactivateVmDisk(positive,
                                              vm=vm,
                                              diskAlias=disk_name)
                LOGGER.info("Finished deactivating disk %s" % disk_name)
                self.assertTrue(status)

        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)

        for vm in self.vm_names:
            inactive_disks = [disk for disk in vms.getVmDisks(vm)
                              if not disk.get_bootable() and
                              not disk.get_active()]
            if len(inactive_disks) > 0:
                for disk in inactive_disks:
                    disk_name = disk.get_name()
                    LOGGER.info("Activating disk %s on VM %s"
                                % (disk_name, vm))
                    vms.wait_for_vm_states(vm, [config.VM_UP])
                    status = vms.activateVmDisk(positive,
                                                vm=vm,
                                                diskAlias=disk_name)
                    LOGGER.info("Finished activating disk %s" % disk_name)
                    self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        Remove all vms and disks created during the test
        """
        LOGGER.info("Removing vms %s", cls.vm_names)
        common.shutdown_and_remove_vms(cls.vm_names)

        LOGGER.info("Removing disks  %s", cls.disks_aliases)
        for disk_alias in cls.disks_aliases:
            assert disks.deleteDisk(True, disk_alias)
