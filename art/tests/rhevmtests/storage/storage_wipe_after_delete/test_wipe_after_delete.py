"""
Storage live wipe after delete - 14205
https://tcms.engineering.redhat.com/plan/14205/
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from art.rhevm_api.tests_lib.low_level.disks import getVmDisk
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost, getHostIP
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.utils.log_listener import watch_logs
from art.unittest_lib.common import StorageTest as BaseTestCase
from art.rhevm_api.tests_lib.high_level.datacenters import (
    build_setup,
    clean_datacenter,
)

from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, removeDisk, start_vms,
    getVmDisks, updateVmDisk, live_migrate_vm_disk, addDisk, removeVms,
)
from art.rhevm_api.utils.test_utils import get_api

from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr
from rhevmtests.storage.storage_wipe_after_delete import config
from rhevmtests.storage.helpers import create_vm_or_clone
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

VM_API = get_api('vm', 'vms')

ENUMS = config.ENUMS
BLOCK_TYPES = (ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp'])

TCMS_PLAN_ID = '14205'

FILE_TO_WATCH = "/var/log/vdsm/vdsm.log"

TASK_TIMEOUT = 5 * 60

GB = config.GB
vmArgs = {'positive': True,
          'vmDescription': config.VM_NAME,
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.COW_DISK,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.DISK_SIZE,
          'nic': config.NIC_NAME[0],
          'image': config.COBBLER_PROFILE,
          'useAgent': True,
          'os_type': config.OS_TYPE,
          'user': config.VM_USER,
          'password': config.VM_PASSWORD,
          'network': config.MGMT_BRIDGE
          }

VM_NAME = config.VM_NAME + "_%s"
VMS_NAMES = []
ISCSI = config.STORAGE_TYPE_ISCSI


def setup_module():
    """
    Sets up the environment - creates vms with all disk types and formats
    """
    if not config.GOLDEN_ENV:
        logger.info("Preparing datacenter %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)

        build_setup(config=config.PARAMETERS,
                    storage=config.PARAMETERS,
                    storage_type=config.STORAGE_TYPE)

    exs = []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for storage_type in config.STORAGE_SELECTOR:
            storage_domain = getStorageDomainNamesForType(
                config.DATA_CENTER_NAME, storage_type)[0]

            vm_name = VM_NAME % storage_type
            VMS_NAMES.append(vm_name)

            args = vmArgs.copy()
            args['storageDomainName'] = storage_domain
            args['vmName'] = vm_name

            logger.info('Creating vm %s and installing OS on it', vm_name)

            exs.append((vm_name, executor.submit(create_vm_or_clone, **args)))

    for vm_name, ex in exs:
        if not ex.result():
            raise Exception("Unable to create vm %s" % vm_name)

    logger.info('Shutting down vms %s', VMS_NAMES)
    stop_vms_safely(VMS_NAMES)


def teardown_module():
    """
    Clean datacenter
    """
    if not config.GOLDEN_ENV:
        logger.info('Cleaning datacenter')
        clean_datacenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                         vdc_password=config.VDC_PASSWORD)

    else:
        stop_vms_safely(VMS_NAMES)
        assert removeVms(True, VMS_NAMES)


class CommonUsage(BaseTestCase):
    """
    Base class
    """
    __test__ = False
    vm_name = None

    def setUp(self):
        self.vm_name = VM_NAME % self.storage
        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        assert removeDisk(True, self.vm_name, self.disk_name)

    def _remove_disks(self, disks_names):
        """
        Removes created disks
        """
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

        for disk in disks_names:
            logger.info("Deleting disk %s", disk)
            if not disks.deleteDisk(True, disk):
                logger.error("Failed to remove disk %s", disk)

    def _perform_operation(self, update=True):
        """
        Adding new disk, edit the wipe after delete flag if update=True,
        and removes the disk to see in log file that the operation succeeded
        """
        assert addDisk(True, self.vm_name, config.DISK_SIZE,
                       storagedomain=self.storage_domain, sparse=True,
                       wipe_after_delete=False, interface=config.VIRTIO)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        waitForVMState(self.vm_name)

        self.disk_name = [d.get_alias() for d in getVmDisks(self.vm_name) if
                          not d.get_bootable()][0]
        logger.info("Selecting host from %s", config.HOSTS)
        host = getSPMHost(config.HOSTS)
        logger.info("Host %s", host)
        self.host_ip = getHostIP(host)
        assert self.host_ip
        disk_obj = getVmDisk(self.vm_name, self.disk_name)
        self.regex = self.regex % disk_obj.get_image_id()

        if update:
            assert updateVmDisk(True, self.vm_name, self.disk_name,
                                wipe_after_delete=True)

        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

        t = threading.Thread(
            target=watch_logs,
            args=(
                FILE_TO_WATCH,
                self.regex,
                '',
                TASK_TIMEOUT,
                self.host_ip,
                'root',
                config.HOSTS_PW))

        try:
            t.start()

            time.sleep(5)

            self.assertTrue(removeDisk(True, self.vm_name, self.disk_name),
                            "Failed to remove disk %s" % self.disk_name)

        finally:
            t.join(TASK_TIMEOUT)
            wait_for_jobs()


@attr(tier=1)
class TestCase379370(CommonUsage):
    """
    wipe after delete on hotplugged disks
    https://tcms.engineering.redhat.com/case/379370/
    """
    __test__ = True
    tcms_test_case = '379370'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_behavior_on_hotplugged_disks(self):
        """
        Actions:
            1.add vm + disk
            2.create a new disk
            3.run the vm
            3.hot plug the disk to the vm
            4.go to vm->disks
        Expected Results:
            - operation should succeed
        """
        start_vms([self.vm_name], 1, wait_for_ip=False)
        waitForVMState(self.vm_name)

        addDisk(True, self.vm_name, config.DISK_SIZE,
                storagedomain=self.storage_domain, sparse=True,
                wipe_after_delete=False, interface=config.VIRTIO)

        self.disk_name = [d.get_alias() for d in getVmDisks(self.vm_name) if
                          not d.get_bootable()][0]

        assert updateVmDisk(True, self.vm_name, self.disk_name,
                            wipe_after_delete=True)


@attr(tier=0)
class TestCase379367(CommonUsage):
    """
    Checking functionality - checked box
    https://tcms.engineering.redhat.com/case/379367/
    """
    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])
    tcms_test_case = '379367'
    disk_name = None
    regex = 'dd oflag=direct if=/dev/zero of=.*/%s'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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


@attr(tier=1)
class TestCase384228(CommonUsage):
    """
    Wipe after delete with LSM
    https://tcms.engineering.redhat.com/case/384228/
    """
    __test__ = True
    tcms_test_case = '384228'
    disk_name = "disk_%s" % tcms_test_case
    regex = 'dd oflag=direct if=/dev/zero of=.*/%s'

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        super(TestCase384228, self).setUp()
        assert addDisk(True, self.vm_name, config.DISK_SIZE,
                       storagedomain=self.storage_domain, sparse=True,
                       wipe_after_delete=True, interface=config.VIRTIO,
                       alias=self.disk_name)

        start_vms([self.vm_name], 1, wait_for_ip=False)
        waitForVMState(self.vm_name)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_live_migration_wipe_after_delete(self):
        """
        Actions:
            - add a vm + block disk (select the "wipe after delete box")
            - install Os on bootable
            - live migrate the disk and uncheck the "wipe after delete box"
        Expected Results:
            - editing should be blocked
        """
        second_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[1]
        live_migrate_vm_disk(self.vm_name, self.disk_name, second_domain,
                             wait=False)

        assert updateVmDisk(False, self.vm_name, self.disk_name,
                            wipe_after_delete=False)

        wait_for_jobs()
