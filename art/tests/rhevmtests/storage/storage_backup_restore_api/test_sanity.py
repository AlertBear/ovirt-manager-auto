"""
Storage backup restore API
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Backup_API
"""
import logging
import helpers
from unittest2 import SkipTest
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
import art.rhevm_api.utils.storage_api as st_api
from art.rhevm_api.utils import test_utils as utils
from art.test_handler import exceptions
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, StorageTest as TestCase, testflow
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import config
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)

VM_COUNT = 2
TASK_TIMEOUT = 1500
BACKUP_DISK_SIZE = 10 * config.GB
LIVE_MIGRATE_DISK_TIMEOUT = 1800


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    attach_backup_disk = True

    def setUp(self):
        """
        1) Create 2 VMs using Glance image
        2) Take a snapshot of the first VM
        3) Attach the snapshot disk from the first VM to the second VM (
        unless requested otherwise)
        """
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.vm_names = []
        for idx in range(VM_COUNT):
            vm_name = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_VM)
            logger.info(
                "Creating vm %s on storage domain %s",
                vm_name, self.storage_domain
            )
            args = config.create_vm_args.copy()
            args['storageDomainName'] = self.storage_domain
            args['vmName'] = vm_name
            args['deep_copy'] = True
            if not storage_helpers.create_vm_or_clone(**args):
                raise exceptions.VMException(
                    "Failed to create or clone VM '%s'" % vm_name
                )
            self.vm_names.append(vm_name)

        self.template_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
        )
        self.first_snapshot_description = (
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
            )
        )
        # Create snapshot for the first vm only
        if not ll_vms.addSnapshot(
            True, self.vm_names[0], self.first_snapshot_description
        ):
            raise exceptions.VMException(
                "Failed to create snapshot on VM '%s'" % self.vm_names[0]
            )

        if self.attach_backup_disk:
            if not ll_vms.attach_backup_disk_to_vm(
                self.vm_names[0], self.vm_names[1],
                self.first_snapshot_description
            ):
                raise exceptions.DiskException(
                    "Failed to attach backup disk to backup vm %s" %
                    self.vm_names[1]
                )

    def tearDown(self):
        """
        Remove created VMs
        """
        if not ll_vms.stop_vms_safely(self.vm_names):
            logger.error(
                "Failed to power off vms %s", ', '.join(self.vm_names)
            )
            BaseTestCase.test_failed = True
        for disk in ll_vms.getVmDisks(self.vm_names[1]):
            if not ll_vms.removeDisk(True, self.vm_names[1], disk.get_alias()):
                logger.error(
                    "Failed to remove disk '%s' from VM '%s'",
                    disk.get_alias(), self.vm_names[1]
                )
                BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        if not ll_vms.safely_remove_vms(self.vm_names):
            logger.error(
                "Failed to power off and remove vms %s",
                ', '.join(self.vm_names)
            )
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


class CreateTemplateFromVM(BaseTestCase):
    """
    Create a template of a backup VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = False

    def _create_template(self):
        """
        Create a template of a backup VM after attaching snapshot disk of
        source VM to backup VM
        """
        logger.info(
            "Creating template of backup vm %s", self.vm_name_for_template
        )
        assert ll_templates.createTemplate(
            True, vm=self.vm_name_for_template, name=self.template_name
        ), "Failed to create template '%s'" % self.template_name

    def tearDown(self):
        """
        Remove template and restoring environment
        """
        if not ll_templates.removeTemplate(True, self.template_name):
            logger.error("Failed to remove template %s", self.template_name)
            BaseTestCase.test_failed = True
        super(CreateTemplateFromVM, self).tearDown()


@attr(tier=2)
class TestCase6178(BaseTestCase):
    """
    Shutdown backup VM with attached snapshot of source vm and verify
    that on VDSM, the folder /var/lib/vdsm/transient is empty and backup
    disk still attached
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6178'

    @polarion("RHEVM3-6178")
    def test_shutdown_backup_vm_with_attached_snapshot(self):
        """
        Shutdown backup VM with attached snapshot
        """
        ll_vms.startVm(True, self.vm_names[1], config.VM_UP, True)
        backup_vm_vdsm_host = ll_vms.get_vm_host(self.vm_names[1])
        backup_vm_vdsm_host_ip = ll_hosts.get_host_ip_from_engine(
            backup_vm_vdsm_host
        )
        assert not (
            helpers.is_transient_directory_empty(backup_vm_vdsm_host_ip)
        ), "Transient directory is empty"
        ll_vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        assert helpers.is_transient_directory_empty(backup_vm_vdsm_host_ip), (
            "Transient directory still contains backup disk volumes"
        )

        source_vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        backup_vm_disks = ll_vms.getVmDisks(self.vm_names[1])
        disk_id = source_vm_disks[0].get_id()
        is_disk_attached = disk_id in [disk.get_id() for disk in
                                       backup_vm_disks]

        assert is_disk_attached, "Backup disk is not attached"


