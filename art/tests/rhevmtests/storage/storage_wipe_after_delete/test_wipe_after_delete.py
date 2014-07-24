"""
Storage live wipe after delete - 14205
https://tcms.engineering.redhat.com/plan/14205/
"""

import logging
import threading
import time
from utilities.utils import getIpAddressByHostName
from art.rhevm_api.tests_lib.low_level.disks import getVmDisk
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.utils.log_listener import watch_logs
from art.unittest_lib.common import StorageTest as BaseTestCase
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup

from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    get_master_storage_domain_name,
    cleanDataCenter,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    createVm, stop_vms_safely, waitForVMState, removeDisk, start_vms,
    getVmDisks, updateVmDisk, live_migrate_vm_disk, addDisk,
)
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler import exceptions

from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr
from rhevmtests.storage.storage_wipe_after_delete import config


logger = logging.getLogger(__name__)

VM_API = get_api('vm', 'vms')

ENUMS = config.ENUMS
BLOCK_TYPES = (ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp'])

TCMS_PLAN_ID = '14205'

FILE_TO_WATCH = "/var/log/vdsm/vdsm.log"

SD_NAME_0 = config.SD_NAMES_LIST[0]
SD_NAME_1 = config.SD_NAMES_LIST[1]
TASK_TIMEOUT = 5 * 60

GB = config.GB
vmArgs = {'positive': True,
          'vmName': config.VM_NAME,
          'vmDescription': config.VM_NAME,
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.COW_DISK,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.DISK_SIZE,
          'nic': config.HOST_NICS[0],
          'image': config.COBBLER_PROFILE,
          'useAgent': True,
          'os_type': config.OS_TYPE,
          'user': config.VM_USER,
          'password': config.VM_PASSWORD,
          'network': config.MGMT_BRIDGE
          }


def setup_module():
    """
    Sets up the environment - creates vms with all disk types and formats
    """
    logger.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)

    build_setup(config=config.PARAMETERS,
                storage=config.PARAMETERS,
                storage_type=config.STORAGE_TYPE)

    vmArgs['storageDomainName'] = (
        get_master_storage_domain_name(config.DATA_CENTER_NAME)
    )

    logger.info('Creating vm and installing OS on it')

    if not createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % config.VM_NAME)

    logger.info('Shutting down VM %s', config.VM_NAME)
    stop_vms_safely([config.VM_NAME])


def teardown_module():
    """
    Clean datacenter
    """
    logger.info('Cleaning datacenter')
    cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class CommonUsage(BaseTestCase):
    """
    Base class
    """
    __test__ = False

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        assert removeDisk(True, config.VM_NAME, self.disk_name)

    def _remove_disks(self, disks_names):
        """
        Removes created disks
        """
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)

        for disk in disks_names:
            logger.info("Deleting disk %s", disk)
            if not disks.deleteDisk(True, disk):
                logger.error("Failed to remove disk %s", disk)

    def _perform_operation(self, update=True):
        """
        Adding new disk, edit the wipe after delete flag if update=True,
        and removes the disk to see in log file that the operation succeeded
        """
        assert addDisk(True, config.VM_NAME, config.DISK_SIZE, SD_NAME_0,
                       wipe_after_delete=False, interface=config.VIRTIO)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        self.disk_name = [d.get_alias() for d in getVmDisks(config.VM_NAME) if
                          not d.get_bootable()][0]
        host = getSPMHost(config.HOSTS)
        self.host_ip = getIpAddressByHostName(host)
        disk_obj = getVmDisk(config.VM_NAME, self.disk_name)
        self.regex = self.regex % disk_obj.get_image_id()

        if update:
            assert updateVmDisk(True, config.VM_NAME, self.disk_name,
                                wipe_after_delete=True)

        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)

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

            self.assertTrue(removeDisk(True, config.VM_NAME, self.disk_name),
                            "Failed to remove disk %s" % self.disk_name)

        finally:
            t.join(TASK_TIMEOUT)
            wait_for_jobs()


@attr(tier=1)
class TestCase379365(CommonUsage):
    """
    Check wipe after delete functionality
    https://tcms.engineering.redhat.com/case/379365/
    """
    __test__ = True
    tcms_test_case = (
        '379365' if config.STORAGE_TYPE in config.BLOCK_TYPES else '384227'
    )
    disk_name = None

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_live_edit_wipe_after_delete(self):
        """
        Actions:
            - add vm + disk (do not check Wipe after Delete box)
              and run it
            - check the "Wipe after Delete box" and press Ok
        Expected Results:
            - no Errors should appear
        """
        addDisk(True, config.VM_NAME, config.DISK_SIZE, SD_NAME_0,
                wipe_after_delete=False, interface=config.VIRTIO)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        self.disk_name = [d.get_alias() for d in getVmDisks(config.VM_NAME) if
                          not d.get_bootable()][0]

        assert updateVmDisk(True, config.VM_NAME, self.disk_name,
                            wipe_after_delete=True)


@attr(tier=2)
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
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        addDisk(True, config.VM_NAME, config.DISK_SIZE, SD_NAME_0,
                wipe_after_delete=False, interface=config.VIRTIO)

        self.disk_name = [d.get_alias() for d in getVmDisks(config.VM_NAME) if
                          not d.get_bootable()][0]

        assert updateVmDisk(True, config.VM_NAME, self.disk_name,
                            wipe_after_delete=True)


@attr(tier=2)
class TestCase379367(CommonUsage):
    """
    Checking functionality - checked box
    https://tcms.engineering.redhat.com/case/379367/
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
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


@attr(tier=2)
class TestCase384228(CommonUsage):
    """
    Wipe after delete with LSM
    https://tcms.engineering.redhat.com/case/384228/

    __test__ = False:
    https://bugzilla.redhat.com/show_bug.cgi?id=1124321
    """
    __test__ = False
    tcms_test_case = '384228'
    disk_name = "disk_%s" % tcms_test_case
    regex = 'dd oflag=direct if=/dev/zero of=.*/%s'

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        assert addDisk(True, config.VM_NAME, config.DISK_SIZE, SD_NAME_0,
                       wipe_after_delete=True, interface=config.VIRTIO,
                       alias=self.disk_name)

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

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
        live_migrate_vm_disk(config.VM_NAME, self.disk_name, SD_NAME_1,
                             wait=False)

        assert updateVmDisk(False, config.VM_NAME, self.disk_name,
                            wipe_after_delete=False)

        wait_for_jobs()
