"""
Hotplug full test plan
"""

import logging
from concurrent.futures import ThreadPoolExecutor
import time

from art.test_handler.tools import bz, tcms

from art.rhevm_api.utils import test_utils as utils
import art.test_handler.exceptions as exceptions
from art.test_handler.settings import opts
from art.rhevm_api.utils.test_utils import get_api, wait_for_tasks

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter


from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import vms, disks, storagedomains


import config
import helpers
import common
from art.unittest_lib import StorageTest as TestCase

LOGGER = logging.getLogger(__name__)

FILE_WITH_RESULTS = helpers.FILE_WITH_RESULTS
VM_NAME = helpers.VM_NAME
DISKS_TO_PLUG = helpers.DISKS_TO_PLUG
UNATTACHED_DISK = helpers.UNATTACHED_DISK
TEXT = helpers.TEXT
ENUMS = opts['elements_conf']['RHEVM Enums']

DISK_INTERFACES = (ENUMS['interface_virtio'],)

VM_NAME_FORMAT = "%s-%sVM"

DISK_NAME_FORMAT = '%s_%s_%s_disk'
positive = True


def setup_module():
    """
    Create VM templates with different OSs and all disk type combinations
    """
    LOGGER.info("setup_module")
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE, basename=config.BASENAME)

    helpers.create_local_files_with_hooks()
    helpers.create_vm_with_disks()

    disk_results = common.start_creating_disks_for_test()

    vm_results = common.start_installing_vms_for_test()

    LOGGER.info("Ensuring all disks were created successfully")
    for result in disk_results:
        exception = result.exception()
        if exception is not None:
            raise exception
        status, diskIdDict = result.result()
        if not status:
            raise exceptions.DiskException("Unable to create disk")
    LOGGER.info("All disks created successfully")
    LOGGER.info("Waiting for vms to be installed and templates to be created")

    vdc = config.VDC
    vdc_password = config.VDC_PASSWORD
    dc_name = config.DEFAULT_DATA_CENTER_NAME
    if vdc is not None and vdc_password is not None:
        LOGGER.info("Waiting for vms to be installed and "
                    "templates to be created")
        wait_for_tasks(
            vdc=vdc, vdc_password=vdc_password, datacenter=dc_name)
    for result in vm_results:
        exception = result.exception()
        if exception is not None:
            raise exception
    LOGGER.info("All templates created successfully")
    LOGGER.info("Package setup successfully")