@attr(tier=4)
class TestCase6182(BaseTestCase):
    """
    Restart vdsm / engine while snapshot disk attached to backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6182'

    @polarion("RHEVM3-6182")
    def test_restart_VDSM_and_engine_while_disk_attached_to_backup_vm(self):
        """
        Restart vdsm and engine
        """
        ll_vms.startVm(True, self.vm_names[1], config.VM_UP, True)
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0], self.first_snapshot_description
        )
        snapshot_disk = disk_objects[0]

        dc_obj = ll_dc.get_data_center(config.DATA_CENTER_NAME)
        backup_vm_vdsm_host = ll_vms.get_vm_host(self.vm_names[1])
        backup_vm_vdsm_host_ip = ll_hosts.get_host_ip_from_engine(
            backup_vm_vdsm_host
        )
        checksum_before = ll_disks.checksum_disk(
            backup_vm_vdsm_host_ip, config.HOSTS_USER, config.HOSTS_PW,
            snapshot_disk, dc_obj
        )

        logger.info("Restarting VDSM...")
        assert utils.restartVdsmd(backup_vm_vdsm_host_ip, config.HOSTS_PW), (
            "Failed restarting VDSM service"
        )
        ll_hosts.waitForHostsStates(True, self.host)
        logger.info("Successfully restarted VDSM service")

        vm_disks = ll_vms.getVmDisks(self.vm_names[1])
        status = disk_objects[0].get_alias() in (
            [disk.get_alias() for disk in vm_disks]
        )
        assert status, "Backup disk is not attached after restarting VDSM"

        assert not (
            helpers.is_transient_directory_empty(backup_vm_vdsm_host_ip)
        ), "Transient directory is empty"

        logger.info("Restarting ovirt-engine...")
        utils.restart_engine(config.ENGINE, 5, 30)
        logger.info("Successfully restarted ovirt-engine")

        vm_disks = ll_vms.getVmDisks(self.vm_names[1])
        status = disk_objects[0].get_alias() in (
            [disk.get_alias() for disk in vm_disks]
        )
        assert status, (
            "Backup disk is not attached after restarting ovirt-engine"
        )
        assert not (
            helpers.is_transient_directory_empty(backup_vm_vdsm_host_ip)
        ), "Transient directory is empty"
        logger.info("Transient directory contains backup disk")

        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0], self.first_snapshot_description
        )

        snapshot_disk = disk_objects[0]

        logger.info("Verifying disk is not corrupted")
        dc_obj = ll_dc.get_data_center(config.DATA_CENTER_NAME)
        checksum_after = ll_disks.checksum_disk(
            backup_vm_vdsm_host_ip, config.HOSTS_USER, config.HOSTS_PW,
            snapshot_disk, dc_obj
        )

        assert checksum_before == checksum_after, "Disk is corrupted"
        logger.info("Disk is not corrupted")


@attr(tier=2)
class TestCase6183(BaseTestCase):
    """
    Attach snapshot disk of source VM to backup VM
    Make sure tempfile (i.e. /var/lib/vdsm/transient/) is not created and
    then power on the backup VM and check again
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6183'

    @polarion("RHEVM3-6183")
    def test_temporary_snapshot_is_created_after_backup_vm_starts(self):
        """
        Make sure that before starting backup vm, /var/lib/vdsm/transient/
        will not contain any backup volumes and after starting it, the
        backup volumes will be created
        """
        logger.info(
            "Use the first host which resides on the first cluster to check "
            "the transient directory for the backup disk volumes"
        )
        vdsm_host_name = config.HOSTS[0]
        vdsm_host_ip = ll_hosts.get_host_ip_from_engine(vdsm_host_name)
        logger.info(
            "Updating vm %s to placement host %s", self.vm_names[1],
            vdsm_host_name
        )
        if not ll_vms.updateVm(
            True, self.vm_names[1], placement_host=vdsm_host_name
        ):
            raise exceptions.VMException(
                "Failed to update VM '%s'" % self.vm_names[1]
            )
        assert helpers.is_transient_directory_empty(vdsm_host_ip), (
            "Transient directory contains backup disk volumes before backup "
            "vm '%s' is powered on" % self.vm_names[1]
        )
        logger.info("%s is empty", helpers.TRANSIENT_DIR_PATH)

        logger.info("Starting vm %s", self.vm_names[1])
        assert ll_vms.startVm(
            True, self.vm_names[1], config.VM_UP, True
        ), "Failed to start vm %s" % self.vm_names[1]
        logger.info("vm %s started successfully", self.vm_names[1])
        assert not helpers.is_transient_directory_empty(vdsm_host_ip), (
            "Transient directory should contain backup disk volumes"
        )
        logger.info("%s contain backup volume", helpers.TRANSIENT_DIR_PATH)


