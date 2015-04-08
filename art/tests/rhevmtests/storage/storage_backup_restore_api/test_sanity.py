"""
Storage backup restore API - 10435
https://tcms.engineering.redhat.com/plan/10435
"""

import config
import helpers
import logging
from concurrent.futures import ThreadPoolExecutor
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import templates, hosts
from art.rhevm_api.tests_lib.low_level.datacenters import get_data_center
from art.unittest_lib import attr
from rhevmtests.storage.helpers import get_vm_ip
import art.rhevm_api.utils.storage_api as st_api
from art.rhevm_api.utils import test_utils as utils
from utilities.machine import Machine
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler import exceptions

logger = logging.getLogger(__name__)

TASK_TIMEOUT = 1500

TEST_PLAN_ID = '10435'

VM_NAMES = {}


def setup_module():
    """
    Prepares environment
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)

    exs = []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for storage_type in config.STORAGE_SELECTOR:
            storage_domain = storagedomains.getStorageDomainNamesForType(
                config.DATA_CENTER_NAME, storage_type)[0]
            VM_NAMES[storage_type] = []
            for idx in range(config.VM_COUNT):
                vm_name = "backup_api_vm_%d_%s" % (idx, storage_type)
                VM_NAMES[storage_type].append(vm_name)

                logger.info("Creating vm %s on storage domain %s",
                            vm_name, storage_domain)
                exs.append((
                    vm_name,
                    executor.submit(
                        helpers.prepare_vm, vm_name,
                        helpers.SHOULD_CREATE_SNAPSHOT[idx], storage_domain,
                    )
                ))

    # helpers.prepare_vm will raise a exception in case anything goes wrong
    [ex[1].exception() for ex in exs]


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )

    else:
        for storage_type, vm_names in VM_NAMES.iteritems():
            vm_names = filter(vms.does_vm_exist, vm_names)
            vms.stop_vms_safely(vm_names)
            vms.removeVms(True, vm_names)


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_test_case = None

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, self.vm_names)
        if not vms.attach_backup_disk_to_vm(self.vm_names[0],
                                            self.vm_names[1],
                                            helpers.SNAPSHOT_TEMPLATE_DESC
                                            % self.vm_names[0]):
            raise exceptions.DiskException("Failed to attach backup disk "
                                           "to backup vm %s"
                                           % self.vm_names[1])

    def tearDown(self):
        """
        Start vm and detach backup disk and start vms
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                self.vm_names[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())


class CreateTemplateFromVM(BaseTestCase):
    """
    Create a template of a backup VM
    https://tcms.engineering.redhat.com/case/304166/?from_plan=10435
    """
    __test__ = False
    template_name = "%s-template"

    def _create_template(self):
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

        super(CreateTemplateFromVM, self).tearDown()


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
        self.host = vms.getVmHost(self.vm_names[1])[1]['vmHoster']
        self.host_ip = hosts.getHostIP(self.host)
        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory is empty")
        vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        self.assertTrue(helpers.is_transient_directory_empty(self.host_ip),
                        "Transient directory still "
                        "contains backup disk volumes")

        source_vm_disks = vms.getVmDisks(self.vm_names[0])
        backup_vm_disks = vms.getVmDisks(self.vm_names[1])
        disk_id = source_vm_disks[0].get_id()
        is_disk_attached = disk_id in [disk.get_id() for disk in
                                       backup_vm_disks]

        self.assertTrue(is_disk_attached, "Backup disk is not attached")


