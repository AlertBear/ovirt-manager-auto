"""
Storage backup restore API
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Backup_API
"""
import logging

import config
import helpers
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils as utils
import art.rhevm_api.utils.storage_api as st_api
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase
from rhevmtests.storage import helpers as storage_helpers
from utilities.machine import Machine

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

TASK_TIMEOUT = 1500
BACKUP_DISK_SIZE = 10 * config.GB
MOVING_DISK_TIMEOUT = 600

VM_NAMES = {}


def setup_module():
    """
    Prepares environment
    """
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        VM_NAMES[storage_type] = []
        for idx in range(config.VM_COUNT):
            vm_name = "backup_api_vm_%d_%s" % (idx, storage_type)
            logger.info(
                "Creating vm %s on storage domain %s", vm_name, storage_domain
            )
            helpers.prepare_vm(
                vm_name, helpers.SHOULD_CREATE_SNAPSHOT[idx], storage_domain
            )
            VM_NAMES[storage_type].append(vm_name)


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    for storage_type, vm_names in VM_NAMES.iteritems():
        vm_names = filter(ll_vms.does_vm_exist, vm_names)
        ll_vms.stop_vms_safely(vm_names)
        ll_vms.removeVms(True, vm_names)
    ll_jobs.wait_for_jobs([ENUMS['job_remove_vm']])


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    polarion_test_case = None

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        ll_vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        ll_vms.waitForVmsStates(True, self.vm_names)
        if not ll_vms.attach_backup_disk_to_vm(
                self.vm_names[0], self.vm_names[1],
                helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        ):
            raise exceptions.DiskException(
                "Failed to attach backup disk to backup vm %s" %
                self.vm_names[1]
            )

    def tearDown(self):
        """
        Start vm and detach backup disk and start vms
        """
        logger.info('Detaching backup disk')
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        ll_vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))

        if not ll_disks.detachDisk(
                True, disk_objects[0].get_alias(), self.vm_names[1]
        ):
            raise exceptions.DiskException(
                "Failed to remove disk %s" % disk_objects[0].get_alias()
            )


