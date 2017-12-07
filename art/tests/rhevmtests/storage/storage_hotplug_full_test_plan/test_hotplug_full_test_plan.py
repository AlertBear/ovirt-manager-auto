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
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils as utils
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion, bz
from rhevmtests.storage.storage_hotplug_full_test_plan.fixtures import (
    initializer_hotplug_hook, wait_for_dc_and_hosts,
    add_disks_to_vm, add_floating_disks, create_second_vm, remove_vm_disk,
    attach_floating_disks_to_vm, set_disks_in_the_correct_state, install_hooks,
    create_results_files,
)
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    create_vm, add_disk, delete_disks, start_vm
)
from rhevmtests.storage.fixtures import remove_vm  # noqa


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

DISK_INTERFACES = (ENUMS['interface_virtio'],)


@pytest.fixture(scope='module', autouse=True)
def initializer_module(request):
    """
    Create VM templates with various disk type combinations
    """
    def finalizer_module():
        """
        clean setup
        """
        helpers.remove_hook_files()
        vms_to_remove = config.VM_NAMES.values()
        testflow.teardown("Remove VMs %s", vms_to_remove)
        assert ll_vms.safely_remove_vms(vms_to_remove), (
            "Failed to remove VMs %s" % vms_to_remove
        )
        testflow.teardown("Removing all floating disks")
        for disks in config.UNATTACHED_DISKS_PER_STORAGE_TYPE.values():
            hl_disks.delete_disks(disks)

    request.addfinalizer(finalizer_module)
    helpers.create_local_files_with_hooks()
    testflow.setup("Add VM with 7 disks")
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        config.VM_NAMES[storage_type] = (
            helpers.create_vm_with_disks(storage_domain, storage_type)
        )
        utils.wait_for_tasks(
            engine=config.ENGINE, datacenter=config.DATA_CENTER_NAME
        )


@pytest.mark.usefixtures(
    initializer_hotplug_hook.__name__,
    create_results_files.__name__,
    set_disks_in_the_correct_state.__name__,
    install_hooks.__name__
)
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

    def get_hooks_result_file(self):
        """ Reads hook result file """
        _, tmpfile = tempfile.mkstemp()
        logger.info("temp: %s" % tmpfile)
        try:
            assert self.host_resource.fs.transfer(
                path_src=config.FILE_WITH_RESULTS,
                target_host=config.SLAVE_HOST,
                path_dst=tmpfile
            )
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
            assert future.result(), "Failed to perform action %s on %s" % (
                self.action[0].__name__, disk_name)

    def perform_action_and_verify_hook_called(self):
        """
        Calls defined action (activate/deactivate disk) and checks if hooks
        were called
        """
        testflow.step("Performing hotplug/hot-unplug action on disk")
        self.perform_action()
        testflow.step(
            "Verifying relevant hook '%s' was called", self.hooks.keys()[0]
        )
        self.verify_hook_called()


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
    @tier2
    def test_before_disk_hotplug(self):
        """
        Check if before_disk_hotplug is called
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][0:1]
        self.perform_action_and_verify_hook_called()


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
    @tier2
    def test_after_disk_hotplug(self):
        """
        Check if after_disk_hotplug is called
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][1:2]
        self.perform_action_and_verify_hook_called()


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
    @tier2
    def test_before_disk_hotunplug(self):
        """
        Check if before_disk_hotunplug is called
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][2:3]
        self.perform_action_and_verify_hook_called()


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
    @tier2
    def test_after_disk_hotunplug(self):
        """
        Check if after_disk_hotunplug is called
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][3:4]
        self.perform_action_and_verify_hook_called()


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
    @tier3
    def test_after_disk_hotplug_5_disks_concurrently(self):
        """
        Try to hotplug 7 tests concurrently and check that all hooks were
        called
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage]
        self.perform_action_and_verify_hook_called()

    def verify_hook_called(self):
        result = self.get_hooks_result_file()
        logger.info(
            "Hook should have been called %s times", len(
                config.DISKS_TO_PLUG[self.storage]
            )
        )
        assert len(result) == len(config.DISKS_TO_PLUG[self.storage]), result


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
    @tier3
    def test_after_disk_hotunplug_5_disks_concurrently(self):
        """
        Concurrently unplug 7 disks and check if after_unplug hook were
        called 7 times
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage]
        self.perform_action_and_verify_hook_called()

    def verify_hook_called(self):
        result = self.get_hooks_result_file()
        logger.info(
            "Hook should have been called %s times", len(
                config.DISKS_TO_PLUG[self.storage]
            )
        )
        assert len(result) == len(config.DISKS_TO_PLUG[self.storage]), result