def teardown_module():
    """
    clean setup
    """
    LOGGER.info("Teardown module")

    helpers.remove_hook_files()

    cleanDataCenter(
        True, config.DEFAULT_DATA_CENTER_NAME, vdc=config.VDC,
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
    active_disk = False
    action = [vms.activateVmDisk]
    use_disks = DISKS_TO_PLUG
    hooks = {'after_disk_hotplug': [helpers.HOOKWITHSLEEPFILENAME]}

    @bz(1003649, 991742)
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

    @bz(1003649, 991742)
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
        if ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME):
            vm_disks = vms.getVmDisks(VM_NAME)
            disk_names = [disk.get_name() for disk in vm_disks]
            if not self.use_disks[0] in disk_names:
                self.assertTrue(disks.attachDisk(True,
                                                 self.use_disks[0],
                                                 VM_NAME),
                                "Failed to attach disk %s to vm %s"
                                % (self.use_disks[0], VM_NAME))

    def put_disks_in_correct_state(self):
        pass

    @tcms(9940, 287249)
    def test_before_disk_hotplug_attaching_new_disk(self):
        """ Check if after_disk_hotunplug is called
        """
        self.perform_action_and_verify_hook_called()

    def tearDown(self):
        super(self.__class__, self).tearDown()
        vm_disks = vms.getVmDisks(VM_NAME)
        disk_names = [disk.get_name() for disk in vm_disks]
        if self.use_disks[0] in disk_names:
            disks.detachDisk(True, self.use_disks[0], VM_NAME)


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

        vm_disks = vms.getVmDisks(VM_NAME)
        disk_names = [disk.get_name() for disk in vm_disks]

        LOGGER.info("Attached disks - %s", disk_names)
        if not self.use_disks[0] in disk_names:
            self.assertTrue(disks.attachDisk(True, self.use_disks[0],
                                             VM_NAME, False),
                            "Attaching disk %s to vm %s - fails"
                            % (self.use_disks[0], VM_NAME))

        self.assertTrue(vms.activateVmDisk(True, VM_NAME, self.use_disks[0]),
                        "Activation of VM disk %s should have succeed"
                        % self.use_disks[0])

        vms.deactivateVmDisk(True, VM_NAME, self.use_disks[0])

        self.clear_hooks()
        assert vms.activateVmDisk(True, VM_NAME, self.use_disks[0])

    def verify_hook_called(self):
        LOGGER.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @tcms(9940, 287481)
    @bz(1015171)
    def test_after_disk_hotplug_binary_executable_hook_file(self):
        """ check that activate succeed and hook fails if hook is binary
            executable file
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
            utils.restartVdsmd(self.address, self.password)

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
        super(self.__class__, self).tearDown()


class TestCase134134(TestCase):
    """Plug in disk while OS is running (virtIO on supported OS type only)"""

    __test__ = True

    vm_names = []
    tcms_plan_id = '5291'
    tcms_test_case = '134134'

    @classmethod
    def setup_class(cls):
        """
        Clone a vm of each supported OS type and wait for VM boot to complete
        """
        LOGGER.info("setup class %s" % cls.__name__)

        def _create_and_start_vm(template):
            """
            Clones and starts a single vm from template
            """
            vm_name = common.create_vm_from_template(template, cls.__name__)
            LOGGER.info("Starting VM %s" % vm_name)
            vms.startVm(positive, vm=vm_name, wait_for_ip=True)
            LOGGER.info("VM %s started successfully" % vm_name)
            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_and_start_vm, template))

        utils.raise_if_exception(results)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_virtio_disk(self):
        """
        Try to plug in a new virtIO disk while OS is running
        """
        for template in config.TEMPLATE_NAMES:
            vm_name = VM_NAME_FORMAT % (template, self.__class__.__name__)
            disk_name = DISK_NAME_FORMAT % (
                template, ENUMS["interface_virtio"], "shareable")
            LOGGER.info("Attempting to hotplug disk %s to VM %s" %
                        (disk_name, vm_name))
            status = disks.attachDisk(positive,
                                      alias=disk_name,
                                      vmName=vm_name,
                                      active=True)
            LOGGER.info('Done')
            self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        Shuts down the vm and removes it
        """
        common.shutdown_and_remove_vms(cls.vm_names)


class TestCase134139(TestCase):
    """Unplug a disk and detach it. Tested as 2 independent functions"""
    __test__ = True

    vm_names = []
    tcms_plan_id = '5291'
    tcms_test_case = '134139'

    @classmethod
    def setup_class(cls):
        """
        Clone VMs, one for each template and create 2 additional disks
        for each vm - one should be active and the other inactive
        """
        def _create_vm_and_disks(template):
            """
            Creates a single vm and adds 2 disks to it, deactivating
            one of the additional disks
            """
            vm_name = common.create_vm_from_template(template, cls.__name__)
            LOGGER.info("Adding 2 disks to VM %s" % vm_name)

            disk_args = {
                'positive': True,
                'size': 2 * config.GB,
                'sparse': True,
                'wipe_after_delete': config.BLOCK_FS,
                'storagedomain': config.STORAGE_DOMAIN_NAME,
                'bootable': False,
                'interface': ENUMS['interface_virtio'],
                'vm': vm_name,
            }

            # add 2 disks:
            for active in True, False:
                LOGGER.info("Adding disk to vm %s with %s active disk",
                            vm_name, "not" if not active else "")
                if not vms.addDisk(active=active, **disk_args):
                    raise exceptions.DiskException("Unable to add disk to VM "
                                                   "%s" % vm_name)

            if not vms.startVm(positive, vm=vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)

            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vm_and_disks, template))

        utils.raise_if_exception(results)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_unplug_disk(self):
        """
        Attempt to unplug (deactivate) active disk from a VM with OS running
        """
        for vm in self.vm_names:
            LOGGER.info("Getting active non-bootable disks for vm %s" % vm)
            active_disks = [disk for disk in vms.getVmDisks(vm) if
                            disk.get_active() and not disk.get_bootable()]
            LOGGER.info("Unplugging disk %s from vm %s" %
                        (active_disks[0].get_name(), vm))
            result = vms.deactivateVmDisk(positive,
                                          vm=vm,
                                          diskAlias=active_disks[0].get_name(),
                                          wait=True)
            LOGGER.info("Done unplugging disk")
            self.assertTrue(result)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_detach_disk(self):
        """
        Attempt to detach inactive disk from a VM with OS running
        """
        for vm in self.vm_names:
            LOGGER.info("Getting inactive non-bootable disks for vm %s" % vm)
            inactive_disks = [disk for disk in vms.getVmDisks(vm) if
                              not disk.get_active()]
            LOGGER.info("Detaching disk %s from vm %s" %
                        (inactive_disks[0].get_alias(), vm))
            self.assertTrue(disks.detachDisk(positive,
                            alias=inactive_disks[0].get_alias(),
                            vmName=vm))
            LOGGER.info("Done detaching disk %s from vm %s" %
                        (inactive_disks[0].get_alias(), vm))

    @classmethod
    def teardown_class(cls):
        """
        Shutdown all vms, forcefully if needed, and remove them
        """
        common.shutdown_and_remove_vms(cls.vm_names)