class CreateTemplateFromVM(BaseTestCase):
    """
    Create a template of a backup VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = False
    template_name = "%s-template"

    def _create_template(self):
        """
        Create a template of a backup VM after attaching snapshot disk of
        source VM to backup VM
        """
        if not ll_vms.get_vm_state(self.vm_name_for_template) == (
                config.VM_DOWN
        ):
            self.assertTrue(
                ll_vms.stopVm(True, self.vm_name_for_template),
                "Failed to shutdown vm %s" % self.vm_name_for_template
            )

        logger.info("Creating template of backup vm %s",
                    self.vm_name_for_template)

        self.assertTrue(
            ll_templates.createTemplate(
                True, vm=self.vm_name_for_template,
                name=self.template_name % self.vm_name_for_template
            ), "Failed to create template"
        )

    def tearDown(self):
        """
        Remove template and restoring environment
        """
        if not ll_templates.removeTemplate(
                True, self.template_name % self.vm_name_for_template
        ):

            template_name = self.template_name % self.vm_name_for_template
            raise exceptions.TemplateException(
                "Failed to remove template %s" % template_name
            )

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
        self.host = ll_vms.getVmHost(self.vm_names[1])[1]['vmHoster']
        self.host_ip = ll_hosts.getHostIP(self.host)
        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory is empty")
        ll_vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        self.assertTrue(helpers.is_transient_directory_empty(self.host_ip),
                        "Transient directory still "
                        "contains backup disk volumes")

        source_vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        backup_vm_disks = ll_vms.getVmDisks(self.vm_names[1])
        disk_id = source_vm_disks[0].get_id()
        is_disk_attached = disk_id in [disk.get_id() for disk in
                                       backup_vm_disks]

        self.assertTrue(is_disk_attached, "Backup disk is not attached")


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
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        snapshot_disk = disk_objects[0]

        datacenter_obj = ll_dc.get_data_center(
            config.DATA_CENTER_NAME
        )
        self.host = ll_vms.getVmHost(self.vm_names[1])[1]['vmHoster']
        self.host_ip = ll_hosts.getHostIP(self.host)
        checksum_before = ll_disks.checksum_disk(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, snapshot_disk,
            datacenter_obj
        )

        logger.info("Restarting VDSM...")
        self.assertTrue(utils.restartVdsmd(self.host_ip, config.HOSTS_PW),
                        "Failed restarting VDSM service")
        ll_hosts.waitForHostsStates(True, self.host)
        logger.info("Successfully restarted VDSM service")

        vm_disks = ll_vms.getVmDisks(self.vm_names[1])
        status = disk_objects[0].get_alias() in (
            [disk.get_alias() for disk in vm_disks]
        )
        self.assertTrue(status, "Backup disk is not attached after "
                                "restarting VDSM")

        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory is empty")

        logger.info("Restarting ovirt-engine...")
        utils.restart_engine(config.ENGINE, 5, 30)
        logger.info("Successfully restarted ovirt-engine")

        vm_disks = ll_vms.getVmDisks(self.vm_names[1])
        status = disk_objects[0].get_alias() in [disk.get_alias() for
                                                 disk in vm_disks]
        self.assertTrue(status, "Backup disk is not attached after "
                                "restarting ovirt-engine")
        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory is empty")
        logger.info("Transient directory contains backup disk")

        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        snapshot_disk = disk_objects[0]

        logger.info("Verifying disk is not corrupted")
        datacenter_obj = ll_dc.get_data_center(
            config.DATA_CENTER_NAME
        )
        checksum_after = ll_disks.checksum_disk(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, snapshot_disk,
            datacenter_obj
        )

        self.assertEqual(checksum_before, checksum_after, "Disk is corrupted")
        logger.info("Disk is not corrupted")


@attr(tier=2)
class TestCase6183(BaseTestCase):
    """
    Attach snapshot disk of source VM to backup VM
    Make sure tempfile (i.e. /var/lib/vdsm/transient/) is not created
    and then Start backup VM and check again
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6183'

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        ll_vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        self.host = ll_hosts.get_cluster_hosts(config.CLUSTER_NAME)[0]
        self.host_ip = ll_hosts.getHostIP(self.host)
        logger.info("Updating vm %s to placement host %s",
                    self.vm_names[1], self.host)
        assert ll_vms.updateVm(
            True, self.vm_names[1], placement_host=self.host
        )
        ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

    @polarion("RHEVM3-6183")
    def test_temporary_snapshot_is_created_after_backup_vm_starts(self):
        """
        Make sure that before starting backup vm, /var/lib/vdsm/transient/
        will not contain any backup volumes and after starting it, the
        backup volumes will be created
        """
        self.assertTrue(helpers.is_transient_directory_empty(self.host_ip),
                        "Transient directory still "
                        "contains backup disk volumes")
        logger.info("%s is empty", helpers.TRANSIENT_DIR_PATH)

        logger.info("Starting vm %s", self.vm_names[1])
        self.assertTrue(
            ll_vms.startVm(
                True, self.vm_names[1], wait_for_status=config.VM_UP
            ), "Failed to start vm %s" % self.vm_names[1]
        )
        self.host_ip = ll_hosts.getHostIP(self.host)
        logger.info("vm %s started successfully", self.vm_names[1])

        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory should contain "
                         "backup disk volumes")
        logger.info("%s contain backup volume", helpers.TRANSIENT_DIR_PATH)