@attr(tier=2)
class TestCase6176(BaseTestCase):
    """
    Attach snapshot disk of source VM to running backup VM and Hotplug the
    snapshot disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6176'
    attach_backup_disk = False

    @polarion("RHEVM3-6176")
    def test_attach_and_hotplug_snapshot_disk_of_source_vm_to_backup_vm(self):
        """
        Make sure that before hotplugging the backup disk,
        /var/lib/vdsm/transient/ will not contain any backup volumes and
        after hotplug, the backup volumes will be created
        """
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0], self.first_snapshot_description
        )
        ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            self.first_snapshot_description, activate=False
        )
        ll_vms.startVm(True, self.vm_names[1], config.VM_UP, True)
        backup_vm_vdsm_host = ll_vms.get_vm_host(self.vm_names[1])
        backup_vm_vdsm_host_ip = ll_hosts.get_host_ip_from_engine(
            backup_vm_vdsm_host
        )
        assert helpers.is_transient_directory_empty(backup_vm_vdsm_host_ip), (
            "Transient directory should be empty"
        )
        logger.info("%s is empty on vdsm host", helpers.TRANSIENT_DIR_PATH)

        assert ll_vms.activateVmDisk(
            True, self.vm_names[1], disk_objects[0].get_alias()
        ), "Failed to activate disk %s of vm %s" % (
            disk_objects[0].get_alias(), self.vm_names[1]
        )

        assert not (
            helpers.is_transient_directory_empty(backup_vm_vdsm_host_ip)
        ), "Transient directory should contain backup disk volumes"
        logger.info(
            "%s contains backup volumes on vdsm host after hotplug",
            helpers.TRANSIENT_DIR_PATH
        )


@attr(tier=2)
@bz({'1342783': {}})
class TestCase6174(BaseTestCase):
    """
    Create source VM snapshot, attach snapshot to backup VM
    and try to delete original snapshot of source VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6174'

    @polarion("RHEVM3-6174")
    def test_delete_original_snapshot_while_attached_to_another_vm(self):
        """
        Try to delete original snapshot of source VM that is attached to
        backup VM
        """
        status = ll_vms.removeSnapshot(
            False, self.vm_names[0], self.first_snapshot_description
        )
        if not status:
            raise exceptions.VMException(
                "Succeeded to remove snapshot %s" %
                self.first_snapshot_description
            )