@attr(tier=3)
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
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        snapshot_disk = disks_objs[0]

        datacenter_obj = get_data_center(config.DATA_CENTER_NAME)
        self.host = vms.getVmHost(self.vm_names[1])[1]['vmHoster']
        self.host_ip = hosts.getHostIP(self.host)
        checksum_before = disks.checksum_disk(self.host_ip,
                                              config.HOSTS_USER,
                                              config.HOSTS_PW,
                                              snapshot_disk,
                                              datacenter_obj)

        logger.info("Restarting VDSM...")
        self.assertTrue(utils.restartVdsmd(self.host_ip, config.HOSTS_PW),
                        "Failed restarting VDSM service")
        hosts.waitForHostsStates(True, self.host)
        logger.info("Successfully restarted VDSM service")

        vm_disks = vms.getVmDisks(self.vm_names[1])
        status = disks_objs[0].get_alias() in \
            [disk.get_alias() for disk in vm_disks]
        self.assertTrue(status, "Backup disk is not attached after "
                                "restarting VDSM")

        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory is empty")

        engine = config.VDC
        engine_object = Machine(
            host=engine,
            user=config.HOSTS_USER,
            password=config.HOSTS_PW).util('linux')

        logger.info("Restarting ovirt-engine...")
        self.assertTrue(utils.restartOvirtEngine(engine_object, 5, 30, 30),
                        "Failed restarting ovirt-engine")
        logger.info("Successfully restarted ovirt-engine")

        vm_disks = vms.getVmDisks(self.vm_names[1])
        status = disks_objs[0].get_alias() in [disk.get_alias() for
                                               disk in vm_disks]
        self.assertTrue(status, "Backup disk is not attached after "
                                "restarting ovirt-engine")
        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory is empty")
        logger.info("transient directory contains backup disk")

        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        snapshot_disk = disks_objs[0]

        logger.info("Verifying disk is not corrupted")
        datacenter_obj = get_data_center(config.DATA_CENTER_NAME)
        checksum_after = disks.checksum_disk(self.host_ip,
                                             config.HOSTS_USER,
                                             config.HOSTS_PW,
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

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        self.host = hosts.get_cluster_hosts(config.CLUSTER_NAME)[0]
        self.host_ip = hosts.getHostIP(self.host)
        logger.info("Updating vm %s to placement host %s",
                    self.vm_names[1], self.host)
        assert vms.updateVm(True, self.vm_names[1], placement_host=self.host)
        vms.attach_backup_disk_to_vm(self.vm_names[0],
                                     self.vm_names[1],
                                     helpers.SNAPSHOT_TEMPLATE_DESC
                                     % self.vm_names[0])

    @tcms(TEST_PLAN_ID, tcms_test_case)
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
        self.assertTrue(vms.startVm(
            True, self.vm_names[1],
            wait_for_status=config.VM_UP),
            "Failed to start vm %s" % (self.vm_names[1]))
        self.host_ip = hosts.getHostIP(self.host)
        logger.info("vm %s started successfully", self.vm_names[1])

        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
                         "Transient directory should contain "
                         "backup disk volumes")
        logger.info("%s contain backup volume", helpers.TRANSIENT_DIR_PATH)


