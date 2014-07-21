"""
Storage backup restore API - 10435
https://tcms.engineering.redhat.com/plan/10435
"""

import logging
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import templates, hosts
from art.rhevm_api.tests_lib.low_level.datacenters import get_data_center
from art.unittest_lib import attr

import art.rhevm_api.utils.storage_api as st_api

from art.rhevm_api.utils import test_utils as utils

from utilities.machine import Machine

from art.test_handler.tools import tcms, bz
from art.test_handler import exceptions

import helpers
import config


logger = logging.getLogger(__name__)

TASK_TIMEOUT = 1500

TEST_PLAN_ID = '10435'


def setup_module():
    """
    Prepares environment
    """
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.TESTNAME)

    for index in range(config.VM_COUNT):
        helpers.prepare_vm(
            helpers.VM_NAMES[index],
            create_snapshot=helpers.SHOULD_CREATE_SNAPSHOT[index])


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DC_NAME, vdc=config.VDC,
                                   vdc_password=config.VDC_PASSWORD)


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_test_case = None

    @classmethod
    def setup_class(cls):
        vms.start_vms(helpers.VM_NAMES, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, helpers.VM_NAMES)
        if not vms.attach_backup_disk_to_vm(helpers.VM_NAMES[0],
                                            helpers.VM_NAMES[1],
                                            helpers.SNAPSHOT_TEMPLATE_DESC
                                            % helpers.VM_NAMES[0]):
            raise exceptions.DiskException("Failed to attach backup disk "
                                           "to backup vm %s"
                                           % helpers.VM_NAMES[1])

    @classmethod
    def teardown_class(cls):
        """
        Start vm and detach backup disk and start vms
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        vms.stop_vms_safely(helpers.VM_NAMES)
        logger.info("Succeeded to stop vms %s", ', '.join(helpers.VM_NAMES))

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                helpers.VM_NAMES[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())


class CreateTemplateFromVM(BaseTestCase):
    """
    Create a template of a backup VM
    https://tcms.engineering.redhat.com/case/304166/?from_plan=10435
    """
    __test__ = False
    template_name = "%s-template"
    vm_name_for_template = None

    def create_template(self):
        """
        Create a template of a backup VM after attaching snapshot disk of
        source VM to backup VM
        """
        if not vms.get_vm_state(self.vm_name_for_template) == config.VM_DOWN:
            self.assertTrue(vms.stopVm(True,
                                       self.vm_name_for_template,
                                       async='true'),
                            "Failed to shutdown vm %s"
                            % self.vm_name_for_template)

        logger.info("Creating template of backup vm %s",
                    self.vm_name_for_template)

        self.assertTrue(templates.createTemplate(
            True, vm=self.vm_name_for_template,
            name=self.template_name % self.vm_name_for_template),
            "Failed to create template")

    def tearDown(self):
        """
        Remove template and restoring environment
        """
        if not templates.removeTemplate(True, self.template_name
                                        % self.vm_name_for_template):

            template_name = self.template_name % self.vm_name_for_template
            raise exceptions.TemplateException("Failed to remove template %s"
                                               % template_name)

        super(CreateTemplateFromVM, self).teardown_class()


@attr(tier=1)
class TestCase303842(BaseTestCase):
    """
    Shutdown backup VM with attached snapshot of source vm and verify
    that on VDSM, the folder /var/lib/vdsm/transient is empty and backup
    disk still attached
    https://tcms.engineering.redhat.com/case/303842/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '303842'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_shutdown_backup_vm_with_attached_snapshot(self):
        """
        Shutdown backup VM with attached snapshot
        """
        self.assertFalse(helpers.is_transient_directory_empty(),
                         "Transient directory is empty")
        vms.stop_vms_safely([helpers.VM_NAMES[1]])
        logger.info("Succeeded to stop vm %s", helpers.VM_NAMES[1])

        self.assertTrue(helpers.is_transient_directory_empty(),
                        "Transient directory still "
                        "contains backup disk volumes")

        source_vm_disks = vms.getVmDisks(helpers.VM_NAMES[0])
        backup_vm_disks = vms.getVmDisks(helpers.VM_NAMES[1])
        disk_id = source_vm_disks[0].get_id()
        is_disk_attached = disk_id in [disk.get_id() for disk in
                                       backup_vm_disks]

        self.assertTrue(is_disk_attached, "Backup disk is not attached")