@attr(tier=2)
class TestCase6165(BaseTestCase):
    """
    Try to perform snapshot operations on the source VM:
    - Preview snapshot, undo it
    - Preview snapshot, commit it
    - Delete snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6165'

    @polarion("RHEVM3-6165")
    def test_operations_with_attached_snapshot(self):
        """
        Shut down the source VM
        Try to perform snapshot operations on the source VM:
            - Preview snapshot, undo it
            - Preview snapshot, commit it
            - Delete snapshot

        Create one more snapshot to the source VM
        perform operations on that snapshot (as in step 2)
        """
        logger.info("Previewing snapshot %s", self.first_snapshot_description)
        assert ll_vms.preview_snapshot(
            True, self.vm_names[0], self.first_snapshot_description
        ), "Failed to preview snapshot %s" % self.first_snapshot_description
        ll_vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_IN_PREVIEW,
            self.first_snapshot_description
        )

        logger.info(
            "Undoing Previewed snapshot %s", self.first_snapshot_description
        )
        assert ll_vms.undo_snapshot_preview(
            True, self.vm_names[0], self.first_snapshot_description
        ), "Failed to undo previewed snapshot %s" % (
            self.first_snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_names[0], config.SNAPSHOT_OK)

        logger.info("Previewing snapshot %s", self.first_snapshot_description)
        assert ll_vms.preview_snapshot(
            True, self.vm_names[0], self.first_snapshot_description
        ), "Failed to preview snapshot %s" % self.first_snapshot_description
        ll_vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_IN_PREVIEW,
            self.first_snapshot_description
        )

        logger.info(
            "Committing Previewed snapshot %s", self.first_snapshot_description
        )
        assert ll_vms.commit_snapshot(
            False, self.vm_names[0], self.first_snapshot_description
        ), "Succeeded to commit previewed snapshot %s" % (
            self.first_snapshot_description
        )

        logger.info(
            "Undoing Previewed snapshot %s", self.first_snapshot_description
        )
        assert ll_vms.undo_snapshot_preview(
            True, self.vm_names[0], self.first_snapshot_description
        ), "Failed to undo previewed snapshot %s" % (
            self.first_snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_names[0], config.SNAPSHOT_OK)


@attr(tier=2)
class TestCase6166(CreateTemplateFromVM):
    """
    Create a template of a backup VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6166'

    def setUp(self):
        super(CreateTemplateFromVM, self).setUp()
        self.vm_name_for_template = self.vm_names[1]

    @polarion("RHEVM3-6166")
    def test_create_template_of_backup_vm(self):
        """
        Create a template of a backup VM after attaching snapshot disk of
        source VM to backup VM
        """
        self._create_template()


