"""
Storage VM sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage/3_3_Storage_VM_Sanity
"""
import logging

import pytest

import config
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    templates as ll_template,
    storagedomains as ll_sd,
)
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import polarion
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    add_disk, create_snapshot, create_vm, delete_disks,
    poweroff_vm, preview_snapshot, undo_snapshot
)
from rhevmtests.storage.storage_full_disk_sanity.fixtures import (
    create_second_vm, poweroff_vm_and_wait_for_stateless_to_remove
)

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS


def _prepare_data(sparse, vol_format, template_names, storage_type):
    """ prepares data for vm
    """
    storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage_type)[0]
    template_name = "%s_%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format, storage_type)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.TESTNAME, sparse, vol_format, storage_type)
    logger.info("Creating vm sparse - %s %s %s..." %
                (sparse, vol_format, storage_type))
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    vm_args['volumeType'] = sparse
    vm_args['volumeFormat'] = vol_format
    vm_args['start'] = 'true'
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException("Creation of vm %s failed!" % vm_name)
    logger.info("Waiting for ip of %s" % vm_name)
    vm_ip = ll_vms.waitForIP(vm_name)[1]['ip']
    logger.info("Setting persistent network")
    assert test_utils.setPersistentNetwork(vm_ip, config.VMS_LINUX_PW)
    logger.info("Stopping VM %s" % vm_name)
    if not ll_vms.stopVm(True, vm_name):
        raise exceptions.VMException("Stopping vm %s failed" % vm_name)
    logger.info(
        "Creating template %s from vm %s" % (template_name, vm_name))
    if not ll_template.createTemplate(
            True, vm=vm_name, name=template_name, cluster=config.CLUSTER_NAME):
        raise exceptions.TemplateException(
            "Creation of template %s from vm %s failed!" % (
                template_name, vm_name))
    logger.info("Removing vm %s" % vm_name)
    if not ll_vms.removeVm(True, vm=vm_name):
        raise exceptions.VMException("Removal of vm %s failed" % vm_name)
    logger.info(
        "Template for sparse=%s and volume format '%s' prepared" % (
            sparse, vol_format))
    template_names[(sparse, vol_format)] = template_name


@attr(tier=2)
class TestCase4710(TestCase):
    """
    storage vm sanity test, cloning vm from template with changing disk type
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_VM_Sanity
    """
    __test__ = True
    polarion_test_case = '4710'
    template_names = {}

    @classmethod
    def setup_class(cls):
        for sparse in (True, False):
            for vol_format in (ENUMS['format_cow'], ENUMS['format_raw']):
                if not sparse and vol_format == ENUMS['format_cow']:
                    continue
                if (cls.storage != ENUMS['storage_type_nfs']
                        and sparse and vol_format == ENUMS['format_raw']):
                    continue
                _prepare_data(
                    sparse, vol_format, cls.template_names, cls.storage
                )

    def setUp(self):
        self.vm_names = []

    @polarion("RHEVM3-4710")
    def create_vm_from_template_validate_disks(
            self, name, template_name, sparse, vol_format):
        vm_name = "%s_%s_clone_%s" % (
            self.polarion_test_case, self.storage, name)
        logger.info("Clone vm %s, from %s, sparse=%s, volume format = %s" % (
            vm_name, template_name, sparse, vol_format))
        self.assertTrue(
            ll_vms.cloneVmFromTemplate(
                True, name=vm_name, cluster=config.CLUSTER_NAME,
                vol_sparse=sparse, vol_format=vol_format,
                template=template_name, clone=True, timeout=900),
            "cloning vm %s from template %s failed" % (vm_name, template_name))
        self.vm_names.append(vm_name)
        logger.info("Validating disk type and format")
        self.assertTrue(
            ll_vms.validateVmDisks(
                True, vm=vm_name, sparse=sparse, format=vol_format),
            "Validation of disks on vm %s failed" % vm_name)
        logger.info("Validation passed")

    def create_vms_from_template_convert_disks(
            self, sparse, vol_format, name_prefix):
        name = '%s_sparse_cow' % name_prefix
        template_name = self.template_names[(sparse, vol_format)]
        self.create_vm_from_template_validate_disks(
            name, template_name, True, ENUMS['format_cow'])
        if self.storage == ENUMS['storage_type_nfs']:
            name = '%s_sparse_raw' % name_prefix
            self.create_vm_from_template_validate_disks(
                name, template_name, True, ENUMS['format_raw'])
        name = '%s_preallocated_raw' % name_prefix
        self.create_vm_from_template_validate_disks(
            name, template_name, False, ENUMS['format_raw'])

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_sparse_cow_test(self):
        """ creates vms from template with sparse cow disk
        """
        self.create_vms_from_template_convert_disks(
            True, ENUMS['format_cow'], 'from_sparse_cow')

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_sparse_raw_test(self):
        """ creates vms from template with sparse raw disk
        """
        if self.storage == ENUMS['storage_type_nfs']:
            self.create_vms_from_template_convert_disks(
                True, ENUMS['format_raw'], 'from_sparse_raw')

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_preallocated_raw_test(self):
        """ creates vms from templates with preallocated raw disk
        """
        self.create_vms_from_template_convert_disks(
            False, ENUMS['format_raw'], 'from_prealloc_raw')

    def tearDown(self):
        if self.vm_names:
            ll_vms.removeVms(True, self.vm_names, stop='true')

    @classmethod
    def teardown_class(cls):
        for _, template_name in cls.template_names.iteritems():
            ll_template.removeTemplate(True, template=template_name)