@attr(tier=2)
class TestCase6176(BaseTestCase):
    """
    Attach snapshot disk of source VM to running backup VM
    and Hotplug the snapshot disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6176'

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        ll_vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        ll_vms.waitForVmsStates(True, self.vm_names)

    @polarion("RHEVM3-6176")
    def test_attach_and_hotplug_snapshot_disk_of_source_vm_to_backup_vm(self):
        """
        Make sure that before hotplugging the backup disk,
        /var/lib/vdsm/transient/
        will not contain any backup volumes and after hotplug, the
        backup volumes will be created
        """
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0], activate=False
        )

        self.host = ll_vms.getVmHost(self.vm_names[1])[1]['vmHoster']
        self.host_ip = ll_hosts.getHostIP(self.host)
        self.assertTrue(helpers.is_transient_directory_empty(self.host_ip),
                        "Transient directory should be empty")
        logger.info("%s is empty", helpers.TRANSIENT_DIR_PATH)

        self.assertTrue(
            ll_vms.activateVmDisk(
                True, self.vm_names[1], disk_objects[0].get_alias()
            ), "Failed to activate disk %s of vm %s" % (
                disk_objects[0].get_alias(), self.vm_names[1]
            )
        )

        self.assertFalse(
            helpers.is_transient_directory_empty(self.host_ip),
            "Transient directory should contain backup disk volumes"
        )
        logger.info("%s contains backup volume after hotplug",
                    helpers.TRANSIENT_DIR_PATH)


@attr(tier=2)
class TestCase6174(BaseTestCase):
    """
    Create source VM snapshot, attach snapshot to backup VM
    and try to delete original snapshot of source VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6174'
    snap_desc = None

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        self.snap_desc = helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        super(TestCase6174, self).setUp()

    @polarion("RHEVM3-6174")
    def test_delete_original_snapshot_while_attached_to_another_vm(self):
        """
        Try to delete original snapshot of source VM that is attached to
        backup VM
        """
        logger.info(
            "Removing snapshot %s of vm %s while vm is powering off, this is "
            "expected to fail",
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0], self.vm_names[0]
        )
        if not ll_vms.stopVm(True, self.vm_names[0], async='true'):
            raise exceptions.VMException(
                "Failed to power off vm %s" % self.vm_names[0]
            )
        status = ll_vms.removeSnapshot(
            False, self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )
        ll_vms.waitForVMState(self.vm_names[0], config.VM_DOWN)
        if not status:
            raise exceptions.VMException(
                "Succeeded to remove snapshot %s" % self.snap_desc
            )


@attr(tier=2)
class TestCase6165(TestCase):
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
    snapshot_name_format = "%s-%s"

    first_snapshot = ""
    second_snapshot = ""

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        self.first_snapshot = (
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        self.second_snapshot = self.snapshot_name_format % (
            "second", helpers.SNAPSHOT_TEMPLATE_DESC
            % self.vm_names[0]
        )

        ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1], self.first_snapshot
        )

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
        ll_vms.stop_vms_safely([self.vm_names[0]])
        logger.info("Succeeded to stop vm %s", self.vm_names[0])

        logger.info("Previewing snapshot %s", self.first_snapshot)
        self.assertTrue(
            ll_vms.preview_snapshot(
                True, self.vm_names[0], self.first_snapshot
            ), "Failed to preview snapshot %s" % self.first_snapshot
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_IN_PREVIEW,  self.first_snapshot
        )

        logger.info("Undoing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(ll_vms.undo_snapshot_preview(
            True, self.vm_names[0], self.first_snapshot
        ),
            "Failed to undo previewed snapshot %s" % self.first_snapshot)
        ll_vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_OK,  self.first_snapshot
        )

        logger.info("Previewing snapshot %s", self.first_snapshot)
        self.assertTrue(
            ll_vms.preview_snapshot(
                True, self.vm_names[0], self.first_snapshot
            ), "Failed to preview snapshot %s" % self.first_snapshot
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_IN_PREVIEW,  self.first_snapshot
        )

        logger.info("Committing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(ll_vms.commit_snapshot(
            False, self.vm_names[0], self.first_snapshot
        ),
            "Succeeded to commit previewed snapshot %s" % self.first_snapshot)

        logger.info("Undoing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(ll_vms.undo_snapshot_preview(
            True, self.vm_names[0], self.first_snapshot
        ),
            "Failed to undo previewed snapshot %s" % self.first_snapshot)

    def tearDown(self):
        """
        Detach backup disk
        """
        logger.info('Detaching backup disk')
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        if not ll_disks.detachDisk(
                True, disk_objects[0].get_alias(), self.vm_names[1]
        ):
            raise exceptions.DiskException(
                "Failed to remove disk %s" % disk_objects[0].get_alias()
            )
        ll_vms.start_vms(
            [self.vm_names[0]], 1, wait_for_status=config.VM_UP,
            wait_for_ip=False
        )


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
class TestCase6168(TestCase):
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

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]

        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )

        self.host = ll_hosts.getSPMHost(config.HOSTS)
        self.host_ip = ll_hosts.getHostIP(self.host)

        status, self.storage_domain_ip = ll_sd.getDomainAddress(
            True, self.storage_domains[0]
        )
        if not status:
            raise exceptions.SkipTest("Unable to get storage domain %s "
                                      "address" % self.storage_domains[0])

        ll_vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        if not ll_vms.moveVm(True, self.vm_names[1], self.storage_domains[1]):
            raise exceptions.VMException("Failed to move vm %s to storage "
                                         "domain %s"
                                         % (self.vm_names[1],
                                            self.storage_domains[1]))

        ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

    @polarion("RHEVM3-6168")
    def test_storage_failure_of_snapshot(self):
        """
        Test checks that blocking connection from host to storage domain that
        containing the snapshot of attached disk, cause the backup
        vm enter to paused status
        """

        ll_vms.start_vms([self.vm_names[1]], 1, wait_for_ip=False)
        ll_vms.waitForVmsStates(True, [self.vm_names[1]])

        logger.info("Blocking connectivity from host %s to storage domain %s",
                    self.host, self.storage_domains[0])

        status = st_api.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip['address'])

        if status:
            self.blocked = True

        self.assertTrue(status, "block connectivity to master domain failed")

        ll_vms.waitForVMState(self.vm_names[1], state=config.VM_PAUSED)

        vm_state = ll_vms.get_vm_state(self.vm_names[1])
        self.assertEqual(vm_state, config.VM_PAUSED,
                         "vm %s should be in state paused"
                         % self.vm_names[1])

    def tearDown(self):
        """
        Detach backup disk
        """
        logger.info("Unblocking connectivity from host %s to storage domain "
                    "%s", self.host, self.storage_domains[0])

        status = st_api.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip['address'])

        if not status:
            raise exceptions.HostException(
                "Failed to unblock connectivity from host %s to "
                "storage domain %s" % (
                    self.host,
                    self.storage_domains[0]
                )
            )

        ll_vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        if not ll_vms.moveVm(True, self.vm_names[1], self.storage_domains[0]):
            raise exceptions.VMException("Failed to move vm %s to storage "
                                         "domain %s"
                                         % (self.vm_names[1],
                                            self.storage_domains[0]))

        logger.info('Detaching backup disk')
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        if not ll_disks.detachDisk(
                True, disk_objects[0].get_alias(), self.vm_names[1]
        ):
            raise exceptions.DiskException(
                "Failed to remove disk %s" % disk_objects[0].get_alias()
            )

        ll_vms.start_vms(self.vm_names[1], 1, wait_for_ip=False)