@attr(tier=2)
class TestCase6167(CreateTemplateFromVM):
    """
    Create a template of a source VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6167'

    def setUp(self):
        super(TestCase6167, self).setUp()
        self.vm_name_for_template = self.vm_names[0]

    @polarion("RHEVM3-6167")
    def test_create_template_of_source_vm(self):
        """
        Create a template of source VM after attaching snapshot disk of
        source VM to backup VM
        """
        self._create_template()


@attr(tier=4)
class TestCase6168(BaseTestCase):
    """
    Block connection from host to storage domain 2 that contains
    snapshot of attached disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    # TODO: fix this case
    # This case is currently not part of the plan but is disabled due to bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1063336 which cause
    # the environment to be unusable after it runs.
    # Even though that i wrote a temporary solution (see below), it doesn't
    # solve the problem completely.
    __test__ = False
    polarion_test_case = '6168'
    storage_domain_ip = None
    blocked = False
    attach_backup_disk = False

    def setUp(self):
        super(TestCase6168, self).setUp()

        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )

        self.host = ll_hosts.getSPMHost(config.HOSTS)
        self.host_ip = ll_hosts.getHostIP(self.host)

        status, self.storage_domain_ip = ll_sd.getDomainAddress(
            True, self.storage_domains[0]
        )
        if not status:
            raise SkipTest(
                "Unable to get storage domain %s address" %
                self.storage_domains[0]
            )

        ll_vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])
        hl_vms.move_vm_disks(self.vm_names[1], self.storage_domains[1])
        ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1], self.first_snapshot_description
        )

    @polarion("RHEVM3-6168")
    def test_storage_failure_of_snapshot(self):
        """
        Test checks that blocking connection from host to storage domain that
        containing the snapshot of attached disk, cause the backup
        vm enter to paused status
        """
        ll_vms.start_vms([self.vm_names[1]], 1, config.VM_UP, True)

        logger.info(
            "Blocking connectivity from host %s to storage domain %s",
            self.host, self.storage_domains[0]
        )

        status = st_api.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip['address']
        )

        if status:
            self.blocked = True

        assert status, "block connectivity to master domain failed"

        ll_vms.waitForVMState(self.vm_names[1], config.VM_PAUSED)

        vm_state = ll_vms.get_vm_state(self.vm_names[1])
        assert vm_state == config.VM_PAUSED, (
            "vm %s should be in state paused" % self.vm_names[1]
        )

    def tearDown(self):
        """
        Detach backup disk
        """
        logger.info(
            "Unblocking connectivity from host %s to storage domain %s",
            self.host, self.storage_domains[0]
        )

        status = st_api.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip['address']
        )

        if not status:
            logger.error(
                "Failed to unblock connectivity from host %s to storage "
                "domain %s", self.host, self.storage_domains[0]
            )
            BaseTestCase.test_failed = True

        super(TestCase6168, self).tearDown()