@attr(tier=1)
class TestCase304156(BaseTestCase):
    """
    Attach snapshot disk of source VM to running backup VM
    and Hotplug the snapshot disk
    https://tcms.engineering.redhat.com/case/304156/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304156'

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, self.vm_names)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_and_hotplug_snapshot_disk_of_source_vm_to_backup_vm(self):
        """
        Make sure that before hotplugging the backup disk,
        /var/lib/vdsm/transient/
        will not contain any backup volumes and after hotplug, the
        backup volumes will be created
        """
        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        vms.attach_backup_disk_to_vm(self.vm_names[0],
                                     self.vm_names[1],
                                     helpers.SNAPSHOT_TEMPLATE_DESC
                                     % self.vm_names[0],
                                     activate=False)

        self.host = vms.getVmHost(self.vm_names[1])[1]['vmHoster']
        self.host_ip = hosts.getHostIP(self.host)
        self.assertTrue(helpers.is_transient_directory_empty(self.host_ip),
                        "Transient directory should be empty")
        logger.info("%s is empty", helpers.TRANSIENT_DIR_PATH)

        self.assertTrue(vms.activateVmDisk(True, self.vm_names[1],
                                           disks_objs[0].get_alias()),
                        "Failed to activate disk %s of vm %s"
                        % (disks_objs[0].get_alias(), self.vm_names[1]))

        self.assertFalse(helpers.is_transient_directory_empty(self.host_ip),
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

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        self.snap_desc = helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        super(TestCase304159, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_delete_original_snapshot_while_attached_to_another_vm(self):
        """
        Try to delete original snapshot of source VM that is attached to
        backup VM
        """
        logger.info("Removing snapshot %s of vm %s",
                    helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0],
                    self.vm_names[0])

        self.assertTrue(vms.stopVm(True, self.vm_names[0],
                                   async='true'),
                        "Failed to shutdown vm %s" % self.vm_names[0])

        status = vms.removeSnapshot(True, self.vm_names[0],
                                    helpers.SNAPSHOT_TEMPLATE_DESC
                                    % self.vm_names[0])

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
    """
    __test__ = True
    tcms_test_case = '304161'
    snapshot_name_format = "%s-%s"

    first_snapshot = ""
    second_snapshot = ""

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        self.first_snapshot = helpers.SNAPSHOT_TEMPLATE_DESC \
            % self.vm_names[0]

        self.second_snapshot = self.snapshot_name_format % (
            "second", helpers.SNAPSHOT_TEMPLATE_DESC
            % self.vm_names[0])

        vms.attach_backup_disk_to_vm(self.vm_names[0],
                                     self.vm_names[1],
                                     self.first_snapshot)

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
        vms.stop_vms_safely([self.vm_names[0]])
        logger.info("Succeeded to stop vm %s", self.vm_names[0])

        logger.info("Previewing snapshot %s", self.first_snapshot)
        self.assertTrue(vms.preview_snapshot(True, self.vm_names[0],
                                             self.first_snapshot),
                        "Failed to preview snapshot %s" % self.first_snapshot)
        vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_IN_PREVIEW,  self.first_snapshot
        )

        logger.info("Undoing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(vms.undo_snapshot_preview(
            True, self.vm_names[0], self.first_snapshot
        ),
            "Failed to undo previewed snapshot %s" % self.first_snapshot)
        vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_OK,  self.first_snapshot
        )

        logger.info("Previewing snapshot %s", self.first_snapshot)
        self.assertTrue(vms.preview_snapshot(True, self.vm_names[0],
                                             self.first_snapshot),
                        "Failed to preview snapshot %s" % self.first_snapshot)
        vms.wait_for_vm_snapshots(
            self.vm_names[0], config.SNAPSHOT_IN_PREVIEW,  self.first_snapshot
        )

        logger.info("Committing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(vms.commit_snapshot(
            False, self.vm_names[0], self.first_snapshot
        ),
            "Succeeded to commit previewed snapshot %s" % self.first_snapshot)

        logger.info("Undoing Previewed snapshot %s", self.first_snapshot)
        self.assertTrue(vms.undo_snapshot_preview(
            True, self.vm_names[0], self.first_snapshot
        ),
            "Failed to undo previewed snapshot %s" % self.first_snapshot)

    def tearDown(self):
        """
        Detach backup disk
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0]
        )

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                self.vm_names[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())
        vms.start_vms(
            [self.vm_names[0]], 1, wait_for_status=config.VM_UP,
            wait_for_ip=False
        )


@attr(tier=1)
class TestCase304166(CreateTemplateFromVM):
    """
    Create a template of a backup VM
    https://tcms.engineering.redhat.com/case/304166/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304166'

    def setUp(self):
        super(CreateTemplateFromVM, self).setUp()
        self.vm_name_for_template = self.vm_names[1]

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_template_of_backup_vm(self):
        """
        Create a template of a backup VM after attaching snapshot disk of
        source VM to backup VM
        """
        self._create_template()