@pytest.mark.usefixtures(
    add_disk.__name__,
    remove_vm_disk.__name__
)
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
    activate_or_deactivate_disks = False

    def perform_action(self):
        if ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME):
            testflow.step(
                "Attach disk: %s to %s", self.disk_name, self.vm_name
            )
            assert ll_disks.attachDisk(True, self.disk_name, self.vm_name), (
                "Failed to attach disk %s to VM %s" % (
                    self.disk_name, self.vm_name
                )
            )

    @polarion("RHEVM3-5039")
    @tier3
    def test_before_disk_hotplug_attaching_new_disk(self):
        """
        Check if after_disk_hotunplug is called
        """
        self.use_disks = config.UNATTACHED_DISKS_PER_STORAGE_TYPE[self.storage]
        self.perform_action_and_verify_hook_called()


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

        testflow.step(
            "Attach disk: %s to %s", self.use_disks[0], self.vm_name
        )
        if not self.use_disks[0] in disk_names:
            assert ll_disks.attachDisk(
                True, self.use_disks[0], self.vm_name, False
            ), "Failed to attach disk %s to vm %s" % (
                self.use_disks[0], self.vm_name
            )
        testflow.step("Activate disk %s", self.use_disks[0])
        assert ll_vms.activateVmDisk(
            True, self.vm_name, self.use_disks[0]
        ), "Activation of VM disk %s should have succeed" % self.use_disks[0]

        testflow.step("Deactivete disk %s", self.use_disks[0])
        assert ll_vms.deactivateVmDisk(
            True, self.vm_name, self.use_disks[0]), (
            "Failed to deactivate disk %s" % self.use_disks[0]
        )

        helpers.clear_hooks(self.executor)
        assert ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0]), (
            "Failed to activate disk %s" % self.use_disks[0]
        )

    def verify_hook_called(self):
        logger.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @polarion("RHEVM3-5044")
    @tier3
    def test_after_disk_hotplug_binary_executable_hook_file(self):
        """
        Check that activate succeed and hook fails if hook is binary
        executable file
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][4:5]
        self.perform_action_and_verify_hook_called()


@bz({'1469235': {}})
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
    non_executable_hook = True

    def perform_action(self):
        assert ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0]), (
            "Failed to activate disk %s" % self.use_disks[0]
        )
        assert ll_vms.deactivateVmDisk(
            True, self.vm_name, self.use_disks[0]
        ), "Failed to deactivate disk %s" % self.use_disks[0]

    def verify_hook_called(self):
        logger.info("Hooks shouldn't have been called")
        assert not self.get_hooks_result_file()

    @polarion("RHEVM3-5041")
    @tier2
    def test_non_executable_hooks(self):
        """
        Check that vdsm skips a hook file if it is non-executable
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][5:6]
        self.perform_action_and_verify_hook_called()


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
        assert ll_vms.activateVmDisk(True, self.vm_name, self.use_disks[0]), (
            "Failed to activate disk %s" % self.use_disks[0]
        )
        assert ll_vms.deactivateVmDisk(
            True, self.vm_name, self.use_disks[0]
        ), "Failed to deactivate disk %s" % self.use_disks[0]

    def verify_hook_called(self):
        logger.info("Verifying hook files")
        result = self.get_hooks_result_file()
        assert len(result) == 4, "There should have been 4 hooks called"
        assert len(
            [x for x in result if x.strip() == config.TEXT]
        ) == 2, "'%s' should have appeared twice" % config.TEXT

    @polarion("RHEVM3-5040")
    @tier3
    def test_multiple_hooks(self):
        """
        Multiple hooks for one action, checks that all will be called
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][6:7]
        self.perform_action_and_verify_hook_called()


@pytest.mark.usefixtures(
    wait_for_dc_and_hosts.__name__
)
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

    def perform_action(self):
        def func():
            testflow.step("Restart VDSM for host: %s", self.host_address)
            time.sleep(5)
            utils.restartVdsmd(self.host_address, self.password)

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            attach = executor.submit(
                ll_vms.activateVmDisk, False, self.vm_name, self.use_disks[0]
            )
            executor.submit(func)

        assert attach.result(), "Activate should have failed"

    def verify_hook_called(self):
        logger.info("File should be empty")
        assert not self.get_hooks_result_file()

    @polarion("RHEVM3-5042")
    @tier4
    def test_multiple_hooks(self):
        """
        Restart VDSM during before_disk_hotplug, action should fail
        """
        self.use_disks = config.DISKS_TO_PLUG[self.storage][7:8]
        self.perform_action_and_verify_hook_called()


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks_to_vm.__name__,
    start_vm.__name__
)
class TestCase6231(TestCase):
    """
    Activate/Deactivate an already attached disk on a running VM with
    supported OS
    """
    __test__ = True

    polarion_test_case = '6231'
    interfaces = [config.VIRTIO, config.VIRTIO_SCSI]

    @polarion("RHEVM3-6231")
    @bz({'1506677': {'storage': ['glusterfs']}})
    @tier1
    def test_activate_deactivate_disk(self):
        """
        Activate an already attached disk on a running VM
        """
        inactive_disks = [
            disk for disk in ll_vms.getVmDisks(self.vm_name) if not
            ll_vms.is_bootable_disk(self.vm_name, disk.get_id()) and not
            ll_vms.is_active_disk(self.vm_name, disk.get_id())
        ]
        disk_name = inactive_disks[0].get_name()
        testflow.step("Hot plug disk %s to VM %s", disk_name, self.vm_name)
        assert ll_vms.activateVmDisk(True, self.vm_name, disk_name), (
            "Failed to activate disk %s" % disk_name
        )

        active_disks = [
            disk for disk in ll_vms.getVmDisks(self.vm_name) if not
            ll_vms.is_bootable_disk(self.vm_name, disk.get_id()) and
            ll_vms.is_active_disk(self.vm_name, disk.get_id())
        ]
        disk_name = active_disks[0].get_name()
        testflow.step(
            "Hot unplug disk %s to VM %s", disk_name, self.vm_name
        )
        assert ll_vms.deactivateVmDisk(True, self.vm_name, disk_name), (
            "Failed to deactivate disk %s" % disk_name
        )


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_vm.__name__,
    add_floating_disks.__name__,
    start_vm.__name__
)
class TestCase6243(TestCase):
    """
    Hotplug floating disk (shareable and non-shareable)
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '6243'
    interfaces = DISK_INTERFACES

    @polarion("RHEVM3-6243")
    @tier3
    def test_plug_floating_disk(self):
        """
        Hotplug floating disk (shareable/non-shareable) to a VM
        """
        for disk_alias in self.disk_aliases:
            testflow.step(
                "Hotplug disk %s to VM %s", disk_alias, self.vm_name
            )
            assert ll_disks.attachDisk(
                True, disk_alias, self.vm_name, active=True
            ), "Failed to attach disk %s to VM %s" % (disk_alias, self.vm_name)


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_vm.__name__,
    create_second_vm.__name__,
    add_floating_disks.__name__,
    attach_floating_disks_to_vm.__name__,
)
class TestCase6230(TestCase):
    """
    2 VMS, 2 shareable disks attached to both of them one VIRTIO and the other
    VIRTIO-SCSI, ensure hotplug/hot-unplug works
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])

    polarion_test_case = '6230'

    interfaces = [config.VIRTIO, config.VIRTIO_SCSI]

    @polarion("RHEVM3-6230")
    @tier3
    def test_deactivate_and_activate_disk(self):
        """
        Deactivate an already attached disks on a running VM and then
        activates it
        """
        vm_names = [self.vm_name, self.vm_name_2]
        for vm in vm_names:
            assert ll_vms.startVm(True, vm, wait_for_status=config.VM_UP), (
                "Unable to power on VM '%s'" % vm
            )

        for vm in vm_names:
            active_disks = [
                disk for disk in ll_vms.getVmDisks(vm) if not
                ll_vms.is_bootable_disk(vm, disk.get_id()) and
                ll_vms.is_active_disk(vm, disk.get_id())
            ]
            for disk in active_disks:
                disk_name = disk.get_name()
                testflow.step("Deactivating disk %s on VM %s", disk_name, vm)
                assert ll_vms.deactivateVmDisk(True, vm, disk_name), (
                    "Failed to deactivate disk %s" % disk_name
                )
        utils.wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        for vm in vm_names:
            inactive_disks = [
                disk for disk in ll_vms.getVmDisks(vm) if not
                ll_vms.is_bootable_disk(vm, disk.get_id()) and not
                ll_vms.is_active_disk(vm, disk.get_id())
            ]
            for disk in inactive_disks:
                disk_name = disk.get_name()
                testflow.step("Activating disk %s on VM %s", disk_name, vm)
                ll_vms.wait_for_vm_states(vm, [config.VM_UP])
                assert ll_vms.activateVmDisk(True, vm, disk_name), (
                    "Failed to activate disk %s" % disk_name
                )


@bz({'1433949': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
    delete_disks.__name__,
)
class TestCase6234(TestCase):
    """
    Hot unplug bootable disk
    """
    __test__ = False
    polarion_test_case = '6234'

    @polarion("RHEVM3-6234")
    @tier2
    def test_hot_unplug_bootable_disk(self):
        """
        Hot unplug a bootable disk from a VM
        Test = False because bz 1433949 that will not be fixed
        """
        # Fetch VM boot disk
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP
        ), "Failed to start VM %s" % self.vm_name
        testflow.step("Hot unplug disk %s", self.disk_name)
        assert ll_disks.detachDisk(
            True, self.disk_name, self.vm_name
        ), "Failed to detach disk %s to vm %s" % (
            self.disk_name, self.vm_name
        )
        self.disks_to_remove.append(self.disk_name)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
    delete_disks.__name__,
    start_vm.__name__,
)
class TestCase16753(TestCase):
    """
    Hot plug disk with unsupported interface IDE
    """
    __test__ = True
    polarion_test_case = '16753'

    @polarion("RHEVM-16753")
    @tier3
    def test_hot_plug_disk_unsupported_interface(self):
        """
        Hot plug disk with unsupported interface IDE
        """
        testflow.step(
            "Trying to Hotplug disk %s with IDE interface", self.disk_name
        )
        assert ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, interface=config.IDE
        )
        self.disks_to_remove.append(self.disk_name)
