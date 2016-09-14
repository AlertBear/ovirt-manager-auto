"""
Test exposing BZ 1000789, checks that creating a vm
from a template with no disks is working
"""
import logging

import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)

import art.test_handler.exceptions as errors
from art.test_handler.tools import polarion
from art.test_handler.settings import opts
from art.unittest_lib import attr, StorageTest as TestCase
import rhevmtests.helpers as rhevm_helpers

logger = logging.getLogger(__name__)

VM_NO_DISKS = '11843_no_disk_vm'
TEMPLATE_NO_DISKS = '11843_no_disks_template'
VM_SHARED_DISK = '11843_shared_disk_vm'
TEMPLATE_SHARED_DISK = '11843_shared_disk_template'
VM_DIRECT_LUN = '11843_direct_lun_vm'
TEMPLATE_DIRECT_LUN = '11843_direct_lun_template'

ISCSI = config.STORAGE_TYPE_ISCSI


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    rhevm_helpers.storage_cleanup()


@attr(tier=3)
class TestCase11843(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=1000789
    scenario:
    * create a VM from a template without disks

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Templates_General
    """
    # TODO: Why is this only for ISCSI?
    __test__ = ISCSI in opts['storages']
    polarion_test_case = '11843'
    storages = set([ISCSI])
    # Bugzilla history:
    # 1220824:  [REST] Adding a disk to a vm fails with NullPointerException
    # if not disk.storage_domains is provided (even for direct lun disks)

    def setUp(self):
        """ Create vms and templates"""
        self.vms = []
        self.templates = []
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )

        # Add a vm without disks
        if not ll_vms.addVm(True, name=VM_NO_DISKS,
                            storagedomain=self.storage_domains[0],
                            cluster=config.CLUSTER_NAME):
            raise errors.VMException("Cannot create vm %s" % VM_NO_DISKS)
        self.vms.append(VM_NO_DISKS)

        # Create a template from vm without disks
        template_kwargs = {"vm": VM_NO_DISKS,
                           "name": TEMPLATE_NO_DISKS}

        if not ll_templates.createTemplate(True, **template_kwargs):
            raise errors.TemplateException("Can't create template "
                                           "from vm %s" % VM_NO_DISKS)
        self.templates.append(TEMPLATE_NO_DISKS)

        # Add a vm with shared disk
        if not ll_vms.addVm(True, name=VM_SHARED_DISK,
                            storagedomain=self.storage_domains[0],
                            cluster=config.CLUSTER_NAME):
            raise errors.VMException("Cannot create vm %s" % VM_SHARED_DISK)
        self.vms.append(VM_SHARED_DISK)

        # Add a shared disk
        self.shared_disk_alias = "%s_sharable_disk" % self.polarion_test_case
        shared_disk_kwargs = {
            "interface": config.DISK_INTERFACE_VIRTIO,
            "alias": self.shared_disk_alias,
            "format": config.DISK_FORMAT_RAW,
            "provisioned_size": config.DISK_SIZE,
            "bootable": True,
            "storagedomain": self.storage_domains[0],
            "shareable": True,
            "sparse": False,
        }

        if not ll_disks.addDisk(True, **shared_disk_kwargs):
            raise errors.DiskException("Cannot create shared disk %s"
                                       % self.shared_disk_alias)
        ll_disks.wait_for_disks_status([self.shared_disk_alias], timeout=300)
        if not ll_disks.attachDisk(
            True, self.shared_disk_alias, VM_SHARED_DISK
        ):
            raise errors.DiskException("Cannot attach shared disk to vm %s"
                                       % VM_SHARED_DISK)

        # Create a template from vm with shared disk
        template_kwargs = {"vm": VM_SHARED_DISK,
                           "name": TEMPLATE_SHARED_DISK}

        if not ll_templates.createTemplate(True, **template_kwargs):
            raise errors.TemplateException("Can't create template "
                                           "from vm %s" % VM_SHARED_DISK)
        self.templates.append(TEMPLATE_SHARED_DISK)

        # Add a vm with direct lun disk
        if not ll_vms.addVm(True, name=VM_DIRECT_LUN,
                            storagedomain=self.storage_domains[0],
                            cluster=config.CLUSTER_NAME):
            raise errors.VMException("Cannot create vm %s" % VM_DIRECT_LUN)
        self.vms.append(VM_DIRECT_LUN)

        # Add a direct lun disk
        self.direct_lun_disk_alias = (
            "%s_direct_lun_disk" % self.polarion_test_case
        )
        direct_lun_disk_kwargs = {
            "interface": config.VIRTIO_SCSI,
            "format": config.DISK_FORMAT_COW,
            "alias": self.direct_lun_disk_alias,
            "provisioned_size": config.DISK_SIZE,
            "bootable": True,
            "shareable": False,
            "active": True,
            "lun_address": config.UNUSED_LUN_ADDRESSES[0],
            "lun_target": config.UNUSED_LUN_TARGETS[0],
            "lun_id": config.UNUSED_LUNS[0],
            "type_": self.storage,
        }

        if not ll_disks.addDisk(True, **direct_lun_disk_kwargs):
            raise errors.DiskException("Cannot add direct lun disk to vm %s"
                                       % VM_DIRECT_LUN)

        if not ll_disks.attachDisk(
            True, self.direct_lun_disk_alias, VM_DIRECT_LUN
        ):
            raise errors.DiskException(
                "Cannot attach disk lun disk to vm %s" % VM_DIRECT_LUN
            )

        # Create a template from vm with a direct lun disk
        template_kwargs = {"vm": VM_DIRECT_LUN,
                           "name": TEMPLATE_DIRECT_LUN}

        if not ll_templates.createTemplate(True, **template_kwargs):
            raise errors.TemplateException("Can't create template "
                                           "from vm %s" % VM_DIRECT_LUN)
        self.templates.append(TEMPLATE_DIRECT_LUN)

    @polarion("RHEVM3-11843")
    def test_create_vm_from_template(self):
        """ creates vms from templates
        """
        logger.info("Creating vm from template without disks")
        new_vm_name = "%s_new" % VM_NO_DISKS
        assert ll_vms.createVm(True, new_vm_name,
                               "VM for bug 1000789",
                               template=TEMPLATE_NO_DISKS,
                               cluster=config.CLUSTER_NAME)
        self.vms.append(new_vm_name)

        logger.info("Creating vm from template with shared disk")
        new_vm_name = "%s_new" % VM_SHARED_DISK
        assert ll_vms.createVm(True, new_vm_name,
                               "VM for bug 1000789",
                               template=TEMPLATE_SHARED_DISK,
                               cluster=config.CLUSTER_NAME)
        self.vms.append(new_vm_name)

        logger.info("Creating vm from template with direct lun")
        new_vm_name = "%s_new" % VM_DIRECT_LUN
        assert ll_vms.createVm(True, new_vm_name,
                               "VM for bug 1000789",
                               template=TEMPLATE_DIRECT_LUN,
                               cluster=config.CLUSTER_NAME)
        self.vms.append(new_vm_name)
        ll_jobs.wait_for_jobs([config.JOB_ADD_VM_FROM_TEMPLATE])

    def tearDown(self):
        """
        Remove all created vms, templates and disks
        """
        if not ll_vms.safely_remove_vms(self.vms):
            logger.error("Failed to remove vms %s", self.vms)
            TestCase.test_failed = True
        if not ll_templates.removeTemplates(True, self.templates):
            logger.error("Failed to remove templates %s", self.templates)
            TestCase.test_failed = True
        if not ll_disks.deleteDisk(True, self.shared_disk_alias):
            logger.error("Failed to delete disk %s", self.shared_disk_alias)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs(
            [config.JOB_REMOVE_DISK, config.JOB_REMOVE_VM,
             config.JOB_REMOVE_TEMPLATE]
        )
        TestCase.teardown_exception()