@attr(tier=1)
class TestCase6169(TestCase):
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
        self.vm_names = VM_NAMES[self.storage]
        self.source_vm = self.vm_names[0]
        self.backup_vm = self.vm_names[1]
        ll_vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        assert ll_vms.waitForVmsStates(True, self.vm_names)
        self.backup_vm_ip = storage_helpers.get_vm_ip(self.backup_vm)
        assert self.backup_vm_ip is not None
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
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
        - Create new VM (restored_vm)
        - Restore source VM that has backup to newly created VMs

        """
        logger.info("Starting to backup vm %s", self.source_vm)
        status = ll_vms.attach_backup_disk_to_vm(
            self.source_vm, self.backup_vm,
            helpers.SNAPSHOT_TEMPLATE_DESC % self.source_vm
        )

        self.assertTrue(
            status, "Failed to attach backup snapshot disk to backup vm"
        )

        logger.info("Get ovf configuration file of vm %s", self.source_vm)
        ovf = ll_vms.get_vm_snapshot_ovf_obj(
            self.source_vm, helpers.SNAPSHOT_TEMPLATE_DESC % self.source_vm
        )
        status = ovf is None
        self.assertFalse(status, "OVF object wasn't found")

        logger.info("Adding backup disk to vm %s", self.backup_vm)
        self.assertTrue(
            ll_vms.addDisk(
                True, self.backup_vm, BACKUP_DISK_SIZE, True,
                self.storage_domains[0], interface=config.INTERFACE_VIRTIO
            ), "Failed to add backup disk to backup vm %s" % self.backup_vm
        )

        for disk in ll_vms.getVmDisks(self.backup_vm):
            if not ll_vms.check_VM_disk_state(
                    self.backup_vm, disk.get_alias()
            ):
                ll_vms.activateVmDisk(True, self.backup_vm, disk.get_alias())

        linux_machine = Machine(
            host=self.backup_vm_ip, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW).util('linux')

        devices = linux_machine.get_storage_devices()

        logger.info("Copy disk from %s to %s", devices[1], devices[2])
        status = helpers.copy_backup_disk(
            self.backup_vm_ip, devices[1], devices[2], timeout=TASK_TIMEOUT
        )

        self.assertTrue(status, "Failed to copy disk")

        ll_vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))

        disk_objects = ll_vms.get_snapshot_disks(
            self.source_vm,
            helpers.SNAPSHOT_TEMPLATE_DESC % self.source_vm)

        self.assertTrue(
            ll_disks.detachDisk(
                True, disk_objects[0].get_alias(), self.backup_vm
            ), "Failed to detach disk %s" % disk_objects[0].get_alias()
        )

        ll_vms.safely_remove_vms([self.source_vm])

        logger.info("Restoring vm %s", self.source_vm)
        status = ll_vms.create_vm_from_ovf(
            helpers.RESTORED_VM, config.CLUSTER_NAME, ovf
        )
        self.assertTrue(status, "Failed to create vm from ovf configuration")

        disk_objects = ll_vms.getVmDisks(self.backup_vm)
        disk_to_detach = [
            d.get_alias() for d in disk_objects if not d.get_bootable()
        ][0]
        self.assertTrue(
            ll_disks.detachDisk(
                True, disk_to_detach, self.backup_vm
            ), "Failed to detach disk %s from backup vm" %
               disk_objects[1].get_alias()
        )

        self.assertTrue(
            ll_disks.attachDisk(
                True, disk_to_detach, helpers.RESTORED_VM
            ), "Failed to attach disk %s to restored vm" %
               disk_objects[1].get_alias()
        )

        ll_vms.updateVm(True, helpers.RESTORED_VM, name=self.source_vm)

        ll_vms.start_vms(self.vm_names, 2, wait_for_ip=True)

    def tearDown(self):
        """
        Creating a snapshot for source vm
        """
        if not ll_vms.addSnapshot(
            positive=True, vm=self.source_vm,
            description=helpers.SNAPSHOT_TEMPLATE_DESC % self.source_vm
        ):
            logger.error("Filed to create snapshot on vm %s", self.source_vm)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs([ENUMS['job_create_snapshot']])
        TestCase.teardown_exception()


@attr(tier=2)
class TestCase6170(TestCase):
    """
    Attach more than 1 backup disks (i.e. snapshot disks) to backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6170'
    snapshot_template_name = "%s-snapshot"

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]

    @polarion("RHEVM3-6170")
    def test_attach_multiple_disks(self):
        """
         Create a snapshot to source VM and
         try to attach all source VM's snapshot disks to backup VM
        """
        storage_domain = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_names[0])
        if not ll_vms.addDisk(
                True, self.vm_names[0], 6 * config.GB, True, storage_domain,
                interface=config.INTERFACE_VIRTIO
        ):
            raise exceptions.DiskException(
                "Failed to add disk to vm %s" % self.vm_names[0]
            )
        ll_vms.addSnapshot(
            True, vm=self.vm_names[0],
            description=self.snapshot_template_name % self.vm_names[0])

        self.assertTrue(
            ll_vms.attach_backup_disk_to_vm(
                self.vm_names[0], self.vm_names[1],
                self.snapshot_template_name % self.vm_names[0]
            ), "Failed to attach all snapshot disks to backup vm"
        )

    def tearDown(self):
        """
        Restoring the environment
        """
        logger.info('Detaching backup disk')
        disk_objects = ll_vms.get_snapshot_disks(
            self.vm_names[0],
            self.snapshot_template_name % self.vm_names[0])

        for disk_obj in disk_objects:
            if not ll_disks.detachDisk(
                    True, disk_obj.get_alias(), self.vm_names[1]
            ):
                raise exceptions.DiskException(
                    "Failed to remove disk %s" % disk_obj.get_alias()
                )
        ll_vms.stop_vms_safely([self.vm_names[0]])
        logger.info("Succeeded to stop vm %s", self.vm_names[0])

        if not ll_vms.removeSnapshot(
                True, self.vm_names[0],
                self.snapshot_template_name % self.vm_names[0]
        ):
            snapshot_name = self.snapshot_template_name % self.vm_names[0]
            raise exceptions.VMException("Failed to remove snapshot %s"
                                         % snapshot_name)

        disks_to_remove = ll_vms.getVmDisks(self.vm_names[0])
        for disk in disks_to_remove:
            if not disk.get_bootable():
                ll_vms.removeDisk(True, self.vm_names[0], disk.get_alias())
                logger.info("Disk %s - removed", disk.get_alias())