@attr(tier=1)
class TestCase304167(CreateTemplateFromVM):
    """
    Create a template of a source VM
    https://tcms.engineering.redhat.com/case/304167/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '304167'

    def setUp(self):
        super(TestCase304167, self).setUp()
        self.vm_name_for_template = self.vm_names[0]

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_template_of_source_vm(self):
        """
        Create a template of source VM after attaching snapshot disk of
        source VM to backup VM
        """
        self._create_template()


@attr(tier=3)
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
    storage_domain_ip = None
    blocked = False

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]

        self.storage_domains = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)

        self.host = hosts.getSPMHost(config.HOSTS)
        self.host_ip = hosts.getHostIP(self.host)

        status, self.storage_domain_ip = storagedomains.getDomainAddress(
            True, self.storage_domains[0])
        if not status:
            raise exceptions.SkipTest("Unable to get storage domain %s "
                                      "address" % self.storage_domains[0])

        vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        if not vms.moveVm(True, self.vm_names[1], self.storage_domains[1]):
            raise exceptions.VMException("Failed to move vm %s to storage "
                                         "domain %s"
                                         % (self.vm_names[1],
                                            self.storage_domains[1]))

        vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_storage_failure_of_snapshot(self):
        """
        Test checks that blocking connection from host to storage domain that
        containing the snapshot of attached disk, cause the backup
        vm enter to paused status
        """

        vms.start_vms([self.vm_names[1]], 1, wait_for_ip=False)
        vms.waitForVmsStates(True, [self.vm_names[1]])

        logger.info("Blocking connectivity from host %s to storage domain %s",
                    self.host, self.storage_domains[0])

        status = st_api.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip['address'])

        if status:
            self.blocked = True

        self.assertTrue(status, "block connectivity to master domain failed")

        vms.waitForVMState(self.vm_names[1], state=config.VM_PAUSED)

        vm_state = vms.get_vm_state(self.vm_names[1])
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

        # TODO: temporary solution for bug -
        # https://bugzilla.redhat.com/show_bug.cgi?id=1063336

        host_name = vms.getVmHost(self.vm_names[0])[1]['vmHoster']
        host_ip = hosts.getHostIP(host_name)
        utils.restartVdsmd(host_ip, config.HOSTS_PW)

        hosts.waitForHostsStates(True, host_name)

        vms.stop_vms_safely([self.vm_names[1]])
        logger.info("Succeeded to stop vm %s", self.vm_names[1])

        if not vms.moveVm(True, self.vm_names[1], self.storage_domains[0]):
            raise exceptions.VMException("Failed to move vm %s to storage "
                                         "domain %s"
                                         % (self.vm_names[1],
                                            self.storage_domains[0]))

        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        if not disks.detachDisk(True, disks_objs[0].get_alias(),
                                self.vm_names[1]):
            raise exceptions.DiskException("Failed to remove disk %s"
                                           % disks_objs[0].get_alias())

        vms.start_vms(self.vm_names[1], 1, wait_for_ip=False)


@attr(tier=0)
class TestCase304197(TestCase):
    """
    Full flow of backup/restore API
    https://tcms.engineering.redhat.com/case/304197/?from_plan=10435
    """
    __test__ = True
    # The ticket for sdk support:
    # https://projects.engineering.redhat.com/browse/RHEVM-1901
    apis = TestCase.apis - set(['sdk'])
    tcms_test_case = '304197'

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, self.vm_names)
        self.vm_machine_ip = get_vm_ip(self.vm_names[1])
        self.storage_domains = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)

    @tcms(TEST_PLAN_ID, tcms_test_case)
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
        logger.info("Starting to backup vm %s", self.vm_names[0])
        status = vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        self.assertTrue(status, "Failed to attach backup snapshot disk to "
                                "backup vm")

        logger.info("Get ovf configuration file of vm %s", self.vm_names[0])
        ovf = vms.get_vm_snapshot_ovf_obj(self.vm_names[0],
                                          helpers.SNAPSHOT_TEMPLATE_DESC
                                          % self.vm_names[0])
        status = ovf is None
        self.assertFalse(status, "OVF object wasn't found")

        self.assertTrue(vms.addDisk(
            True, self.vm_names[1], 6 * config.GB, True,
            self.storage_domains[0], interface=config.DISK_INTERFACE_VIRTIO),
            "Failed to add backup disk to backup vm %s" % self.vm_names[1])

        for disk in vms.getVmDisks(self.vm_names[1]):
            if not vms.check_VM_disk_state(self.vm_names[1],
                                           disk.get_alias()):

                vms.activateVmDisk(True, self.vm_names[1], disk.get_alias())

        linux_machine = Machine(
            host=self.vm_machine_ip, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW).util('linux')

        devices = linux_machine.get_storage_devices()

        logger.info("Copy disk from %s to %s", devices[1], devices[2])
        status = helpers.copy_backup_disk(self.vm_machine_ip, devices[1],
                                          devices[2],
                                          timeout=TASK_TIMEOUT)

        self.assertTrue(status, "Failed to copy disk")

        vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))

        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        self.assertTrue(
            disks.detachDisk(
                True, disks_objs[0].get_alias(), self.vm_names[1]),
            "Failed to detach disk %s" % disks_objs[0].get_alias())

        snapshots = vms.get_vm_snapshots(self.vm_names[0])
        snaps_to_remove = [s.get_description() for s in snapshots if
                           (s.get_description() ==
                            helpers.SNAPSHOT_TEMPLATE_DESC)]
        for snap in snaps_to_remove:
            vms.removeSnapshot(True, self.vm_names[0],
                               snap)

        vms.stop_vms_safely([self.vm_names[0]])
        vms.removeVms(True, self.vm_names[0])

        logger.info("Restoring vm...")
        status = vms.create_vm_from_ovf(helpers.RESTORED_VM,
                                        config.CLUSTER_NAME,
                                        ovf)
        self.assertTrue(status, "Failed to create vm from ovf configuration")

        disks_objs = vms.getVmDisks(self.vm_names[1])

        self.assertTrue(disks.detachDisk(True, disks_objs[1].get_alias(),
                                         self.vm_names[1]),
                        "Failed to detach disk %s from backup vm"
                        % disks_objs[1].get_alias())

        self.assertTrue(disks.attachDisk(True, disks_objs[1].get_alias(),
                        helpers.RESTORED_VM),
                        "Failed to attach disk %s to restored vm"
                        % disks_objs[1].get_alias())

        new_vm_list = self.vm_names[:]
        new_vm_list[0] = helpers.RESTORED_VM

        vms.start_vms(new_vm_list, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, new_vm_list)

    def tearDown(self):
        """
        Restoring the environment
        """
        vms_to_remove = self.vm_names[:]
        # If the first vm still exists, remove it
        vms_to_remove.append(helpers.RESTORED_VM)

        vms_to_remove = filter(vms.does_vm_exist, vms_to_remove)
        vms.stop_vms_safely(vms_to_remove)
        vms.removeVms(True, vms_to_remove)

        for index in range(config.VM_COUNT):
            helpers.prepare_vm(
                self.vm_names[index],
                create_snapshot=helpers.SHOULD_CREATE_SNAPSHOT[index],
                storage_domain=self.storage_domains[0])


@attr(tier=1)
class TestCase322485(TestCase):
    """
    Attach more than 1 backup disks (i.e. snapshot disks) to backup vm
    https://tcms.engineering.redhat.com/case/322485/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322485'
    snapshot_template_name = "%s-snapshot"

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_multiple_disks(self):
        """
         Create a snapshot to source VM and
         try to attach all source VM's snapshot disks to backup VM
        """
        storage_domain = vms.get_vms_disks_storage_domain_name(
            self.vm_names[0])
        if not vms.addDisk(
                True, self.vm_names[0], 6 * config.GB, True, storage_domain,
                interface=config.DISK_INTERFACE_VIRTIO
        ):
            raise exceptions.DiskException(
                "Failed to add disk to vm %s" % self.vm_names[0]
            )
        vms.addSnapshot(
            True, vm=self.vm_names[0],
            description=self.snapshot_template_name % self.vm_names[0])

        self.assertTrue(vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            self.snapshot_template_name % self.vm_names[0]),
            "Failed to attach all snapshot disks to backup vm")

    def tearDown(self):
        """
        Restoring the environment
        """
        logger.info('Detaching backup disk')
        disks_objs = vms.get_snapshot_disks(
            self.vm_names[0],
            self.snapshot_template_name % self.vm_names[0])

        for disk_obj in disks_objs:
            if not disks.detachDisk(True, disk_obj.get_alias(),
                                    self.vm_names[1]):
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk_obj.get_alias())
        vms.stop_vms_safely([self.vm_names[0]])
        logger.info("Succeeded to stop vm %s", self.vm_names[0])

        if not vms.removeSnapshot(
                True, self.vm_names[0],
                self.snapshot_template_name % self.vm_names[0]):
            snapshot_name = self.snapshot_template_name % self.vm_names[0]
            raise exceptions.VMException("Failed to remove snapshot %s"
                                         % snapshot_name)

        disks_to_remove = vms.getVmDisks(self.vm_names[0])
        for disk in disks_to_remove:
            if not disk.get_bootable():
                vms.removeDisk(True, self.vm_names[0], disk.get_alias())
                logger.info("Disk %s - removed", disk.get_alias())


