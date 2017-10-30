"""
Storage VM sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage/3_1_Virtual_Machines_Sanity
"""
import logging
from threading import Thread
import time
import pytest
import config
from art.unittest_lib import (
    StorageTest as TestCase,
    testflow,
    tier2,
    tier3,
    tier4,
)
from art.rhevm_api.utils import test_utils, resource_utils, log_listener
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    templates as ll_templates,
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from art.test_handler.tools import polarion, bz
from art.core_api.apis_exceptions import EntityNotFound
import rhevmtests.helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers
from fixtures import (
    deactivate_hsms, initialize_object_names, wait_for_hosts_to_be_up
)
from rhevmtests.storage.fixtures import (
    create_vm, remove_vms,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

logger = logging.getLogger(__name__)
GB = config.GB


@pytest.fixture(scope='class')
def prepare_data(request, storage):
    """
    Prepare data
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing templates %s" % self.template_names)
        for _, template_name in self.template_names.iteritems():
            ll_templates.remove_template(True, template=template_name)

    request.addfinalizer(finalizer)
    testflow.setup(
        "Creating templates for permutation of sparse and disk format"
    )
    for sparse in (True, False):
        for vol_format in (config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW):
            if not sparse and vol_format == config.DISK_FORMAT_COW:
                continue
            if (self.storage != config.STORAGE_TYPE_NFS
                    and sparse and vol_format == config.DISK_FORMAT_RAW):
                continue
            _prepare_data(
                sparse, vol_format, self.template_names, self.storage
            )


@pytest.fixture()
def clean_leftover_data(request, storage):
    """
    Clean leftover data in the slave
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Cleaning leftover data in the slave")
        for data_path in self.data_for_vm:
            # we don't need try-except, as cleanupData uses
            # rmtree(path, ignore_errors=True)
            test_utils.cleanupData(data_path)

    request.addfinalizer(finalizer)


def _prepare_data(sparse, vol_format, template_names, storage_type):
    """
    prepares data for vm
    """
    template_name = "%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.VM_BASE_NAME, storage_type, sparse, vol_format)
    vm_description = '%s_%s_prep' % (
        config.VM_BASE_NAME, storage_type)
    logger.info("Creating vm %s %s ...", sparse, vol_format)
    storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage_type)[0]
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_description
    vm_args['volumeType'] = sparse
    vm_args['volumeFormat'] = vol_format
    vm_args['storageDomainName'] = storage_domain
    vm_args['start'] = 'true'
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Creation of vm %s failed!" % vm_name
    )
    logger.info("Waiting for ip of %s", vm_name)
    vm_ip = ll_vms.wait_for_vm_ip(vm_name)[1]['ip']
    vm_executor = storage_helpers.get_vm_executor(vm_name)
    logger.info("Setting persistent network")
    test_utils.setPersistentNetwork(vm_ip, config.VM_LINUX_PASSWORD)
    logger.info("Stopping VM %s", vm_name)
    assert storage_helpers._run_cmd_on_remote_machine(
        vm_name, config.SYNC_CMD, vm_executor
    )
    assert ll_vms.stop_vms_safely([vm_name]), (
        "Failed to power off vm %s" % vm_name
    )
    ll_vms.waitForVMState(vm_name, state=config.VM_DOWN)
    logger.info(
        "Creating template %s from vm %s", template_name, vm_name)
    assert ll_templates.createTemplate(
        True, vm=vm_name, name=template_name, cluster=config.CLUSTER_NAME
    ), "Creation of template %s from vm %s failed" % (template_name, vm_name)
    logger.info("Removing vm %s", vm_name)
    assert ll_vms.removeVm(True, vm=vm_name), (
        "Removal of vm %s failed" % vm_name
    )
    logger.info(
        "Template for sparse=%s and volume format '%s' prepared",
        sparse, vol_format
    )
    template_names[(sparse, vol_format)] = template_name