@attr(tier=2)
class TestCase303854(BaseTestCase):
    """
    Restart vdsm / engine while snapshot disk attached to backup vm
    https://tcms.engineering.redhat.com/case/303854/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '303854'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_restart_VDSM_and_engine_while_disk_attached_to_backup_vm(self):
        """
        Restart vdsm and engine
        """
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        snapshot_disk = disks_objs[0]

        datacenter_obj = get_data_center(config.DC_NAME)
        checksum_before = disks.checksum_disk(config.HOSTS[0],
                                              config.VDS_USER[0],
                                              config.VDS_PASSWORD[0],
                                              snapshot_disk,
                                              datacenter_obj)

        logger.info("Restarting VDSM...")
        host_name = vms.getVmHost(helpers.VM_NAMES[0])[1]['vmHoster']
        self.assertTrue(utils.restartVdsmd(host_name, config.VDS_PASSWORD[0]),
                        "Failed restarting VDSM service")
        hosts.waitForHostsStates(True, config.HOSTS[0])
        logger.info("Successfully restarted VDSM service")

        vm_disks = vms.getVmDisks(helpers.VM_NAMES[1])
        status = disks_objs[0].get_alias() in \
            [disk.get_alias() for disk in vm_disks]
        self.assertTrue(status, "Backup disk is not attached after "
                                "restarting VDSM")

        self.assertFalse(helpers.is_transient_directory_empty(),
                         "Transient directory is empty")

        engine = config.VDC
        engine_object = Machine(
            host=engine,
            user=config.VDS_USER[0],
            password=config.VDS_PASSWORD[0]).util('linux')

        logger.info("Restarting ovirt-engine...")
        self.assertTrue(utils.restartOvirtEngine(engine_object, 5, 30, 30),
                        "Failed restarting ovirt-engine")
        logger.info("Successfully restarted ovirt-engine")

        vm_disks = vms.getVmDisks(helpers.VM_NAMES[1])
        status = disks_objs[0].get_alias() in [disk.get_alias() for
                                               disk in vm_disks]
        self.assertTrue(status, "Backup disk is not attached after "
                                "restarting ovirt-engine")
        self.assertFalse(helpers.is_transient_directory_empty(),
                         "Transient directory is empty")
        logger.info("transient directory contains backup disk")

        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        snapshot_disk = disks_objs[0]

        logger.info("Verifying disk is not corrupted")
        datacenter_obj = get_data_center(config.DC_NAME)
        checksum_after = disks.checksum_disk(config.HOSTS[0],
                                             config.VDS_USER[0],
                                             config.VDS_PASSWORD[0],
                                             snapshot_disk,
                                             datacenter_obj)

        self.assertEqual(checksum_before, checksum_after, "Disk is corrupted")
        logger.info("Disk is not corrupted")


@attr(tier=1)
class TestCase304134(BaseTestCase):
    """
    Attach snapshot disk of source VM to backup VM
    Make sure tempfile (i.e. /var/lib/vdsm/transient/) is not created
    and then Start backup VM and check again
    https://tcms.engineering.redhat.com/case/304134/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304134'

    @classmethod
    def setup_class(cls):
        vms.stop_vms_safely([helpers.VM_NAMES[1]])
        logger.info("Succeeded to stop vm %s", helpers.VM_NAMES[1])

        vms.attach_backup_disk_to_vm(helpers.VM_NAMES[0],
                                     helpers.VM_NAMES[1],
                                     helpers.SNAPSHOT_TEMPLATE_DESC
                                     % helpers.VM_NAMES[0])

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_temporary_snapshot_is_created_after_backup_vm_starts(self):
        """
        Make sure that before starting backup vm, /var/lib/vdsm/transient/
        will not contain any backup volumes and after starting it, the
        backup volumes will create
        """

        self.assertTrue(helpers.is_transient_directory_empty(),
                        "Transient directory still "
                        "contains backup disk volumes")
        logger.info("%s is empty", helpers.TRANSIENT_DIR_PATH)

        logger.info("Starting vm %s", helpers.VM_NAMES[1])
        self.assertTrue(vms.startVm(
            True, helpers.VM_NAMES[1],
            wait_for_status=config.VM_UP),
            "Failed to start vm %s" % (helpers.VM_NAMES[1]))

        logger.info("vm %s started successfully", helpers.VM_NAMES[1])

        self.assertFalse(helpers.is_transient_directory_empty(),
                         "Transient directory should contain "
                         "backup disk volumes")
        logger.info("%s contain backup volume", helpers.TRANSIENT_DIR_PATH)