class TestCase231521(TestCase):
    """Activate/Deactivate an already attached disk
    on a running VM with support OS"""

    __test__ = True

    vm_names = []
    tcms_plan_id = '5291'
    tcms_test_case = '231521'

    @classmethod
    def setup_class(cls):
        """Create a VM with 2 disks extra disks - 1 active and 1 inactive"""
        def _create_vm_and_disks(template):
            vm_name = common.create_vm_from_template(template, cls.__name__)

            # add disk and deactivate it
            LOGGER.info("Adding 2 disks to VM %s" % vm_name)
            disk_args = {
                'positive': True,
                'size': 2 * config.GB,
                'sparse': True,
                'wipe_after_delete': config.BLOCK_FS,
                'storagedomain': config.STORAGE_DOMAIN_NAME,
                'bootable': False,
                'interface': ENUMS['interface_virtio'],
                'vm': vm_name,
            }

            # add 2 disks:
            for active in True, False:
                LOGGER.info("Adding disk to vm %s with %s active disk",
                            vm_name, "not" if not active else "")
                if not vms.addDisk(active=active, **disk_args):
                    raise exceptions.DiskException("Unable to add disk to VM "
                                                   "%s" % vm_name)

            if not vms.startVm(positive, vm=vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)

            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vm_and_disks, template))

        utils.raise_if_exception(results)

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

    @classmethod
    def teardown_class(cls):
        """
        remove all vms created during the test
        """
        common.shutdown_and_remove_vms(cls.vm_names)


