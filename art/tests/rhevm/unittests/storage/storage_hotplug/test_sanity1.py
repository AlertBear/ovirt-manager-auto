"""
Hotplug Sanity Tests
Test Cases:
        * Plug in Disk (134134)
        * Unplug Disk (134139)
        * Activate & Deactivate disk (231521)
Author: Gadi Ickowicz
"""

from art.rhevm_api.tests_lib.low_level import disks, vms
import art.test_handler.exceptions as exceptions
from art.test_handler.tools import tcms
from art.test_handler.settings import opts
import common
from common import shutdown_and_remove_vms, GB, ENUMS, \
    DISK_INTERFACES, VM_NAME_FORMAT, DISK_NAME_FORMAT, _raise_if_exception
from concurrent.futures import ThreadPoolExecutor
import config
import logging
from nose.tools import istest
import time
import unittest

positive = True
logger = logging.getLogger(__name__)


def setup_module():
    """
    Create VM templates with different OSs and all disk type combinations
    """
    logger.info("setup_module")

    disk_results = common.start_creating_disks_for_test()

    vm_results = common.start_installing_vms_for_test()

    logger.info("Ensuring all disks were created succesfully")
    for result in disk_results:
        exception = result.exception()
        if exception is not None:
            raise exception
        status, diskIdDict = result.result()
        if not status:
            raise exceptions.DiskException("Unable to create disk")
    logger.info("All disks created succesfully")
    logger.info("Waiting for vms to be installed and templates to be created")
    for result in vm_results:
        exception = result.exception()
        if exception is not None:
            raise exception
    logger.info("All templatess created succesfully")
    logger.info("Package setup successfull")


def teardown_module():
    """
    clean setup
    """
    logger.info("Teardown module")


