"""
Hotplug Sanity Tests
Test Cases:
        * Plug in Disk (139348)
        * Plug Shared Disk into 2 vms (244310)
        * Unplug shared disk from one VM only (244314)
Author: Gadi Ickowicz
"""

from art.rhevm_api.tests_lib.low_level import disks, vms
import art.test_handler.exceptions as exceptions
from art.test_handler.tools import tcms
from art.test_handler.settings import opts
import common
from common import shutdown_and_remove_vms, GB, ENUMS,\
    DISK_INTERFACES, VM_NAME_FORMAT, DISK_NAME_FORMAT, _raise_if_exception
from concurrent.futures import ThreadPoolExecutor
import config
import logging
from nose.tools import istest
import time
from art.unittest_lib import BaseTestCase as TestCase

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
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            logger.info("Starting vm %s" % vm_name)
            if not vms.startVm(positive, vm_name, wait_for_ip=True):
                raise exceptions.VMException("Unable to start VM %s" % vm_name)
            logger.info("VM %s started successfully" % vm_name)
            cls.vm_names.append(vm_name)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_and_start_vm, template))

        _raise_if_exception(results)

    @istest
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

                    logger.info("attempting to plug disk %s to vm %s" %
                                (disk_name, vm_name))
                    status = disks.attachDisk(positive,
                                              alias=disk_name,
                                              vmName=vm_name)
                    logger.info("Done - status is %s" % status)
                    self.assertTrue(status)

    @classmethod
    def teardown_class(cls):
        """
        remove vm and disk
        """
        shutdown_and_remove_vms(cls.vm_names)


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
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            new_name = vm_name + "1"
            logger.info("renaming vm %s to %s" % (vm_name, new_name))
            if not vms.updateVm(positive, vm=vm_name, name=new_name):
                raise exceptions.VMException("Unable to rename vm %s to %s" %
                                             (vm_name, new_name))
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            vm_pair = (vm_name, new_name)
            for vm in vm_pair:
                logger.info("Starting vm %s" % vm)
                if not vms.startVm(positive, vm, wait_for_ip=True):
                    raise exceptions.VMException("Unable to start VM %s" % vm)
                logger.info("VM %s started successfully" % vm)
            cls.vm_pairs.append(vm_pair)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vms_and_disks,
                                               template))

        _raise_if_exception(results)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_plug_shared_disk_to_2_vms_same(self):
        """
        plug same disk into 2 vms simultaneously
        """
        for (first_vm, second_vm), template in zip(self.vm_pairs,
                                                   config.TEMPLATE_NAMES):
            logger.info("VMs are: %s, %s" % (first_vm, second_vm))
            disk_name = DISK_NAME_FORMAT % (template,
                                            ENUMS['interface_virtio'],
                                            'shareable')
            logger.info("Plugging disk %s into vm %s (first vm)" %
                        (disk_name, first_vm))
            first_plug_status = disks.attachDisk(positive,
                                                 alias=disk_name,
                                                 vmName=first_vm)
            logger.info("Plugging disk %s into vm %s (second vm)" %
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
        for vm_pair in cls.vm_pairs:
            shutdown_and_remove_vms(vm_pair)


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
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            new_name = vm_name + "1"
            logger.info("renaming vm %s to %s" % (vm_name, new_name))
            if not vms.updateVm(positive, vm=vm_name, name=new_name):
                raise exceptions.VMException("Unable to rename vm %s to %s" %
                                  (vm_name, new_name))
            vm_name = common.clone_vm_for_test(template, cls.__name__)
            vm_pair = (vm_name, new_name)
            for vm in vm_pair:
                logger.info("Plugging and activating disk %s to vm %s" %
                            (disk_name, vm))
                if not disks.attachDisk(positive, alias=disk_name, vmName=vm):
                    raise exceptions.DiskException("Unable to plug %s to vm %s"
                                                   % (disk_name, vm))
                logger.info("Disk %s plugged to vm %s" % (disk_name, vm))
                logger.info("Starting vm %s" % vm)
                if not vms.startVm(positive, vm, wait_for_ip=True):
                    raise exceptions.VMException("Unable to start VM %s" % vm)
                logger.info("VM %s started successfully" % vm)
                cls.vm_pairs.append(vm_pair)

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template in config.TEMPLATE_NAMES:
                results.append(executor.submit(_create_vms_and_disks,
                                               template))

        _raise_if_exception(results)

    @istest
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
            logger.info("Unplugging disk %s from vm %s" %
                        (disk_name, first_vm))
            unplug_status = vms.deactivateVmDisk(positive,
                                                 diskAlias=disk_name,
                                                 vm=first_vm)
            logger.info("Disk %s unplugged from vm %s" % (disk_name, first_vm))
            self.assertTrue(unplug_status)

    @classmethod
    def teardown_class(cls):
        """
        Shutdown and remove vms created in test
        """
        for vm_pair in cls.vm_pairs:
            shutdown_and_remove_vms(vm_pair)