@attr(tier=0)
class TestCase304156(BaseTestCase):
    """
    Attach snapshot disk of source VM to running backup VM
    and Hotplug the snapshot disk
    https://tcms.engineering.redhat.com/case/304156/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304156'

    @classmethod
    def setup_class(cls):
        vms.start_vms(helpers.VM_NAMES, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, helpers.VM_NAMES)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_and_hotplug_snapshot_disk_of_source_vm_to_backup_vm(self):
        """
        Make sure that before hotplugging the backup disk,
        /var/lib/vdsm/transient/
        will not contain any backup volumes and after hotplug, the
        backup volumes will be created
        """
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        vms.attach_backup_disk_to_vm(helpers.VM_NAMES[0],
                                     helpers.VM_NAMES[1],
                                     helpers.SNAPSHOT_TEMPLATE_DESC
                                     % helpers.VM_NAMES[0],
                                     activate=False)

        self.assertTrue(helpers.is_transient_directory_empty(),
                        "Transient directory should be empty")
        logger.info("%s is empty", helpers.TRANSIENT_DIR_PATH)

        self.assertTrue(vms.activateVmDisk(True, helpers.VM_NAMES[1],
                                           disks_objs[0].get_alias()),
                        "Failed to activate disk %s of vm %s"
                        % (disks_objs[0].get_alias(), helpers.VM_NAMES[1]))

        self.assertFalse(helpers.is_transient_directory_empty(),
                         "Transient directory should"
                         "contain backup disk volumes")
        logger.info("%s contains backup volume after hotplug",
                    helpers.TRANSIENT_DIR_PATH)


@attr(tier=1)
class TestCase304159(BaseTestCase):
    """
    Create source VM snapshot, attach snapshot to backup VM
    and try to delete original snapshot of source VM
    https://tcms.engineering.redhat.com/case/304159/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304159'
    snap_desc = None

    @classmethod
    def setup_class(cls):
        cls.snap_desc = helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0]
        super(TestCase304159, cls).setup_class()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_delete_original_snapshot_while_attached_to_another_vm(self):
        """
        Try to delete original snapshot of source VM that is attached to
        backup VM
        """
        vms.attach_backup_disk_to_vm(helpers.VM_NAMES[0],
                                     helpers.VM_NAMES[1],
                                     self.snap_desc)

        logger.info("Removing snapshot %s of vm %s",
                    helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0],
                    helpers.VM_NAMES[0])

        self.assertTrue(vms.stopVm(True, helpers.VM_NAMES[0],
                                   async='true'),
                        "Failed to shutdown vm %s" % helpers.VM_NAMES[0])

        status = vms.removeSnapshot(True, helpers.VM_NAMES[0],
                                    helpers.SNAPSHOT_TEMPLATE_DESC
                                    % helpers.VM_NAMES[0])

        self.assertFalse(status, "Succeeded to remove snapshot %s"
                                 % self.snap_desc)