class TestReadLock(TestCase):
    """
    Create a template from a VM, then start to create 2 VMs from
    this template at once.
    """
    # TODO: Create a polarion case for this/verify it, if not remove it
    __test__ = False
    polarion_test_case = None
    vm_type = None
    vm_name = None
    template_name = None
    vm_name_1 = '%s_readlock_1' % config.TEST_NAME
    vm_name_2 = '%s_readlock_2' % config.TEST_NAME
    SLEEP_AMOUNT = 5

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_readlock_%s' % (config.TEST_NAME, cls.vm_type)
        cls.template_name = "template_%s" % (cls.vm_name)
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        if not storage_helpers.create_vm_or_clone(
            True, cls.vm_name, diskInterface=config.INTERFACE_VIRTIO,
            type=cls.vm_type, storageDomainName=storage_domain
        ):
            raise exceptions.VMException(
                "Creation of VM %s failed!" % cls.vm_name)
        logger.info("Waiting for vm %s state 'up'" % cls.vm_name)
        if not ll_vms.waitForVMState(cls.vm_name):
            raise exceptions.VMException(
                "Waiting for VM %s status 'up' failed" % cls.vm_name)
        logger.info("Waiting for ip of %s" % cls.vm_name)
        vm_ip = ll_vms.waitForIP(cls.vm_name)[1]['ip']
        logger.info("Setting persistent network")
        assert test_utils.setPersistentNetwork(vm_ip, config.VMS_LINUX_PW)

        logger.info("Shutting down %s" % cls.vm_name)
        if not ll_vms.shutdownVm(True, cls.vm_name, async='false'):
            raise exceptions.VMException("Can't shut down vm %s" %
                                         cls.vm_name)
        logger.info("Creating template %s from VM %s" % (cls.template_name,
                                                         cls.vm_name))
        template_args = {
            "vm": cls.vm_name,
            "name": cls.template_name,
            "cluster": config.CLUSTER_NAME
        }
        if not ll_template.createTemplate(True, **template_args):
            raise exceptions.TemplateException("Failed creating template %s" %
                                               cls.template_name)

    def create_two_vms_simultaneously(self):
        """
        Start creating a VM from template
        Wait until template is locked
        Start creating another VM from the same template
        """
        logger.info("Creating first vm %s from template %s" %
                    (self.vm_name_1, self.template_name))
        assert ll_vms.createVm(
            True, self.vm_name_1, self.vm_name_1, template=self.template_name,
            cluster=config.CLUSTER_NAME
        )
        logger.info("Waiting for createVolume command in engine.log")
        log_listener.watch_logs(
            files_to_watch=config.ENGINE_LOG,
            regex='createVolume',
            time_out=60,
            ip_for_files=config.VDC,
            username='root',
            password=config.VDC_ROOT_PASSWORD
        )
        logger.info("Starting to create vm %s from template %s" %
                    (self.vm_name_2, self.template_name))
        assert ll_vms.createVm(
            True, self.vm_name_2, self.vm_name_2, template=self.template_name,
            cluster=config.CLUSTER_NAME
        )
        logger.info("Starting VMs")
        assert ll_vms.startVm(
            True, self.vm_name_1, wait_for_status=ENUMS['vm_state_up']
        )
        assert ll_vms.startVm(
            True, self.vm_name_2, wait_for_status=ENUMS['vm_state_up']
        )

    @classmethod
    def teardown_class(cls):
        vms_list = [cls.vm_name, cls.vm_name_1, cls.vm_name_2]
        logger.info("Removing VMs %s" % vms_list)
        if not ll_vms.removeVms(True, vms_list, stop='true'):
            raise exceptions.VMException("Failed removing vms %s" % vms_list)
        logger.info("Removing template")
        if not ll_template.removeTemplate(True, cls.template_name):
            raise exceptions.TemplateException("Failed removing template %s"
                                               % cls.template_name)


