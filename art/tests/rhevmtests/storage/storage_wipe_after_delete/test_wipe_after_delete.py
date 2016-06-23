"""
Storage live wipe after delete
TODO: The following link will change to 3_5 from 3_6
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Wipe_After_Delete
"""
import logging
import threading
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    vms as ll_vms,
    jobs as ll_jobs,
    storagedomains as ll_sd,
)
from art.rhevm_api.utils.log_listener import watch_logs
from art.unittest_lib.common import StorageTest as BaseTestCase

from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from rhevmtests.storage.storage_wipe_after_delete import config
from rhevmtests.storage.helpers import create_vm_or_clone
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)
FILE_TO_WATCH = config.VDSM_LOG
REGEX_TEMPLATE = 'dd if=/dev/zero of=.*/%s'
TASK_TIMEOUT = 120
VM_NAMES = dict()
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP


def setup_module():
    """
    Sets up the environment - creates vms with all disk types and formats
    """
    global VM_NAMES
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]

        vm_name = config.VM_NAME % storage_type
        VM_NAMES[storage_type] = vm_name
        args = config.create_vm_args.copy()
        args['storageDomainName'] = storage_domain
        args['vmName'] = vm_name

        logger.info('Creating vm %s and installing OS on it', vm_name)
        if not create_vm_or_clone(**args):
            raise exceptions.VMException("Unable to create vm %s" % vm_name)


def teardown_module():
    """
    Clean datacenter
    """
    if not ll_vms.safely_remove_vms(VM_NAMES.values()):
        raise exceptions.VMException("Failed to remove vms in teardown")
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])


class CommonUsage(BaseTestCase):
    """
    Base class
    """
    __test__ = False
    vm_name = None
    disk_id = None

    def setUp(self):
        self.vm_name = VM_NAMES[self.storage]
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

    def tearDown(self):
        if ll_disks.checkDiskExists(True, self.disk_id, 'id'):
            ll_vms.stop_vms_safely([self.vm_name])
            ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
            if not ll_vms.removeDisk(
                True, self.vm_name, disk_id=self.disk_id
            ):
                logger.error(
                    "Failed to remove disk attached to vm %s", self.vm_name
                )
                BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()

    def _perform_operation(self, update=True, wipe_after_delete=False):
        """
        Adding new disk, edit the wipe after delete flag if update=True,
        and removes the disk to see in log file that the operation succeeded
        """
        assert ll_vms.addDisk(
            True, self.vm_name, config.DISK_SIZE,
            storagedomain=self.storage_domain, sparse=True,
            wipe_after_delete=wipe_after_delete, interface=config.VIRTIO,
            alias=config.DISK_ALIAS
        )
        ll_vms.start_vms([self.vm_name], wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)

        self.disk_id = ll_disks.get_disk_obj(config.DISK_ALIAS).get_id()
        logger.info("Selecting host from %s", config.HOSTS)
        host = ll_hosts.getSPMHost(config.HOSTS)
        logger.info("Host %s", host)
        self.host_ip = ll_hosts.getHostIP(host)
        assert self.host_ip
        disk_obj = ll_disks.getVmDisk(self.vm_name, disk_id=self.disk_id)
        regex = REGEX_TEMPLATE % disk_obj.get_image_id()

        if update:
            assert ll_vms.updateVmDisk(
                True, self.vm_name, config.DISK_ALIAS, disk_id=self.disk_id,
                wipe_after_delete=True
            )
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)

        t = threading.Timer(
            5.0, ll_vms.removeDisk, (
                True, self.vm_name, None, True, self.disk_id
            )
        )
        t.start()
        found_regex, _ = watch_logs(
            FILE_TO_WATCH, regex, None, TASK_TIMEOUT, self.host_ip,
            config.HOSTS_USER, config.HOSTS_PW
        )

        t.join(TASK_TIMEOUT)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        if not found_regex and (update or wipe_after_delete):
            raise exceptions.DiskException(
                "Wipe after delete functionality is not working"
            )
        elif found_regex and not update and not wipe_after_delete:
            raise exceptions.DiskException(
                "Wipe after delete functionality should not work"
            )