@attr(tier=1)
class TestCase304161(TestCase):
    """
    Try to perform snapshot operations on the source VM:
    - Preview snapshot, undo it
    - Preview snapshot, commit it
    - Delete snapshot
    https://tcms.engineering.redhat.com/case/304161/?from_plan=10435

    This case is currently __test__ = False because snapshot operation are
    currently
    missing from REST API:
    https://bugzilla.redhat.com/show_bug.cgi?id=867339
    """
    __test__ = False
    tcms_test_case = '304161'
    snapshot_name_format = "%s-%s"

    first_snapshot = ""
    second_snapshot = ""

    @classmethod
    def setup_class(cls):
        cls.first_snapshot = helpers.SNAPSHOT_TEMPLATE_DESC \
            % helpers.VM_NAMES[0]

        cls.second_snapshot = cls.snapshot_name_format % (
            "second", helpers.SNAPSHOT_TEMPLATE_DESC
            % helpers.VM_NAMES[0])

        vms.attach_backup_disk_to_vm(helpers.VM_NAMES[0],
                                     helpers.VM_NAMES[1],
                                     cls.first_snapshot)

    @tcms(TEST_PLAN_ID, tcms_test_case)
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
        vms.stop_vms_safely([helpers.VM_NAMES[0]])
        logger.info("Succeeded to stop vm %s", helpers.VM_NAMES[0])

        logger.info("Previewing snapshot %s", self.first_snapshot)
        self.assertTrue(vms.preview_snapshot(True, helpers.VM_NAMES[0],
                                             self.first_snapshot),
                        "Failed to preview snapshot %s" % self.first_snapshot)

        logger.info("Undoing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(vms.undo_snapshot_preview(
            True, helpers.VM_NAMES[0], self.first_snapshot),
            "Failed to undo previewed snapshot %s" % self.first_snapshot)

        logger.info("Previewing snapshot %s", self.first_snapshot)
        self.assertTrue(vms.preview_snapshot(True, helpers.VM_NAMES[0],
                                             self.first_snapshot),
                        "Failed to preview snapshot %s" % self.first_snapshot)

        logger.info("Committing Previewed snapshot %s", self.first_snapshot)
        self.assertFalse(vms.commit_snapshot(
            True, helpers.VM_NAMES[0], self.first_snapshot),
            "Failed to commit previewed snapshot %s" % self.first_snapshot)

        logger.info("Deleting snapshot %s", self.first_snapshot)
        self.assertFalse(vms.removeSnapshot(
            True, helpers.VM_NAMES[0], self.first_snapshot),
            "Failed to delete snapshot %s" % self.first_snapshot)

    @classmethod
    def teardown_class(cls):
        """
        Detach backup disk
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                helpers.VM_NAMES[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())

        vms.start_vms(helpers.VM_NAMES[1], 1, wait_for_ip=False)


@attr(tier=1)
class TestCase304166(CreateTemplateFromVM):
    """
    Create a template of a backup VM
    https://tcms.engineering.redhat.com/case/304166/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304166'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_template_of_backup_vm(self):
        """
        Create a template of a backup VM after attaching snapshot disk of
        source VM to backup VM
        """
        self.vm_name_for_template = helpers.VM_NAMES[1]
        self.create_template()


