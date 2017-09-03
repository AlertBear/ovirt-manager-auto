"""
Storage live wipe after delete
TODO: The following link will change to 3_5 from 3_6
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Wipe_After_Delete
"""
import logging
import pytest
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
from art.unittest_lib.common import StorageTest as BaseTestCase, testflow

from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier3,
)
from rhevmtests.storage.storage_wipe_after_delete import config
from art.test_handler.settings import ART_CONFIG
from fixtures import (
    update_storage_domain_wipe_after_delete, add_disk_start_vm
)
from rhevmtests.storage.fixtures import (
    create_vm,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

logger = logging.getLogger(__name__)
FILE_TO_WATCH = config.VDSM_LOG
TASK_TIMEOUT = 120
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP


class CommonUsage(BaseTestCase):
    """
    Base class
    """
    __test__ = False

    def _perform_operation(self, update=True, wipe_after_delete=False):
        """
        Adding new disk, edit the wipe after delete flag if update=True,
        and removes the disk to see in log file that the operation succeeded
        """
        testflow.step(
            "Adding new disk %s to vm %s", config.DISK_ALIAS, self.vm_name
        )
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
        host = ll_hosts.get_spm_host(config.HOSTS)
        logger.info("Host %s", host)
        self.host_ip = ll_hosts.get_host_ip(host)
        assert self.host_ip
        disk_obj = ll_disks.getVmDisk(self.vm_name, disk_id=self.disk_id)
        regex = (
            config.REGEX_DD_WIPE_AFTER_DELETE % disk_obj.get_image_id()
        )

        if update:
            testflow.step(
                "Update disk's %s wipe_after_delete flag to 'True'",
                config.DISK_ALIAS
            )
            assert ll_disks.updateDisk(
                True, vmName=self.vm_name, id=self.disk_id,
                wipe_after_delete=True
            )
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        testflow.step("Removing disk %s", config.DISK_ALIAS)

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


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase5116(CommonUsage):
    """
    wipe after delete on hotplugged disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    polarion_test_case = '5116'

    @polarion("RHEVM3-5116")
    @tier2
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

        self.disk_id = [
            d.get_id() for d in ll_vms.getVmDisks(self.vm_name) if not
            ll_vms.is_bootable_disk(self.vm_name, d.get_id())
        ][0]

        assert ll_disks.updateDisk(
            True, vmName=self.vm_name, id=self.disk_id,
            wipe_after_delete=True
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase10443(CommonUsage):
    """
    wipe after delete on attached disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    polarion_test_case = '10443'

    @polarion("RHEVM3-10443")
    @tier2
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


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase5113(CommonUsage):
    """
    Checking functionality - checked box
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = (ISCSI in ART_CONFIG['RUN']['storages'] or
                FCP in ART_CONFIG['RUN']['storages'])
    storages = set([ISCSI, FCP])
    polarion_test_case = '5113'

    @polarion("RHEVM3-5113")
    @tier2
    def test_live_edit_wipe_after_delete(self):
        """
        Actions:
            - Checks that 'regex' is sent in vdsm log
        Expected Results:
            - dd command from /dev/zero to relevant image in vdsm log
        """
        self._perform_operation(True)


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase5115(CommonUsage):
    """
    Checking functionality - unchecked box negative case
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    polarion_test_case = '5115'

    @polarion("RHEVM3-5115")
    @tier2
    def test_uncheck_wipe_after_delete(self):
        """
        Actions:
            - Checks that 'regex' is not sent in vdsm log
        Expected Results:
            - dd command not sent from /dev/zero to relevant image in vdsm log
        """
        self._perform_operation(False)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk_start_vm.__name__
)
class TestCase11864(CommonUsage):
    """
    Wipe after delete with LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    polarion_test_case = '11864'
    disk_name = "disk_%s" % polarion_test_case

    @polarion("RHEVM3-11864")
    @tier3
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
        ll_vms.migrate_vm_disk(
            self.vm_name, self.disk_name, second_domain, wait=False
        )
        ll_disks.wait_for_disks_status(
            [self.disk_name], status=config.DISK_LOCKED
        )
        status = ll_disks.updateDisk(
            False, vmName=self.vm_name, id=self.disk_id,
            wipe_after_delete=False
        )
        ll_vms.waitForVmsDisks(self.vm_name)
        ll_jobs.wait_for_jobs(
            [config.JOB_LIVE_MIGRATE_DISK, config.JOB_REMOVE_SNAPSHOT]
        )
        if not status:
            raise exceptions.DiskException("Disk update should be blocked")


@pytest.mark.usefixtures(
    create_vm.__name__,
    update_storage_domain_wipe_after_delete.__name__,
)
class TestCase10432(CommonUsage):
    """
    Remove disk from configured domain with wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Wipe_After_Delete
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    polarion_test_case = '10432'

    @polarion("RHEVM3-10432")
    @tier2
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