@attr(tier=1)
@bz({'1358271': {}})
class TestCase6169(BaseTestCase):
    """
    Full flow of backup/restore API
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    # Bugzilla history:
    # 1231849: Creating a vm with configuration fails (like ovf data)
    # 1211670: The CLI doesn't provide a mechanism to escape characters
    # in string literals
    polarion_test_case = '6169'

    def setUp(self):
        super(TestCase6169, self).setUp()
        self.source_vm = self.vm_names[0]
        self.backup_vm = self.vm_names[1]
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.restored_vm = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )

    @polarion("RHEVM3-6169")
    def test_full_flow_of_backup_restore(self):
        """
        Full backup API flow:
        - Attach snapshots disk of source VM to backup VM
        - Backup disk with backup software on backup VM
        - Backup OVF of source VM on backup VM
        - Detach snapshot disk of source VM from backup VM
        - Remove source VM
        - Create new VM (to be restored from OVF)
        - Restore source VM that has backup to newly created VMs

        """
        logger.info("Get ovf configuration file of vm %s", self.source_vm)
        ovf = ll_vms.get_vm_snapshot_ovf_obj(
            self.source_vm, self.first_snapshot_description
        )
        status = ovf is None
        assert not status, "OVF object wasn't found"

        testflow.step("Add second disk (backup disk) to vm %s", self.backup_vm)
        self.backup_disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        assert ll_vms.addDisk(
            True, self.backup_vm, BACKUP_DISK_SIZE, True,
            self.storage_domains[0], interface=config.INTERFACE_VIRTIO,
            alias=self.backup_disk_alias,
        ), "Failed to add backup disk to backup vm %s" % self.backup_vm

        for disk in ll_vms.getVmDisks(self.backup_vm):
            if not ll_vms.is_active_disk(
                self.backup_vm, disk.get_alias(), 'alias'
            ):

                ll_vms.activateVmDisk(True, self.backup_vm, disk.get_alias())
        testflow.step("Starting vms %s", ', '.join(self.vm_names))
        ll_vms.start_vms(self.vm_names, 2, config.VM_UP, True)
        self.backup_vm_ip = storage_helpers.get_vm_ip(self.backup_vm)
        if not self.backup_vm_ip:
            raise exceptions.VMException(
                "Failed to get IP for vm %s" % self.backup_vm
            )
        backup_disk_device = ll_vms.get_vm_disk_logical_name(
            self.backup_vm, self.backup_disk_alias
        ).split('/')[-1]
        source_vm_disk_alias = ll_vms.getVmDisks(self.source_vm)[0].get_alias()
        source_vm_device = ll_vms.get_vm_disk_logical_name(
            self.backup_vm, source_vm_disk_alias
        ).split('/')[-1]
        testflow.step(
            "Copy data from disk %s to %s of backup vm %s",
            source_vm_device, backup_disk_device, self.backup_vm
        )
        status = helpers.copy_backup_disk(
            self.backup_vm_ip, source_vm_device, backup_disk_device,
            timeout=TASK_TIMEOUT
        )

        assert status, "Failed to copy disk"
        testflow.step("Stopping vms %s", self.vm_names)
        ll_vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))

        disk_objects = ll_vms.get_snapshot_disks(
            self.source_vm, self.first_snapshot_description
        )

        testflow.step(
            "Detaching snapshot's disk %s, of source vm %s, from backup vm %s",
            disk_objects[0].get_alias(), self.source_vm, self.backup_vm
        )
        assert ll_disks.detachDisk(
            True, disk_objects[0].get_alias(), self.backup_vm
        ), "Failed to detach disk %s" % disk_objects[0].get_alias()

        testflow.step("Remove source vm %s", self.source_vm)
        if not ll_vms.safely_remove_vms([self.source_vm]):
            raise exceptions.VMException(
                "Failed to power off and remove VM '%s'" % self.source_vm
            )
        self.vm_names.remove(self.source_vm)

        testflow.step(
            "Restoring source vm %s from ovf file", self.source_vm
        )
        status = ll_vms.create_vm_from_ovf(
            self.restored_vm, config.CLUSTER_NAME, ovf
        )
        assert status, "Failed to create vm from ovf configuration"
        self.vm_names.append(self.restored_vm)

        disk_objects = ll_vms.getVmDisks(self.backup_vm)
        disk_to_detach = [
            d.get_alias() for d in disk_objects if not d.get_bootable()
        ][0]
        testflow.step("Detach backup disk from backup vm %s", self.backup_vm)
        assert ll_disks.detachDisk(
            True, disk_to_detach, self.backup_vm
        ), "Failed to detach disk %s from backup vm" % (
            disk_objects[1].get_alias()
        )

        testflow.step("Attach backup disk to restored vm %s", self.restored_vm)
        assert ll_disks.attachDisk(
            True, disk_to_detach, self.restored_vm
        ), "Failed to attach disk %s to restored vm" % (
            disk_objects[1].get_alias()
        )

        assert ll_vms.updateVm(True, self.restored_vm, name=self.source_vm), (
            "Failed to update VM '%s' to use name '%s'" %
            (self.restored_vm, self.source_vm)
        )
        self.vm_names.remove(self.restored_vm)
        self.vm_names.append(self.source_vm)
        testflow.step("Start restored vm %s and wait for IP", self.restored_vm)
        assert ll_vms.startVm(True, self.source_vm, config.VM_UP, True), (
            "Failed to power on source VM '%s'" % self.source_vm
        )


@attr(tier=2)
class TestCase6170(BaseTestCase):
    """
    Attach more than 1 backup disks (i.e. snapshot disks) to backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6170'
    attach_backup_disk = False

    @polarion("RHEVM3-6170")
    def test_attach_multiple_disks(self):
        """
        Create a snapshot to source VM and try to attach all source VM's
        snapshot disks to backup VM
        """
        storage_domain = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_names[0]
        )
        if not ll_vms.addDisk(
            True, self.vm_names[0], 1 * config.GB, True, storage_domain,
            interface=config.INTERFACE_VIRTIO
        ):
            raise exceptions.DiskException(
                "Failed to add disk to vm %s" % self.vm_names[0]
            )

        self.second_snapshot_description = (
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
            )
        )
        assert ll_vms.addSnapshot(
            True, self.vm_names[0], self.second_snapshot_description
        ), "Failed to create snapshot for VM '%s'" % self.vm_names[0]

        assert ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            self.second_snapshot_description
        ), "Failed to attach second snapshot disks to backup vm '%s'" % (
            self.vm_names[1]
        )