@attr(tier=1)
class TestCase304167(CreateTemplateFromVM):
    """
    Create a template of a source VM
    https://tcms.engineering.redhat.com/case/304167/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304167'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_template_of_source_vm(self):
        """
        Create a template of source VM after attaching snapshot disk of
        source VM to backup VM
        """
        self.vm_name_for_template = helpers.VM_NAMES[0]
        self.create_template()


@attr(tier=2)
class TestCase304168(TestCase):
    """
    Block connection from host to storage domain 2 that contains
    snapshot of attached disk
    https://tcms.engineering.redhat.com/case/304168/?from_plan=10435

    This case is currently not part of the plan (__test__ = False) due to bug:
    https://bugzilla.redhat.com/show_bug.cgi?id=1063336 which cause
    the environment to be unusable after it runs.
    Even though that i wrote a temporary solution (see below), it doesn't
    solve the problem completely.
    """
    __test__ = False
    tcms_test_case = '304168'
    master_domain_ip = None
    blocked = False

    @classmethod
    def setup_class(cls):

        status, cls.master_domain_ip = storagedomains.getDomainAddress(
            True, config.SD_NAME_0)
        if not status:
            raise exceptions.SkipTest("Unable to get storage domain %s "
                                      "address" % config.SD_NAME_0)

        vms.stop_vms_safely([helpers.VM_NAMES[1]])
        logger.info("Succeeded to stop vm %s", helpers.VM_NAMES[1])

        if not vms.moveVm(True, helpers.VM_NAMES[1], config.SD_NAME_1):
            raise exceptions.VMException("Failed to move vm %s to storage "
                                         "domain %s"
                                         % (helpers.VM_NAMES[1],
                                            config.SD_NAME_1))

        vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_storage_failure_of_snapshot(self):
        """
        Test checks that blocking connection from host to storage domain that
        containing the snapshot of attached disk, cause the backup
        vm enter to paused status
        """

        vms.start_vms([helpers.VM_NAMES[1]], 1, wait_for_ip=False)
        vms.waitForVmsStates(True, [helpers.VM_NAMES[1]])

        logger.info("Blocking connectivity from host %s to storage domain %s",
                    config.HOSTS[0], config.SD_NAME_0)

        status = st_api.blockOutgoingConnection(
            config.HOSTS[0], 'root', config.VDS_PASSWORD[0],
            self.master_domain_ip['address'])

        if status:
            self.blocked = True

        self.assertTrue(status, "block connectivity to master domain failed")

        vms.waitForVMState(helpers.VM_NAMES[1], state=config.VM_PAUSED)

        vm_state = vms.get_vm_state(helpers.VM_NAMES[1])
        self.assertEqual(vm_state, config.VM_PAUSED,
                         "vm %s should be in state paused"
                         % helpers.VM_NAMES[1])

    def tearDown(self):
        """
        Detach backup disk
        """
        logger.info("Unblocking connectivity from host %s to storage domain "
                    "%s", config.HOSTS[0], config.SD_NAME_0)

        status = st_api.unblockOutgoingConnection(
            config.HOSTS[0], 'root', config.VDS_PASSWORD[0],
            self.master_domain_ip['address'])

        if not status:
            raise exceptions.HostException(
                "Failed to unblock connectivity from host %s to "
                "storage domain %s" % (
                    config.HOSTS[0],
                    config.SD_NAME_0
                )
            )

        # TODO: temporary solution for bug -
        # https://bugzilla.redhat.com/show_bug.cgi?id=1063336

        host_obj = vms.getVmHost(helpers.VM_NAMES[0])[1]['vmHoster']
        utils.restartVdsmd(host_obj, config.VDS_PASSWORD[0])

        hosts.waitForHostsStates(True, config.HOSTS[0])

        vms.stop_vms_safely([helpers.VM_NAMES[1]])
        logger.info("Succeeded to stop vm %s", helpers.VM_NAMES[1])

        if not vms.moveVm(True, helpers.VM_NAMES[1], config.SD_NAME_0):
            raise exceptions.VMException("Failed to move vm %s to storage "
                                         "domain %s"
                                         % (helpers.VM_NAMES[1],
                                            config.SD_NAME_0))

        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                helpers.VM_NAMES[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())

        vms.start_vms(helpers.VM_NAMES[1], 1, wait_for_ip=False)


@attr(tier=0)
class TestCase304197(TestCase):
    """
    Full flow of backup/restore API
    https://tcms.engineering.redhat.com/case/304197/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304197'

    @classmethod
    def setup_class(cls):
        vms.start_vms(helpers.VM_NAMES, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, helpers.VM_NAMES)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    @bz('1077678')
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
        logger.info("Starting to backup vm %s", helpers.VM_NAMES[0])
        status = vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        self.assertTrue(status, "Failed to attach backup snapshot disk to "
                                "backup vm")

        logger.info("Get ovf configuration file of vm %s", helpers.VM_NAMES[0])
        ovf = vms.get_vm_snapshot_ovf_obj(helpers.VM_NAMES[0],
                                          helpers.SNAPSHOT_TEMPLATE_DESC
                                          % helpers.VM_NAMES[0])

        self.assertTrue(vms.addDisk(
            True, helpers.VM_NAMES[1], 6 * config.GB, True, config.SD_NAME_0,
            interface=config.DISK_INTERFACE_VIRTIO),
            "Failed to add backup disk to backup vm %s" % helpers.VM_NAMES[1])

        for disk in vms.getVmDisks(helpers.VM_NAMES[1]):
            if not vms.check_VM_disk_state(helpers.VM_NAMES[1],
                                           disk.get_alias()):

                vms.activateVmDisk(True, helpers.VM_NAMES[1], disk.get_alias())

        vm_machine_ip = vms.get_vm_ip(helpers.VM_NAMES[1])

        linux_machine = Machine(
            host=vm_machine_ip, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW).util('linux')

        devices = linux_machine.get_storage_devices()

        logger.info("Copy disk from %s to %s", devices[1], devices[2])
        status = helpers.copy_backup_disk(vm_machine_ip, devices[1],
                                          devices[2],
                                          timeout=TASK_TIMEOUT)

        self.assertTrue(status, "Failed to copy disk")

        vms.stop_vms_safely(helpers.VM_NAMES)
        logger.info("Succeeded to stop vms %s", ', '.join(helpers.VM_NAMES))

        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        self.assertTrue(disks.detachDisk(True, disks_objs[0].get_alias(),
                                         helpers.VM_NAMES[1],
                                         "Failed to detach disk %s"
                                         % disks_objs[0].get_alias()))

        snapshot = vms.get_vm_snapshots(helpers.VM_NAMES[0])[0]
        vms.removeSnapshot(True, helpers.VM_NAMES[0],
                           snapshot.get_description())

        vms.removeVms(True, helpers.VM_NAMES[0], stop='true')

        logger.info("Restoring vm...")
        status = vms.create_vm_from_ovf(helpers.RESTORED_VM,
                                        config.CLUSTER_NAME,
                                        ovf)
        self.assertTrue(status, "Failed to create vm from ovf configuration")

        disks_objs = vms.getVmDisks(helpers.VM_NAMES[1])

        self.assertTrue(disks.detachDisk(True, disks_objs[1].get_alias(),
                                         helpers.VM_NAMES[1]),
                        "Failed to detach disk %s from backup vm"
                        % disks_objs[1].get_alias())

        self.assertTrue(disks.attachDisk(True, disks_objs[1].get_alias(),
                        helpers.RESTORED_VM),
                        "Failed to attach disk %s to restored vm"
                        % disks_objs[1].get_alias())

        new_vm_list = helpers.VM_NAMES
        new_vm_list[0] = helpers.RESTORED_VM

        vms.start_vms(helpers.VM_NAMES, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, helpers.VM_NAMES)

    @classmethod
    def teardown_class(cls):
        """
        Restoring the environment
        """
        vms_to_remove = helpers.VM_NAMES
        vms_to_remove[0] = helpers.RESTORED_VM

        vms.removeVms(True, vms_to_remove, stop='true')

        for index in range(config.VM_COUNT):
            helpers.prepare_vm(
                helpers.VM_NAMES[index],
                create_snapshot=helpers.SHOULD_CREATE_SNAPSHOT[index])