@attr(tier=2)
class TestCase6171(TestCase):
    """
    During a vm disk migration, try to attach the snapshot disk to backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6171'

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        ll_vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))
        self.vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        self.original_sd = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_names[0], self.vm_disks[0].get_alias())
        storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.destination_sd = [
            sd for sd in storage_domains if sd != self.original_sd][0]

    @polarion("RHEVM3-6171")
    def test_attach_snapshot_disk_while_the_disk_is_locked(self):
        """
        - Move source vm disk to the second storage domain
        - During the disk movement, try to attach the snapshot disk to the
          backup VM (while the disk is locked)
        """
        ll_vms.move_vm_disk(
            self.vm_names[0], self.vm_disks[0].get_alias(),
            self.destination_sd, wait=False
        )

        ll_disks.wait_for_disks_status(
            disks=self.vm_disks[0].get_alias(),
            status=config.DISK_LOCKED
        )

        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        self.assertFalse(
            status, "Succeeded to attach backup snapshot disk to backup vm"
        )

    def tearDown(self):
        """
        Restoring environment
        """
        vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        # Waiting for the disk's move operation from the test to finish
        ll_disks.wait_for_disks_status(
            vm_disks[0].get_alias(), timeout=MOVING_DISK_TIMEOUT
        )
        logger.info("Moving disk %s to SD %s", vm_disks[0].get_alias(),
                    self.original_sd)
        ll_vms.move_vm_disk(
            self.vm_names[0], vm_disks[0].get_alias(), self.original_sd,
            wait=True
        )
        ll_disks.wait_for_disks_status(
            vm_disks[0].get_alias(), timeout=MOVING_DISK_TIMEOUT
        )
        ll_jobs.wait_for_jobs([ENUMS['job_move_or_copy_disk']])


@attr(tier=2)
class TestCase6172(BaseTestCase):
    """
    Attach snapshot disk to backup vm more than once
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6172'

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]

    @polarion("RHEVM3-6172")
    def test_attach_the_same_disk_twice_to_a_VM(self):
        """
        Attach the snapshot disk of source VM to backup VM and
        do it again
        """
        ll_vms.waitForDisksStat(self.vm_names[0])
        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        self.assertTrue(
            status, "Failed to attach backup snapshot disk to backup vm"
        )

        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        self.assertFalse(
            status, "Succeeded to attach backup snapshot disk to backup vm"
        )