@attr(tier=2)
class TestCase5116(CommonUsage):
    """
    wipe after delete on hotplugged disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '5116'

    @polarion("RHEVM3-5116")
    def test_behavior_on_hotplugged_disks(self):
        """
        Actions:
            1.add vm + disk
            2.create a new disk
            3.run the vm
            3.hot plug the disk to the vm
        Expected Results:
            - operation should succeed
        """
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)

        ll_vms.addDisk(
            True, self.vm_name, config.DISK_SIZE,
            storagedomain=self.storage_domain, sparse=True,
            wipe_after_delete=False, interface=config.VIRTIO,
            alias=config.DISK_ALIAS
        )

        self.disk_id = [d.get_id() for d in ll_vms.getVmDisks(self.vm_name) if
                        not d.get_bootable()][0]

        assert ll_vms.updateVmDisk(
            True, self.vm_name, config.DISK_ALIAS, disk_id=self.disk_id,
            wipe_after_delete=True
        )


@attr(tier=2)
class TestCase10443(CommonUsage):
    """
    wipe after delete on attached disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '10443'

    @polarion("RHEVM3-10443")
    def test_wipe_after_delete_on_attached_disk(self):
        """
        Actions:
            1.add vm + disk
            2.create a new disk
            3.run the vm
            3.Attach the disk to the vm
            4.go to vm->disks
        Expected Results:
            - operation should succeed
        """
        self._perform_operation(False, True)

    def tearDown(self):
        logger.info("Test finished")


@attr(tier=1)
class TestCase5113(CommonUsage):
    """
    Checking functionality - checked box
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = (ISCSI in opts['storages'] or FCP in opts['storages'])
    storages = set([ISCSI, FCP])
    polarion_test_case = '5113'

    @polarion("RHEVM3-5113")
    def test_live_edit_wipe_after_delete(self):
        """
        Actions:
            - Checks that 'regex' is sent in vdsm log
        Expected Results:
            - dd command from /dev/zero to relevant image in vdsm log
        """
        self._perform_operation(True)

    def tearDown(self):
        logger.info("Test finished")


@attr(tier=2)
class TestCase5115(CommonUsage):
    """
    Checking functionality - unchecked box negative case
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '5115'

    @polarion("RHEVM3-5115")
    def test_uncheck_wipe_after_delete(self):
        """
        Actions:
            - Checks that 'regex' is not sent in vdsm log
        Expected Results:
            - dd command not sent from /dev/zero to relevant image in vdsm log
        """
        self._perform_operation(False)

    def tearDown(self):
        logger.info("Test finished")


@attr(tier=2)
class TestCase11864(CommonUsage):
    """
    Wipe after delete with LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    # Bugzilla history:
    # 1251956 - Live storage migration is broken
    # 1259785 - after live migrate a Virtio RAW disk, job
    # stays in status STARTED
    # 1292509 - It is possible to edit a disk using the api during LSM
    # except the snapshot operation phase
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '11864'
    disk_name = "disk_%s" % polarion_test_case

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        super(TestCase11864, self).setUp()
        assert ll_vms.addDisk(
            True, self.vm_name, config.DISK_SIZE,
            storagedomain=self.storage_domain, sparse=True,
            wipe_after_delete=True, interface=config.VIRTIO,
            alias=self.disk_name
        )

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)

    @polarion("RHEVM3-11864")
    def test_live_migration_wipe_after_delete(self):
        """
        Actions:
            - add a vm + block disk (select the "wipe after delete box")
            - install Os on bootable
            - live migrate the disk and uncheck the "wipe after delete box"
        Expected Results:
            - editing should be blocked
        """
        second_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[1]
        self.disk_id = ll_disks.getVmDisk(
            self.vm_name, alias=self.disk_name
        ).get_id()
        ll_vms.live_migrate_vm_disk(
            self.vm_name, self.disk_name, second_domain, wait=False
        )
        ll_disks.wait_for_disks_status(
            [self.disk_name], status=config.DISK_LOCKED
        )
        status = ll_vms.updateVmDisk(
            False, self.vm_name, self.disk_name, wipe_after_delete=False,
            disk_id=self.disk_id
        )
        ll_vms.waitForVmsDisks(self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        if not status:
            raise exceptions.DiskException("Disk update should be blocked")


@attr(tier=2)
class TestCase10432(CommonUsage):
    """
    Remove disk from configured domain with wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '10432'
    sd_args = dict()

    def setUp(self):
        """
        Update storage domain wipe after delete flag
        """
        super(TestCase10432, self).setUp()
        self.sd_args['wipe_after_delete'] = True
        ll_sd.updateStorageDomain(
            True, self.storage_domain, **self.sd_args
        )

    @polarion("RHEVM3-10432")
    def test_domain_configured_with_wipe_after_delete(self):
        """
        Actions:
            1.Configure storage domain with wipe after delete
            2.Create a new disk on that domain
            3.Run the vm
            4.Attach the disk to the vm
            5.Remove the disk
        Expected Results:
            - Operation should succeed
        """
        self._perform_operation(False)

    def tearDown(self):
        logger.info("Test finished")
