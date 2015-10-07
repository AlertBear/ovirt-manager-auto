"""
Test exposing BZ 1000789, checks that creating a vm
from a template with no disks is working
"""
import config
import logging
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import (
    templates, disks, storagedomains, jobs
)
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

VM_NO_DISKS = 'no_disk_vm'
TEMPLATE_NO_DISKS = 'no_disks_template'
VM_SHARED_DISK = 'shared_disk_vm'
TEMPLATE_SHARED_DISK = 'shared_disk_template'
VM_DIRECT_LUN = 'direct_lun_vm'
TEMPLATE_DIRECT_LUN = 'direct_lun_template'

LUN_ADDRESS = None
LUN_TARGET = None
LUN_ID = None
ISCSI = config.STORAGE_TYPE_ISCSI


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    global LUN_ADDRESS, LUN_TARGET, LUN_ID
    if not config.GOLDEN_ENV:
        # Backup all luns info
        lun_address_backup = config.PARAMETERS.as_list('lun_address')
        lun_target_backup = config.PARAMETERS.as_list('lun_target')
        lun_backup = config.PARAMETERS.as_list('lun')

        # Keep only one lun in the config, so build setup won't use both luns
        config.PARAMETERS['lun_address'] = config.PARAMETERS.as_list(
            'lun_address')[0]
        config.PARAMETERS['lun_target'] = config.PARAMETERS.as_list(
            'lun_target')[0]
        config.PARAMETERS['lun'] = config.PARAMETERS.as_list('lun')[0]

        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE)

        # Restore second lun
        config.PARAMETERS['lun_address'] = lun_address_backup
        config.PARAMETERS['lun_target'] = lun_target_backup
        config.PARAMETERS['lun'] = lun_backup

        LUN_ADDRESS = config.PARAMETERS['lun_address'][1] if \
            len(config.PARAMETERS['lun_address']) > 1 \
            else config.PARAMETERS['lun_address'][0]
        LUN_TARGET = config.PARAMETERS['lun_target'][1] if \
            len(config.PARAMETERS['lun_target']) > 1 \
            else config.PARAMETERS['lun_target'][0]
        LUN_ID = config.PARAMETERS['lun'][1] if \
            len(config.PARAMETERS['lun']) > 1 \
            else config.PARAMETERS['lun'][0]
    else:
        LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES[0]
        LUN_TARGET = config.UNUSED_LUN_TARGETS[0]
        LUN_ID = config.UNUSED_LUNS[0]


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True,
            config.DATA_CENTER_NAME,
            vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


@attr(tier=2)
class TestCase11843(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=1000789
    scenario:
    * create a VM from a template without disks

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Templates_General
    """
    # TODO: Why is this only for ISCSI?
    __test__ = (ISCSI in opts['storages'])
    polarion_test_case = '11843'
    storages = set([ISCSI])
    bz = {'1220824': {'engine': None, 'version': ['3.6']}}

    def setUp(self):
        """ Create vms and templates"""
        self.test_failed = False
        self.vms = []
        self.templates = []
        self.storage_domains = storagedomains.getStorageDomainNamesForType(
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

        if not templates.createTemplate(True, **template_kwargs):
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
        self.shared_disk_alias = "sharable_disk_%s" % self.polarion_test_case
        shared_disk_kwargs = {
            "interface": "virtio",
            "alias": self.shared_disk_alias,
            "format": "raw",
            "size": config.DISK_SIZE,
            "bootable": True,
            "storagedomain": self.storage_domains[0],
            "shareable": True,
            "sparse": False,
        }

        if not disks.addDisk(True, **shared_disk_kwargs):
            raise errors.DiskException("Cannot create shared disk %s"
                                       % self.shared_disk_alias)
        disks.wait_for_disks_status([self.shared_disk_alias], timeout=300)
        if not disks.attachDisk(True, self.shared_disk_alias, VM_SHARED_DISK):
            raise errors.DiskException("Cannot attach shared disk to vm %s"
                                       % VM_SHARED_DISK)

        # Create a template from vm with shared disk
        template_kwargs = {"vm": VM_SHARED_DISK,
                           "name": TEMPLATE_SHARED_DISK}

        if not templates.createTemplate(True, **template_kwargs):
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
        self.direct_lun_disk_alias = "direct_lun_disk"
        direct_lun_disk_kwargs = {
            "interface": "virtio",
            "alias": self.direct_lun_disk_alias,
            "size": config.DISK_SIZE,
            "bootable": True,
            "lun_address": LUN_ADDRESS,
            "lun_target": LUN_TARGET,
            "lun_id": LUN_ID,
            "type_": ISCSI,
        }

        if not disks.addDisk(True, **direct_lun_disk_kwargs):
            raise errors.DiskException("Cannot add direct lun disk to vm %s"
                                       % VM_DIRECT_LUN)

        # Create a template from vm without disks
        template_kwargs = {"vm": VM_DIRECT_LUN,
                           "name": TEMPLATE_DIRECT_LUN}

        if not templates.createTemplate(True, **template_kwargs):
            raise errors.TemplateException("Can't create template "
                                           "from vm %s" % VM_DIRECT_LUN)
        self.templates.append(TEMPLATE_DIRECT_LUN)

    @polarion("RHEVM3-11843")
    def test_create_vm_from_template(self):
        """ creates vms from templates
        """
        logger.info("Creating vm from template without disks")
        new_vm_name = "%s_new" % VM_NO_DISKS
        self.assertTrue(ll_vms.createVm(True, new_vm_name,
                                        "VM for bug 1000789",
                                        template=TEMPLATE_NO_DISKS,
                                        cluster=config.CLUSTER_NAME))
        self.vms.append(new_vm_name)

        logger.info("Creating vm from template with shared disk")
        new_vm_name = "%s_new" % VM_SHARED_DISK
        self.assertTrue(ll_vms.createVm(True, new_vm_name,
                                        "VM for bug 1000789",
                                        template=TEMPLATE_SHARED_DISK,
                                        cluster=config.CLUSTER_NAME))
        self.vms.append(new_vm_name)

        logger.info("Creating vm from template with direct lun")
        new_vm_name = "%s_new" % VM_DIRECT_LUN
        self.assertTrue(ll_vms.createVm(True, new_vm_name,
                                        "VM for bug 1000789",
                                        template=TEMPLATE_DIRECT_LUN,
                                        cluster=config.CLUSTER_NAME))
        self.vms.append(new_vm_name)

    def tearDown(self):
        """
        Wait for all vm's disk status to be OK, remove all created vms,
        templates and disks
        """
        for vm in self.vms:
            ll_vms.waitForDisksStat(vm)
        if not ll_vms.safely_remove_vms(self.vms):
            logger.error("Failed to remove vms %s", self.vms)
            self.test_failed = True
        if not templates.removeTemplates(True, self.templates):
            logger.error("Failed to remove templates %s", self.templates)
            self.test_failed = True
        if not disks.deleteDisk(True, self.shared_disk_alias):
            logger.error("Failed to delete disk %s", self.shared_disk_alias)
            self.test_failed = True
        if not disks.deleteDisk(True, self.direct_lun_disk_alias):
            logger.error(
                "Failed to delete disk %s", self.direct_lun_disk_alias,
            )
            self.test_failed = True
        jobs.wait_for_jobs([config.ENUMS['job_remove_disk']])
        if self.test_failed:
            raise errors.TestException("Test failed during tearDown")