@attr(tier=2)
@pytest.mark.usefixtures(create_vm.__name__, delete_disks.__name__)
class NegativeAttachDetach(TestCase):
    """
    * Attach a locked disk to VM
    * Detach disk from vm in powering up state
    """
    __test__ = True
    disk_size = 20 * config.GB
    installation = False

    @polarion("RHEVM3-16713")
    def test_attach_locked_disk_to_vm(self):
        """
        Attach disk to VM when the disk is in locked state
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, provisioned_size=self.disk_size,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO_SCSI, format=config.RAW_DISK,
            sparse=False
        )
        assert ll_disks.wait_for_disks_status(
            [self.disk_name], status=config.DISK_LOCKED
        )
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s" %
            (self.disk_name, self.vm_name)
        )
        self.disks_to_remove.append(self.disk_name)

    @polarion("RHEVM3-16714")
    @pytest.mark.usefixtures(poweroff_vm.__name__)
    def test_detach_disk_from_powering_up_vm(self):
        """
        Detach a disk from a VM in powering up state
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0]
        ll_vms.startVm(True, self.vm_name, None)
        assert ll_disks.detachDisk(False, vm_disk.get_alias(), self.vm_name), (
            "Succeeded to detach disk %s from VM %s" %
            (self.disk_name, self.vm_name)
        )
        ll_vms.wait_for_vm_states(self.vm_name)

    @polarion("RHEVM3-16736")
    @pytest.mark.usefixtures(poweroff_vm.__name__)
    def test_attach_disk_to_vm_in_powering_up_state(self):
        """
        Attach disk to VM in powering up state
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, provisioned_size=config.DISK_SIZE,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO, format=config.COW_DISK, sparse=True
        )
        assert ll_disks.wait_for_disks_status([self.disk_name])
        ll_vms.startVm(True, self.vm_name, None)
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s in powering up state" % (
                self.disk_name, self.vm_name
            )
        )
        ll_vms.wait_for_vm_states(self.vm_name)
        self.disks_to_remove.append(self.disk_name)

    @polarion("RHEVM3-16739")
    def test_attach_disk_to_vm_as_bootable(self):
        """
        Attach disk to VM as second bootable disk - should fail
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, provisioned_size=config.DISK_SIZE,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO, format=config.COW_DISK, sparse=True
        )
        assert ll_disks.wait_for_disks_status([self.disk_name])
        assert ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, bootable=True), (
            "Succeeded to attach disk %s to VM %s as second bootable disk" %
            (self.disk_name, self.vm_name)
        )

        self.disks_to_remove.append(self.disk_name)


@attr(tier=2)
@pytest.mark.usefixtures(create_vm.__name__)
class TestCase16737(TestCase):
    """
    Attach OVF store disk to VM - should fail
    """
    __test__ = True
    installation = False
    storage_domain = None

    @polarion("RHEVM3-16737")
    def test_attach_ovf_disk_to_vm(self):
        """
        Attach OVF disk to VM
        """
        ovf_disk = None
        all_disks = ll_disks.get_all_disks()
        for disk in all_disks:
            if disk.get_alias() == config.OVF_DISK_ALIAS:
                ovf_disk = disk
                break

        assert ll_disks.attachDisk(
            False, ovf_disk.get_alias(), self.vm_name,
            disk_id=ovf_disk.get_id()
        ), "Succeeded to attach disk %s to VM %s" % (
            ovf_disk.get_alias(), self.vm_name
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    preview_snapshot.__name__,
    add_disk.__name__,
    undo_snapshot.__name__
)
class TestCase16738(TestCase):
    """
    Attach disk to VM in preview - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16738")
    def test_attach_disk_to_vm_in_preview(self):
        """
        Attach disk to VM in preview of snapshot
        """
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s in preview" %
            (self.disk_name, self.vm_name)
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    poweroff_vm_and_wait_for_stateless_to_remove.__name__
)
class TestCase16741(TestCase):
    """
    Attach stateless snapshot's disk to VM - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16741")
    def test_attach_disk_of_stateless_snapshot_to_vm(self):
        """
        Attach stateless snapshot's disk to VM
        """
        assert ll_vms.runVmOnce(
            True, self.vm_name, config.VM_UP, stateless=True
        ), "Failed to run VM %s in stateless" % self.vm_name
        stateless_snapshot_disk = ll_vms.get_snapshot_disks(
            self.vm_name, config.STATELESS_SNAPSHOT
        )[0]
        assert not ll_vms.attach_snapshot_disk_to_vm(
            stateless_snapshot_disk, config.VM_NAME[0]
        ), "Succeeded to attach a stateless snapshot's disk to vm"


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
)
class TestCase16742(TestCase):
    """
    Attach read only disk to VM with IDE interface - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16742")
    def test_attach_read_only_disk_with_ide(self):
        """
        Attach read only disk to VM with IDE interface
        """
        assert ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, read_only=True,
            interface=config.IDE
        ), (
            "Succeeded to attach disk %s to VM %s in preview" %
            (self.disk_name, self.vm_name)
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    create_second_vm.__name__
)
class TestCase16743(TestCase):
    """
    Detach snapshot's disk from VM
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16743")
    def test_detach_snapshot_disk_to_vm(self):
        """
        Detach snapshot's disk from VM
        """
        snapshot_disk = ll_vms.get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )[0]
        assert ll_vms.attach_snapshot_disk_to_vm(
            snapshot_disk, self.second_vm_name
        ), (
            "Failed to attach snapshot's disk %s to VM %s" %
            (snapshot_disk.get_alias(), self.second_vm_name)
        )
        assert ll_disks.detachDisk(
            False, snapshot_disk.get_alias(), self.vm_name
        ), (
            "Succeeded to detach snapshot's disk %s from VM %s" %
            (snapshot_disk.get_alias(), self.vm_name)
        )