@attr(tier=1)
class TestCase322486(TestCase):
    """
    During a vm disk migration, try to attach the snapshot disk to backup vm
    https://tcms.engineering.redhat.com/case/322486/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322486'
    bz = {
        '1196049': {'engine': None, 'version': ['3.5.1']},
        '1176673': {'engine': None, 'version': ['3.6']},
    } if TestCase.storage == config.STORAGE_TYPE_ISCSI else None

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        vms.stop_vms_safely(self.vm_names)
        logger.info("Succeeded to stop vms %s", ', '.join(self.vm_names))
        self.vm_disks = vms.getVmDisks(self.vm_names[0])
        self.original_sd = vms.get_vms_disks_storage_domain_name(
            self.vm_names[0], self.vm_disks[0].get_alias())
        storage_domains = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)
        self.destination_sd = [
            sd for sd in storage_domains if sd != self.original_sd][0]

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_snapshot_disk_while_the_disk_is_locked(self):
        """
        - Move source vm disk to the second storage domain
        - During the disk movement, try to attach the snapshot disk to the
          backup VM (while the disk is locked)
        """
        vms.move_vm_disk(self.vm_names[0], self.vm_disks[0].get_alias(),
                         self.destination_sd, wait=False)

        disks.wait_for_disks_status(
            disks=self.vm_disks[0].get_alias(),
            status=config.ENUMS['disk_state_locked']
        )

        status = vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        self.assertFalse(status, "Succeeded to attach backup snapshot disk "
                                 "to backup vm")

    def tearDown(self):
        """
        Restoring environment
        """
        vm_disks = vms.getVmDisks(self.vm_names[0])
        logger.info("Moving disk %s to SD %s", vm_disks[0].get_alias(),
                    self.original_sd)
        disks.wait_for_disks_status(vm_disks[0].get_alias())
        vms.move_vm_disk(self.vm_names[0], vm_disks[0].get_alias(),
                         self.original_sd, wait=True)
        disks.wait_for_disks_status(vm_disks[0].get_alias())


@attr(tier=1)
class TestCase322487(BaseTestCase):
    """
    Attach snapshot disk to backup vm more than once
    https://tcms.engineering.redhat.com/case/322487/?from_plan=10435
    """
    __test__ = True
    tcms_test_case = '322487'

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_the_same_disk_twice_to_a_VM(self):
        """
        Attach the snapshot disk of source VM to backup VM and
        do it again
        """
        vms.waitForDisksStat(self.vm_names[0])
        status = vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        self.assertTrue(status, "Failed to attach backup snapshot disk to "
                                "backup vm")

        status = vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

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
    bz = {
        '1196049': {'engine': None, 'version': ['3.5.1']},
        '1176673': {'engine': None, 'version': ['3.6']},
    } if TestCase.storage == config.STORAGE_TYPE_ISCSI else None

    def setUp(self):
        self.vm_names = VM_NAMES[TestCase.storage]
        vms.waitForDisksStat(self.vm_names[0])
        vms.waitForDisksStat(self.vm_names[1])
        vms.start_vms(self.vm_names, 2, wait_for_ip=False)
        vms.waitForVmsStates(True, self.vm_names)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_Attach_disk_while_performing_LSM(self):
        """
        Live migrate a disk from the source VM.
        Attach the migrated snapshot disk to a backup VM while
        the migration is taking place
        """
        disks = vms.getVmDisks(self.vm_names[0])
        self.original_sd = vms.get_vms_disks_storage_domain_name(
            self.vm_names[0], disks[0].get_alias())
        storage_domains = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)
        self.destination_sd = [
            sd for sd in storage_domains if sd != self.original_sd][0]

        vms.move_vm_disk(self.vm_names[0], disks[0].get_alias(),
                         self.destination_sd, wait=False)

        status = vms.attach_backup_disk_to_vm(
            self.vm_names[0], self.vm_names[1],
            helpers.SNAPSHOT_TEMPLATE_DESC % self.vm_names[0])

        self.assertFalse(status, "Succeeded to attach backup snapshot disk "
                                 "to backup vm")
        logger.info("Waiting for all jobs to finish")
        wait_for_jobs()