@attr(tier=2)
class TestCase6173(TestCase):
    """
    During a vm disk live migration,
    try to attach the snapshot disk to backup vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Backup_API
    """
    __test__ = True
    polarion_test_case = '6173'
    # Bugzilla history:
    # 1176673 1196049
    bz = {
        '1251956': {'engine': None, 'version': ['3.6']},
        '1259785': {'engine': None, 'version': ['3.6']},
    }

    def setUp(self):
        self.vm_names = VM_NAMES[self.storage]
        ll_vms.waitForDisksStat(self.vm_names[0])
        ll_vms.waitForDisksStat(self.vm_names[1])
        ll_vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        ll_vms.waitForVmsStates(True, self.vm_names)

    @polarion("RHEVM3-6173")
    def test_Attach_disk_while_performing_LSM(self):
        """
        Live migrate a disk from the source VM.
        Attach the migrated snapshot disk to a backup VM while
        the migration is taking place
        """
        vm_disks = ll_vms.getVmDisks(self.vm_names[0])
        self.original_sd = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_names[0], vm_disks[0].get_alias())
        storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.destination_sd = [
            sd for sd in storage_domains if sd != self.original_sd][0]

        ll_vms.move_vm_disk(
            self.vm_names[0], vm_disks[0].get_alias(), self.destination_sd,
            wait=False
        )

        status = ll_vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )
        self.assertFalse(
            status, "Succeeded to attach backup snapshot disk to backup vm"
        )

    def tearDown(self):
        """
        Wait for all disk to be in status OK
        """
        logger.info("Waiting for all disk to be in status OK")
        ll_vms.waitForDisksStat(self.vm_names[0], timeout=MOVING_DISK_TIMEOUT)
        ll_vms.waitForDisksStat(self.vm_names[1])