@attr(tier=1)
class TestCase322485(TestCase):
    """
    Attach more than 1 backup disks (i.e. snapshot disks) to backup vm
    https://tcms.engineering.redhat.com/case/322485/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322485'
    snapshot_template_name = "%s-snapshot"

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_hotplug_more_than_1_disk(self):
        """
         Create a snapshot to source VM and
         try to attach all source VM's snapshot disks to backup VM
        """
        vms.addDisk(True, helpers.VM_NAMES[0], 6 * config.GB, True,
                    config.SD_NAME_0,
                    interface=config.DISK_INTERFACE_VIRTIO)
        vms.addSnapshot(
            True, vm=helpers.VM_NAMES[0],
            description=self.snapshot_template_name % helpers.VM_NAMES[0])

        self.assertTrue(vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            self.snapshot_template_name % helpers.VM_NAMES[0]),
            "Failed to attach all snapshot disks to backup vm")

    @classmethod
    def teardown_class(cls):
        """
        Restoring the environment
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            cls.snapshot_template_name % helpers.VM_NAMES[0])

        for disk_obj in disks_objs:
            if not disks.detachDisk(True, disk_obj.get_alias(),
                                    helpers.VM_NAMES[1]):
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk_obj.get_alias())
        vms.stop_vms_safely([helpers.VM_NAMES[0]])
        logger.info("Succeeded to stop vm %s", helpers.VM_NAMES[0])

        if not vms.removeSnapshot(
                True, helpers.VM_NAMES[0],
                cls.snapshot_template_name % helpers.VM_NAMES[0]):
            snapshot_name = cls.snapshot_template_name % helpers.VM_NAMES[0]
            raise exceptions.VMException("Failed to remove snapshot %s"
                                         % snapshot_name)

        disks_to_remove = vms.getVmDisks(helpers.VM_NAMES[0])
        for disk in disks_to_remove:
            if not disk.get_bootable():
                vms.removeDisk(True, helpers.VM_NAMES[0], disk.get_alias())
                logger.info("Disk %s - removed", disk.get_alias())