class TestCase139348(TestCase):
    """Hotplug floating disk (shareable and non-shareable)"""

    __test__ = True
    tcms_plan_id = '5291'
    tcms_test_case = '139348'

    vm_names = []

    @classmethod
    def setup_class(cls):
        """
        Clone and start vm for test
        """
        def _create_and_start_vm(template):
            vm_name = common.create_vm_from_template(template, cls.__name__)
            LOGGER.info("Starting vm %s" % vm_name)
            if not vms.startVm(positive, vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)
            LOGGER.info("VM %s started successfully" % vm_name)
            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_and_start_vm, template))

        utils.raise_if_exception(results)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_floating_disk(self):
        """
        Hotplug floating disk (shareable/non-shareable) to vm
        """
        for template in config.TEMPLATE_NAMES:
            for disk_interface in DISK_INTERFACES:
                for shareable in (True, False):
                    disk_name = DISK_NAME_FORMAT % (
                        template,
                        disk_interface,
                        'shareable' if shareable else 'non-shareable')

                    vm_name = VM_NAME_FORMAT % (template,
                                                self.__class__.__name__)

                    LOGGER.info("attempting to plug disk %s to vm %s" %
                                (disk_name, vm_name))
                    status = disks.attachDisk(positive,
                                              alias=disk_name,
                                              vmName=vm_name)
                    LOGGER.info("Done - status is %s" % status)
                    self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        remove vm and disk
        """
        common.shutdown_and_remove_vms(cls.vm_names)


class TestCase244310(TestCase):
    """
    Plug shared disks into 2 VMs simultaneously
    """

    __test__ = True
    tcms_plan_id = '5291'
    tcms_test_case = '244310'

    vm_pairs = []

    @classmethod
    def setup_class(cls):
        """
        create 2 vms for each template and start them
        """
        def _create_vms_and_disks(template):
            vm_name = common.create_vm_from_template(template, cls.__name__)
            new_name = vm_name + "1"
            LOGGER.info("renaming vm %s to %s" % (vm_name, new_name))
            if not vms.updateVm(positive, vm=vm_name, name=new_name):
                raise exceptions.VMException("Unable to rename vm %s to %s" %
                                             (vm_name, new_name))
            vm_name = common.create_vm_from_template(template, cls.__name__)
            vm_pair = (vm_name, new_name)
            for vm in vm_pair:
                LOGGER.info("Starting vm %s" % vm)
                if not vms.startVm(positive, vm, wait_for_ip=True):
                    raise exceptions.VMException("Unable to start VM %s" % vm)
                LOGGER.info("VM %s started successfully" % vm)
            cls.vm_pairs.append(vm_pair)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vms_and_disks,
                                               template))

        utils.raise_if_exception(results)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_shared_disk_to_2_vms_same(self):
        """
        plug same disk into 2 vms simultaneously
        """
        for (first_vm, second_vm), template in zip(self.vm_pairs,
                                                   config.TEMPLATE_NAMES):
            LOGGER.info("VMs are: %s, %s" % (first_vm, second_vm))
            disk_name = DISK_NAME_FORMAT % (template,
                                            ENUMS['interface_virtio'],
                                            'shareable')
            LOGGER.info("Plugging disk %s into vm %s (first vm)" %
                        (disk_name, first_vm))
            first_plug_status = disks.attachDisk(positive,
                                                 alias=disk_name,
                                                 vmName=first_vm)
            LOGGER.info("Plugging disk %s into vm %s (second vm)" %
                        (disk_name, second_vm))
            second_plug_status = disks.attachDisk(positive,
                                                  alias=disk_name,
                                                  vmName=second_vm)
            self.assertTrue(first_plug_status and second_plug_status)

    @classmethod
    def teardown_class(cls):
        """
        remove and delete vms
        """
        for _ in xrange(len(cls.vm_pairs)):
            vm_pair = cls.vm_pair.pop()
            common.shutdown_and_remove_vms(vm_pair)


class TestCase244314(TestCase):
    """
    Unplug and detach shared disk from one of the vms
    """

    __test__ = True
    tcms_plan_id = '5291'
    tcms_test_case = '244314'

    vm_pairs = []

    @classmethod
    def setup_class(cls):
        """
        create vm pair for each template, plug disk into vms and start them
        """
        def _create_vms_and_disks(template):
            disk_name = DISK_NAME_FORMAT % (template,
                                            ENUMS['interface_virtio'],
                                            'shareable')
            vm_name = common.create_vm_from_template(template, cls.__name__)
            new_name = vm_name + "1"
            LOGGER.info("renaming vm %s to %s" % (vm_name, new_name))
            if not vms.updateVm(positive, vm=vm_name, name=new_name):
                raise exceptions.VMException("Unable to rename vm %s to %s" %
                                            (vm_name, new_name))
            vm_name = common.create_vm_from_template(template, cls.__name__)
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

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vms_and_disks,
                                               template))

        utils.raise_if_exception(results)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_unplug_shared_disk(self):
        """
        Unplug shared disk from a single VM while it is still plugged to
        another vm
        """
        for (first_vm, second_vm), template in zip(self.vm_pairs,
                                                   config.TEMPLATE_NAMES):
            disk_name = DISK_NAME_FORMAT % (template,
                                            ENUMS['interface_virtio'],
                                            'shareable')
            LOGGER.info("Unplugging disk %s from vm %s" %
                        (disk_name, first_vm))
            unplug_status = vms.deactivateVmDisk(positive,
                                                 diskAlias=disk_name,
                                                 vm=first_vm)
            LOGGER.info("Disk %s unplugged from vm %s" % (disk_name, first_vm))
            self.assertTrue(unplug_status)

    @classmethod
    def teardown_class(cls):
        """
        Shutdown and remove vms created in test
        """
        for _ in xrange(len(cls.vm_pairs)):
            vm_pair = cls.vm_pairs.pop()
            common.shutdown_and_remove_vms(vm_pair)


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
    vm_names = list()
    template = config.TEMPLATE_NAMES[0]
    first_disk_name = 'non-shareable_virtio_disk'
    second_disk_name = 'shareable_virtio_disk'
    disks_aliases = [first_disk_name, second_disk_name]
    formats = [ENUMS['format_cow'], ENUMS['format_raw']]
    shareable = [False, True]

    @classmethod
    def setup_class(cls):
        """
        Create 2 VMs, 2 virtio disks and one of them is shareable
        """
        cls.first_vm = common.create_vm_from_template(cls.template,
                                                      cls.first_vm)

        # add disk and attach it
        LOGGER.info("Adding 2 disks to VM %s" % cls.first_vm)

        for index in range(cls.disk_count):
            disk_args = {
                'positive': True,
                'alias': cls.disks_aliases[index],
                'provisioned_size': 3 * config.GB,
                'format': cls.formats[index],
                'sparse': True,
                'wipe_after_delete': config.BLOCK_FS,
                'storagedomain': config.STORAGE_DOMAIN_NAME,
                'bootable': False,
                'interface': ENUMS['interface_virtio'],
                'shareable': cls.shareable[index],
            }
            if config.STORAGE_TYPE == config.ENUMS['storage_type_iscsi'] \
                    and disk_args['format'] == ENUMS['format_raw']:
                disk_args['sparse'] = False

            LOGGER.info("Adding %s disk...", cls.disks_aliases[index])
            if not disks.addDisk(**disk_args):
                raise exceptions.DiskException("Unable to add disk %s"
                                               % cls.disks_aliases[index])
            wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                           config.DEFAULT_DATA_CENTER_NAME)

            if not disks.attachDisk(positive, alias=cls.disks_aliases[index],
                                    vmName=cls.first_vm, active=False):

                raise exceptions.DiskException("Unable to plug %s to vm %s"
                                               % (cls.disks_aliases[index],
                                                  cls.first_vm))
            LOGGER.info("%s disk added successfully", cls.disks_aliases[index])

        cls.second_vm = common.create_vm_from_template(cls.template,
                                                       cls.second_vm)

        if not disks.attachDisk(positive, alias=cls.second_disk_name,
                                vmName=cls.second_vm, active=False):
                raise exceptions.DiskException("Unable to plug %s to vm %s"
                                               % (cls.second_disk_name,
                                                  cls.second_vm))
        cls.vm_names = [cls.first_vm, cls.second_vm]

        for vm in cls.vm_names:
            if not vms.get_vm_state(vm) == ENUMS['vm_state_down']:
                if not vms.stopVm(True, vm):
                    raise exceptions.VMException("Unable to stop vms %s",
                                                 cls.vm_names)

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
                       config.DEFAULT_DATA_CENTER_NAME)

        for vm in self.vm_names:
            inactive_disks = [disk for disk in vms.getVmDisks(vm)
                              if not disk.get_bootable() and
                              not disk.get_active()]
            if len(inactive_disks) > 0:
                for disk in inactive_disks:
                    disk_name = disk.get_name()
                    LOGGER.info("Activating disk %s on VM %s"
                                % (disk_name, vm))
                    vms.wait_for_vm_states(vm, [ENUMS['vm_state_up']])
                    status = vms.activateVmDisk(positive,
                                                vm=vm,
                                                diskAlias=disk_name)
                    LOGGER.info("Finished activating disk %s" % disk_name)
                    self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        remove all vms created during the test
        """
        common.shutdown_and_remove_vms(cls.vm_names)