@attr(tier=2)
class TestCase6171(BaseTestCase):
    """
    During a vm disk migration, try to attach the snapshot disk to backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6171'
    attach_backup_disk = False

    def setUp(self):
        super(TestCase6171, self).setUp()
        self.vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        self.original_sd = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_names[0], self.vm_disks[0].get_alias()
        )
        storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.destination_sd = [
            sd for sd in storage_domains if sd != self.original_sd
        ][0]

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_MOVE_COPY_DISK])
    @polarion("RHEVM3-6171")
    def test_attach_snapshot_disk_while_the_disk_is_locked(self):
        """
        - Move source vm disk to the second storage domain
        - During the disk movement, try to attach the snapshot disk to the
          backup VM (while the disk is locked)
        """
        ll_vms.move_vm_disk(
            self.vm_names[0], self.vm_disks[0].get_alias(),
            self.destination_sd, False
        )

        ll_disks.wait_for_disks_status(
            disks=self.vm_disks[0].get_alias(), status=config.DISK_LOCKED
        )

        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1], self.first_snapshot_description
        )
        ll_disks.wait_for_disks_status(disks=self.vm_disks[0].get_alias())
        assert not status, (
            "Succeeded to attach backup snapshot disk to backup vm while a "
            "migrate disk operation was in progress"
        )


@attr(tier=2)
class TestCase6172(BaseTestCase):
    """
    Attach snapshot disk to backup vm more than once
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6172'

    @polarion("RHEVM3-6172")
    def test_attach_the_same_disk_twice_to_a_VM(self):
        """
        Attach the snapshot disk of source VM to backup VM and do it again
        """
        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1], self.first_snapshot_description
        )
        assert not status, (
            "Succeeded to attach backup snapshot disk to backup vm"
        )


@attr(tier=2)
class TestCase6173(BaseTestCase):
    """
    During a vm disk live migration, try to attach the snapshot disk to
    backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6173'
    attach_backup_disk = False
    # Bugzilla history:
    # 1176673/1196049:[Rhel7.1] After live storage migration on block storage
    # vdsm # extends migrated drive using all free space in the vg
    # 1251956: Live storage migration is broken
    # 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with
    # id' after live migrate a Virtio RAW disk, job stays in status STARTED

    def setUp(self):
        super(TestCase6173, self).setUp()
        ll_vms.start_vms(self.vm_names, 2, config.VM_UP, True)

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_MOVE_COPY_DISK])
    @polarion("RHEVM3-6173")
    def test_Attach_disk_while_performing_LSM(self):
        """
        Live migrate a disk from the source VM.
        Attach the migrated snapshot disk to a backup VM while the migration
        is taking place
        """
        vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        snapshot_disk_name = vm_disks[0].get_alias()
        self.original_sd = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_names[0], snapshot_disk_name
        )
        storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.destination_sd = [
            sd for sd in storage_domains if sd != self.original_sd
        ][0]

        ll_vms.live_migrate_vm_disk(
            self.vm_names[0], snapshot_disk_name, self.destination_sd,
            wait=False
        )
        ll_disks.wait_for_disks_status(
            [snapshot_disk_name], status=config.DISK_LOCKED
        )
        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1], self.first_snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_names[0], config.SNAPSHOT_OK)
        ll_disks.wait_for_disks_status(
            [snapshot_disk_name], timeout=LIVE_MIGRATE_DISK_TIMEOUT
        )
        assert not status, (
            "Succeeded to attach backup snapshot disk to backup vm"
        )