@attr(tier=2)
class TestCase322486(TestCase):
    """
    During a vm disk migration, try to attach the snapshot disk to backup vm
    https://tcms.engineering.redhat.com/case/322486/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322486'

    @classmethod
    def setup_class(cls):
        vms.stop_vms_safely(helpers.VM_NAMES)
        logger.info("Succeeded to stop vms %s", ', '.join(helpers.VM_NAMES))

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_snapshot_disk_while_the_disk_is_locked(self):
        """
        - Move source vm disk to the second storage domain
        - During the disk movement, try to attach the snapshot disk to the
          backup VM (while the disk is locked)
        """
        vm_disks = vms.getVmDisks(helpers.VM_NAMES[0])

        vms.move_vm_disk(helpers.VM_NAMES[0], vm_disks[0].get_alias(),
                         config.SD_NAME_1, wait=False)

        disks.waitForDisksState(vm_disks[0].get_alias(),
                                config.ENUMS['disk_state_locked'])

        status = vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        self.assertFalse(status, "Succeeded to attach backup snapshot disk "
                                 "to backup vm")

    @classmethod
    def teardown_class(cls):
        """
        Restoring environment
        """
        vm_disks = vms.getVmDisks(helpers.VM_NAMES[0])
        logger.info("Moving disk %s to SD %s", vm_disks[0].get_alias(),
                    config.SD_NAME_0)
        disks.waitForDisksState(vm_disks[0].get_alias())
        vms.move_vm_disk(helpers.VM_NAMES[0], vm_disks[0].get_alias(),
                         config.SD_NAME_0, wait=True)
        disks.waitForDisksState(vm_disks[0].get_alias())


@attr(tier=2)
class TestCase322487(BaseTestCase):
    """
    Attach snapshot disk to backup vm more than once
    https://tcms.engineering.redhat.com/case/322487/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322487'

    @classmethod
    def setup_class(cls):
        pass

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_the_same_disk_twice_to_a_VM(self):
        """
        Attach the snapshot disk of source VM to backup VM and
        do it again
        """
        vms.waitForDisksStat(helpers.VM_NAMES[0])
        status = vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        self.assertTrue(status, "Failed to attach backup snapshot disk to "
                                "backup vm")

        status = vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        self.assertFalse(status, "Succeeded to attach backup snapshot disk "
                                 "to backup vm")


@attr(tier=1)
class TestCase322886(TestCase):
    """
    During a vm disk live migration,
    try to attach the snapshot disk to backup vm
    https://tcms.engineering.redhat.com/case/322886/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322886'

    @classmethod
    def setup_class(cls):
        vms.waitForDisksStat(helpers.VM_NAMES[0])
        vms.waitForDisksStat(helpers.VM_NAMES[1])
        vms.start_vms(helpers.VM_NAMES, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, helpers.VM_NAMES)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_Attach_disk_while_performing_LSM(self):
        """
        Live migrate a disk from the source VM.
        Attach the migrated snapshot disk to a backup VM while
        the migration is taking place
        """
        disks = vms.getVmDisks(helpers.VM_NAMES[0])
        vms.move_vm_disk(helpers.VM_NAMES[0], disks[0].get_alias(),
                         config.SD_NAME_1, wait=False)

        status = vms.attach_backup_disk_to_vm(
            helpers.VM_NAMES[0], helpers.VM_NAMES[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        self.assertFalse(status, "Succeeded to attach backup snapshot disk "
                                 "to backup vm")

    @classmethod
    def teardown_class(cls):
        """
        Restoring environment
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            helpers.VM_NAMES[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % helpers.VM_NAMES[0])

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                helpers.VM_NAMES[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())