class TestCase134134(unittest.TestCase):
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
        logger.info("setup class %s" % cls.__name__)

        def _create_and_start_vm(template):
            """
            Clones and starts a single vm from template
            """
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            logger.info("Starting VM %s" % vm_name)
            vms.startVm(positive, vm=vm_name, wait_for_ip=True)
            logger.info("VM %s started succesfully" % vm_name)
            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_and_start_vm, template))

        _raise_if_exception(results)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_virtio_disk(self):
        """
        Try to plug in a new virtIO disk while OS is running
        """
        for template in config.TEMPLATE_NAMES:
            vm_name = VM_NAME_FORMAT % (template, self.__class__.__name__)
            disk_name = DISK_NAME_FORMAT % (
                template, ENUMS["interface_virtio"], "shareable")
            logger.info("Attempting to hotplug disk %s to VM %s" %
                        (disk_name, vm_name))
            status = disks.attachDisk(positive,
                                      alias=disk_name,
                                      vmName=vm_name,
                                      active=True)
            logger.info('Done')
            self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        Shuts down the vm and removes it
        """
        shutdown_and_remove_vms(cls.vm_names)


class TestCase134139(unittest.TestCase):
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
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            logger.info("Adding 2 disks to VM %s" % vm_name)

            disk_args = {
                'positive': True,
                'size': 2 * GB,
                'sparse': True,
                'wipe_after_delete': config.BLOCK_FS,
                'storagedomain': config.STORAGE_DOMAIN_NAME,
                'bootable': False,
                'interface': ENUMS['interface_virtio'],
                'vm': vm_name,
            }

            # add 2 disks:
            logger.info("Adding first disk to vm %s" % vm_name)
            if not vms.addDisk(**disk_args):
                raise exceptions.DiskException("Unable to add disk to VM %s"
                                               % vm_name)
            logger.info("First disk added succesfully to vm %s" % vm_name)
            logger.info("Adding second disk to vm %s" % vm_name)
            if not vms.addDisk(**disk_args):
                raise exceptions.DiskException("Unable to add disk to VM %s"
                                               % vm_name)
            logger.info("Second disk added succesfully to vm %s" % vm_name)

            non_bootable_disks = [disk for disk in vms.getVmDisks(vm_name)
                                  if not disk.get_bootable()]
            disk = non_bootable_disks[0]
            logger.info("Deactivating disk %s on vm %s"
                        % (disk.get_name(), vm_name))
            if not vms.deactivateVmDisk(positive,
                                        vm=vm_name,
                                        diskAlias=disk.get_name(),
                                        wait=True):
                raise exceptions.DiskException("Unable to deactivate disk %s" %
                                               disk)
            logger.info("Disk %s deactivated succesfully on vm %s"
                        % (disk.get_name(), vm_name))
            if not vms.startVm(positive, vm=vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)

            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vm_and_disks, template))

        _raise_if_exception(results)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_unplug_disk(self):
        """
        Attempt to unplug (deactivate) active disk from a VM with OS running
        """
        for vm in self.vm_names:
            logger.info("Getting active non-bootable disks for vm %s" % vm)
            active_disks = [disk for disk in vms.getVmDisks(vm) if
                            disk.get_active() and not disk.get_bootable()]
            logger.info("Unplugging disk %s from vm %s" %
                        (active_disks[0].get_name(), vm))
            result = vms.deactivateVmDisk(positive,
                                          vm=vm,
                                          diskAlias=active_disks[0].get_name(),
                                          wait=True)
            logger.info("Done unplugging disk")
            self.assertTrue(result)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_detach_disk(self):
        """
        Attempt to detach inactive disk from a VM with OS running
        """
        for vm in self.vm_names:
            logger.info("Getting inactive non-bootable disks for vm %s" % vm)
            inactive_disks = [disk for disk in vms.getVmDisks(vm) if
                              not disk.get_active()]
            logger.info("Detaching disk %s from vm %s" %
                        (inactive_disks[0].get_alias(), vm))
            self.assertTrue(disks.detachDisk(positive,
                            alias=inactive_disks[0].get_alias(),
                            vmName=vm))
            logger.info("Done detaching disk %s from vm %s" %
                        (inactive_disks[0].get_alias(), vm))

    @classmethod
    def teardown_class(cls):
        """
        Shutdown all vms, forcefully if needed, and remove them
        """
        shutdown_and_remove_vms(cls.vm_names)


class TestCase231521(unittest.TestCase):
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
            vm_name = common.clone_vm_for_test(template, cls.__name__)

            # add disk and deactivate it
            logger.info("Adding 2 disks to VM %s" % vm_name)
            disk_args = {
                'positive': True,
                'size': 2 * GB,
                'sparse': True,
                'wipe_after_delete': config.BLOCK_FS,
                'storagedomain': config.STORAGE_DOMAIN_NAME,
                'bootable': False,
                'interface': ENUMS['interface_virtio'],
                'vm': vm_name,
            }

            logger.info("Adding first disk...")
            if not vms.addDisk(**disk_args):
                raise exceptions.DiskException("Unable to add disk to VM %s"
                                               % vm_name)
            logger.info("First disk added succesfully")
            logger.info("Adding second disk...")
            if not vms.addDisk(**disk_args):
                raise exceptions.DiskException("Unable to add disk to VM %s"
                                               % vm_name)
            logger.info("Second disk added succesfully")
            non_bootable_disks = [disk for disk in vms.getVmDisks(vm_name)
                                  if not disk.get_bootable()]
            disk = non_bootable_disks[0]
            logger.info("Deactivating disk %s" % disk.get_name())
            diskAlias = disk.get_name()
            if not vms.deactivateVmDisk(positive,
                                        vm=vm_name,
                                        diskAlias=diskAlias,
                                        wait=True):
                raise exceptions.DiskException("Unable to deactivate disk %s" %
                                               disk.get_name())
            if not vms.startVm(positive, vm=vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)

            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vm_and_disks, template))

        _raise_if_exception(results)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_activate_disk(self):
        """Activate an already attached disk on a running VM"""
        for vm in self.vm_names:
            inactive_disks = [disk for disk in vms.getVmDisks(vm)
                              if not disk.get_bootable() and
                              not disk.get_active()]
            disk_name = inactive_disks[0].get_name()
            logger.info("Activating disk %s on VM %s" % (disk_name, vm))
            status = vms.activateVmDisk(positive,
                                        vm=vm,
                                        diskAlias=disk_name)
            logger.info("Finished activating disk %s" % disk_name)
            self.assertTrue(status)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_deactivate_disk(self):
        """Deactivate an already attached disk on a running VM"""
        for vm in self.vm_names:
            active_disks = [disk for disk in vms.getVmDisks(vm)
                            if not disk.get_bootable() and
                            disk.get_active()]
            disk_name = active_disks[0].get_name()
            logger.info("Deactivating disk %s on VM %s" % (disk_name, vm))
            status = vms.deactivateVmDisk(positive,
                                          vm=vm,
                                          diskAlias=disk_name)
            logger.info("Finished deactivating disk %s" % disk_name)
            self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        remove all vms created during the test
        """
        shutdown_and_remove_vms(cls.vm_names)