@pytest.mark.usefixtures(
    create_vm.__name__,
    clean_leftover_data.__name__,
)
class TestCase11834(TestCase):
    """
    storage vm sanity test, creates and removes snapshots
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Virtual_Machines_Sanity
    """
    __test__ = True
    polarion_test_case = '11834'
    data_for_vm = []

    def _prepare_data(self):
        """ don't move it to setUp! if setUp fails, tearDown WON'T be called
        and we do want to remove all prepared data (no need to care for the
        VMs as they will be eventually removed by module-level tearDown)
        """
        self.data_for_vm = []
        testflow.step("Preparing data for copying to VM")
        for i in range(6):
            success, result = test_utils.prepareDataForVm(
                root_dir=config.DATA_ROOT_DIR,
                root_name_prefix='snap',
                dir_cnt=config.DATA_DIR_CNT,
                file_cnt=config.DATA_FILE_CNT)
            assert success, "Preparing data %d failed!" % i
            self.data_for_vm.append(result['data_path'])

    def _copy_data_to_vm_and_make_snapshot(self, source_path, snapshot_name):
        logger.info("Copying data from %s to %s", source_path, self.vm_name)
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        vm_executor = storage_helpers.get_vm_executor(self.vm_name)
        assert resource_utils.copyDataToVm(
            ip=vm_ip, user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD, osType='linux',
            src=source_path, dest=config.DEST_DIR
        ), "Copying data to vm %s failed" % self.vm_ip
        logger.info("Verify that all data were really copied")
        self._verify_data_on_vm([source_path])
        logger.info("Stopping VM %s", self.vm_name)
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, config.SYNC_CMD, vm_executor
        )
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off vm %s" % self.vm_name
        )
        ll_vms.waitForVMState(self.vm_name, state=config.VM_DOWN)
        logger.info("Creating snapshot %s", snapshot_name)
        assert ll_vms.addSnapshot(
            True, self.vm_name, snapshot_name
        ), "Creating snapshot of vm %s failed!" % self.vm_name
        logger.info("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        ), "Starting vm %s failed!" % self.vm_name

    def _verify_data_on_vm(self, paths):
        for path in paths:
            logger.info("Verify data from %s in VM %s", path, self.vm_name)
            vm_ip = storage_helpers.get_vm_ip(self.vm_name)
            assert resource_utils.verifyDataOnVm(
                positive=True, ip=vm_ip,
                user=config.VM_LINUX_USER,
                password=config.VM_LINUX_PASSWORD, osType='linux',
                dest=config.DEST_DIR, destToCompare=path
            ), "Data verification of %s on %s failed!" % (path, self.vm_name)

    def _remove_snapshot_verify_data(self, snapshot_name, expected_data):
        vm_executor = storage_helpers.get_vm_executor(self.vm_name)
        logger.info("Stopping VM %s", self.vm_name)
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, config.SYNC_CMD, vm_executor
        )
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off vm %s" % self.vm_name
        )
        ll_vms.waitForVMState(self.vm_name, state=config.VM_DOWN)
        logger.info("Removing snapshot %s", snapshot_name)
        assert ll_vms.removeSnapshot(
            True, vm=self.vm_name, description=snapshot_name,
            timeout=2100
        ), "Removing snapshot %s failed!" % snapshot_name
        logger.info(
            "Starting VM %s and waiting for status 'up'", self.vm_name)
        assert ll_vms.startVm(
            True, vm=self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        ), "Starting vm %s failed!" % self.vm_name
        logger.info("Verifying data on VM %s", self.vm_name)
        self._verify_data_on_vm(expected_data)

    @polarion("RHEVM3-11834")
    @tier2
    def test_delete_snapshots_advanced(self):
        """
        Deleting snapshots
        """
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        )
        self._prepare_data()
        logger.info("Data prepared")
        first_snap_name, second_snap_name = 'first_snapshot', 'second_snapshot'
        testflow.step("Loading data and creating first snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[0], first_snap_name)
        testflow.step("Verify that all data were really copied")
        self._verify_data_on_vm(self.data_for_vm[:1])
        testflow.step("Loading data and creating second snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[1], second_snap_name)

        testflow.step("Verify that all data were really copied")
        self._verify_data_on_vm(self.data_for_vm[:2])

        testflow.step("Removing first snapshot and verifying data")
        self._remove_snapshot_verify_data(
            first_snap_name, self.data_for_vm[:2])

        testflow.step("Removing second snapshot and verifying data")
        self._remove_snapshot_verify_data(
            second_snap_name, self.data_for_vm[:2])

        third_snap_name = 'third_snapshot'
        testflow.step("Loading data and creating third snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[2], third_snap_name)
        testflow.step("Loading data and creating fourth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[3], 'fourth_snapshot')
        testflow.step("Loading data and creating fifth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[4], 'fifth_snapshot')

        testflow.step("Removing third snapshot and verifying data")
        self._remove_snapshot_verify_data(
            third_snap_name, self.data_for_vm[:5])

        testflow.step("Loading data and creating sixth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[5], 'sixth_snapshot')
        testflow.step("Verifying data")
        self._verify_data_on_vm(self.data_for_vm)


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase11586(TestCase):
    """
    storage vm sanity test, creates 2 snapshots and removes them.
    Check that actual disk size became the same it was
    before snapshots were made.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11586'
    data_for_vm = []
    snapShot1_name = "%s_snapshot1" % config.VM_BASE_NAME
    snapShot2_name = "%s_snapshot2" % config.VM_BASE_NAME
    snapshots = [snapShot1_name, snapShot2_name]
    disk_size_before = 0
    disk_size_after = 0

    def _make_snapshots(self):
        for snapshot in self.snapshots:
            logger.info("Creating snapshot %s", snapshot)
            assert ll_vms.addSnapshot(
                True, self.vm_name, description=snapshot
            ), "Creating snapshot of vm %s failed!" % self.vm_name
            logger.info("successfully created snapshot %s", snapshot)

    def _remove_snapshots(self):
        for snapshot in self.snapshots:
            logger.info("Removing snapshot %s", snapshot)
            assert ll_vms.removeSnapshot(
                True, vm=self.vm_name, description=snapshot,
                timeout=2100
            ), "Removing snapshot %s failed!" % snapshot

    @polarion("RHEVM3-11586")
    @tier2
    @bz({'1185782': {}})
    def test_delete_snapshot(self):
        """
        Create 2 snapshot, Deleting them and Check that actual disk
        size became the same it was before snapshots were made.
        """
        self.disk_alias = ll_vms.get_vm_bootable_disk(self.vm_name)
        diskObj = ll_disks.getVmDisk(self.vm_name, self.disk_alias)
        self.disk_size_before = diskObj.get_actual_size()
        logger.info(
            "Disk %s size - %s before snapshot creation",
            self.disk_alias, self.disk_size_before
        )

        logger.info("Make sure vm %s is up", self.vm_name)
        if ll_vms.get_vm_state(self.vm_name) == config.VM_DOWN:
            ll_vms.startVms([self.vm_name])
            ll_vms.waitForVMState(self.vm_name)
        self._make_snapshots()

        diskObj = ll_disks.getVmDisk(self.vm_name, self.disk_alias)
        logger.info(
            "Disk %s size - %s after snapshot",
            self.disk_alias, diskObj.get_actual_size()
        )

        ll_vms.stop_vms_safely([self.vm_name])
        self._remove_snapshots()

        diskObj = ll_disks.getVmDisk(self.vm_name, self.disk_alias)
        self.disk_size_after = diskObj.get_actual_size()
        logger.info(
            "Disk %s size - %s after snapshot deletion",
            self.disk_alias, self.disk_size_after
        )

        # VDSM allocates more 1 extent for metadata
        assert (
            self.disk_size_after - self.disk_size_before <= config.EXTENT_SIZE
        ), "Failed to auto shrink qcow volumes on merge of block volumes"


@pytest.mark.usefixtures(
    remove_vms.__name__,
)
class TestCase11830(TestCase):
    """
    Create 2 VMs from template at once.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Virtual_Machines_General
    """
    __test__ = True
    polarion_test_case = '11830'

    @polarion("RHEVM3-11830")
    @tier3
    def test_create_vm_from_template_basic_flow(self):
        """
        Start creating a VM from template
        Wait until template is locked
        Start creating another VM from the same template
        """
        self.vm_name_1 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

        self.vm_name_2 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        t = Thread(target=log_listener.watch_logs, args=(
            config.ENGINE_LOG, config.REGEX, None, config.LOG_LISTENER_TIMEOUT,
            config.VDC, config.HOSTS_USER, config.VDC_ROOT_PASSWORD
        ))
        logger.info("Waiting for createVolume command in engine.log")
        t.start()
        time.sleep(5)

        logger.info("Creating first vm %s", self.vm_name_1)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = storage_domain
        vm_args['name'] = self.vm_name_1
        vm_args['wait'] = False
        assert ll_vms.cloneVmFromTemplate(**vm_args)
        t.join()
        self.vm_names.append(self.vm_name_1)

        logger.info("Starting to create second vm %s", self.vm_name_2)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = storage_domain
        vm_args['name'] = self.vm_name_2
        assert ll_vms.cloneVmFromTemplate(**vm_args)
        self.vm_names.append(self.vm_name_2)

        logger.info("Starting VMs")
        ll_vms.start_vms(
            [self.vm_name_1, self.vm_name_2], wait_for_status=config.VM_UP,
            wait_for_ip=True
        )


@pytest.mark.usefixtures(
    initialize_object_names.__name__,
    remove_vms.__name__,
    wait_for_hosts_to_be_up.__name__,
)
class BaseClassKillProc(TestCase):
    """
    Kill 'vdsmd' on SPM when engine sends a regex command
    """
    __test__ = False
    polarion_test_case = ''
    regex = None

    def get_lv_count_before(self):
        self.spm_host = ll_hosts.get_spm_host(config.HOSTS)
        self.spm_ip = ll_hosts.get_host_ip(self.spm_host)
        self.lv_count_before = storage_helpers.get_lv_count_for_block_disk(
            self.spm_ip, config.HOSTS_PW
        )

    def kill_vdsm_on_spm_after_regex_copy_image(self):
        self.get_lv_count_before()

        t = Thread(target=log_listener.watch_logs, args=(
            config.ENGINE_LOG, self.regex, config.KILL_VDSM,
            config.LOG_LISTENER_TIMEOUT, config.VDC, config.HOSTS_USER,
            config.VDC_ROOT_PASSWORD, self.spm_ip, config.HOSTS_USER,
            config.HOSTS_PW
        ))
        t.start()
        time.sleep(5)
        testflow.step("Creating vm %s from template", self.vm_name)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = self.storage_domain
        vm_args['name'] = self.vm_name
        vm_args['clone'] = True
        testflow.step("Waiting for '%s' command in engine.log", self.regex)
        ll_vms.cloneVmFromTemplate(**vm_args)
        t.join()
        self.check_status_after_clone_from_template()

    def check_status_after_clone_from_template(self):
        status = True
        try:
            ll_vms.wait_for_vm_states(self.vm_name, config.VM_DOWN)
        except EntityNotFound:
            testflow.step("Creation of VM %s Failed", self.vm_name)

            testflow.step("Checking that there are no leftovers (LVs)")
            lv_count_after = storage_helpers.get_lv_count_for_block_disk(
                self.spm_ip, config.HOSTS_PW
            )
            assert lv_count_after == self.lv_count_before, (
                "There is a leftover LV after creation of VM failed"
            )
            status = False
        if status:
            self.vm_names.append(self.vm_name)
            testflow.step(
                "Creation of VM %s succeeded.  Starting it", self.vm_name
            )
            assert ll_vms.startVm(
                positive=True, vm=self.vm_name, wait_for_ip=True
            ), (
                "VM %s failed to start after killing 'vdsmd' during cloning "
                "from template %s" % (self.vm_name, config.TEMPLATE_NAME[0])
            )


class TestCase18979(BaseClassKillProc):
    """
    Kill 'vdsmd' on SPM when engine sends create image container to SPM -
    CreateVolumeContainerCommand
    """
    __test__ = True
    polarion_test_case = '18979'
    regex = 'CreateVolumeContainerCommand'

    @polarion("RHEVM-18979")
    @tier4
    def test_kill_vdsm_on_spm_after_regex_copy_image(self):
        self.kill_vdsm_on_spm_after_regex_copy_image()


class TestCase18980(BaseClassKillProc):
    """
     Kill 'vdsmd' on SPM after CopyVolumeDataVDSCommand has been sent to HSM
    """
    __test__ = True
    polarion_test_case = '18980'
    regex = 'CopyVolumeDataVDSCommand'

    @polarion("RHEVM-18980")
    @tier4
    def test_kill_vdsm_on_spm_after_regex_copy_image(self):
        self.kill_vdsm_on_spm_after_regex_copy_image()


class TestCase16794(BaseClassKillProc):
    """
     Restart 'ovirt-engine' after CopyVolumeDataVDSCommand has been sent to HSM
    """
    __test__ = True
    polarion_test_case = '16794'
    regex = 'CopyVolumeDataVDSCommand'

    @polarion("RHEVM-16794")
    @tier4
    def test_restart_ovirt_engine_copy_image(self):
        self.get_lv_count_before()

        t = Thread(target=log_listener.watch_logs, args=(
            config.ENGINE_LOG, self.regex, None,
            config.LOG_LISTENER_TIMEOUT, config.VDC,
            config.VDC_ROOT_USER, config.VDC_ROOT_PASSWORD,
        ))
        t.start()
        time.sleep(5)

        testflow.step("Creating vm %s from template", self.vm_name)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = self.storage_domain
        vm_args['wait'] = False
        vm_args['name'] = self.vm_name
        vm_args['clone'] = True
        testflow.step("Waiting for '%s' command in engine.log", self.regex)
        ll_vms.cloneVmFromTemplate(**vm_args)
        t.join()
        test_utils.restart_engine(config.ENGINE, 5, 30)
        hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)
        self.check_status_after_clone_from_template()


class TestCase18981(BaseClassKillProc):
    """
    Kill 'vdsmd' service on HSM during CopyVolumeDataVDSCommand
    """
    __test__ = True
    polarion_test_case = '18981'
    hsm_host = None

    @polarion("RHEVM-18981")
    @tier4
    def test_restart_hsm_after_regex_copy_data(self):
        self.get_lv_count_before()

        def f():
            """
            Function the searches for the first occurrence of the hsm host and
            initialize an Host resource object
            """
            log_listener.watch_logs(
                config.ENGINE_LOG, 'CopyVolumeDataVDSCommand', None,
                config.LOG_LISTENER_TIMEOUT, config.VDC, config.HOSTS_USER,
                config.VDC_ROOT_PASSWORD,
            )
            self.hsm_host = storage_helpers.get_hsm_host(
                config.JOB_ADD_VM_FROM_TEMPLATE, config.COPY_VOLUME_VERB
            )
        t = Thread(target=f, args=())
        t.start()
        time.sleep(5)

        testflow.step("Creating vm %s from template", self.vm_name)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = self.storage_domain
        vm_args['name'] = self.vm_name
        vm_args['clone'] = True
        vm_args['wait'] = False
        testflow.step(
            "Waiting for 'CopyVolumeDataVDSCommand' command in engine.log"
        )
        ll_vms.cloneVmFromTemplate(**vm_args)
        t.join()

        assert storage_helpers.kill_vdsm_on_hsm_executor(
            config.JOB_ADD_VM_FROM_TEMPLATE, config.COPY_VOLUME_VERB,
            hsm_host=self.hsm_host
        )
        self.check_status_after_clone_from_template()


@pytest.mark.usefixtures(
    deactivate_hsms.__name__,
)
class TestCase18982(BaseClassKillProc):
    """
    Create VM from Template and kill 'vdsmd' on SPM with only SPM and
    no HSM available
    """
    __test__ = True
    polarion_test_case = '18982'

    @polarion("RHEVM-18982")
    @tier3
    def test_create_vm_from_template_with_spm_only(self):
        self.get_lv_count_before()

        spm_object = rhevm_helpers.get_host_resource(
            self.spm_ip, config.HOSTS_PW
        )
        testflow.step("Creating vm %s from template", self.vm_name)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = self.storage_domain
        vm_args['name'] = self.vm_name
        vm_args['clone'] = True
        vm_args['wait'] = False
        assert ll_vms.cloneVmFromTemplate(**vm_args)
        testflow.step("Killing 'vdsmd' service on SPM host %s", self.spm_host)
        assert ll_hosts.kill_vdsmd(spm_object)
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        )
        self.check_status_after_clone_from_template()
