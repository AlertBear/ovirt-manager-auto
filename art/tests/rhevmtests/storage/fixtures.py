import pytest
import logging
import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    storagedomains as ll_sd,
    jobs as ll_jobs,
)
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def create_vm(request):
    """
    Create VM and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error(
                "Failed to power off and remove VM %s",
                self.vm_name
            )
            self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.vm_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    )
    if not hasattr(self, 'installation'):
        self.installation = True
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.vm_name
    vm_args['installation'] = self.installation
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException(
            "Failed to create VM %s" % self.vm_name
        )


@pytest.fixture(scope='class')
def add_disk(request):
    """
    Add disk and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        if ll_disks.checkDiskExists(True, self.disk_name):
            ll_disks.wait_for_disks_status([self.disk_name])
            if not ll_disks.deleteDisk(True, self.disk_name):
                self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    if not hasattr(self, 'disk_size'):
        self.disk_size = config.DISK_SIZE
    if not hasattr(self, 'add_disk_params'):
        self.add_disk_params = {
            'format': config.COW_DISK,
            'sparse': True,
        }

    self.disk_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DISK
    )

    if not ll_disks.addDisk(
        True, provisioned_size=self.disk_size,
        storagedomain=self.storage_domain, alias=self.disk_name,
        **self.add_disk_params
    ):
        raise exceptions.DiskException(
            "Failed to create disk %s" % self.disk_name
        )
    ll_disks.wait_for_disks_status([self.disk_name])


@pytest.fixture(scope='class')
def attach_disk(request):
    """
    Attach a disk to VM
    """
    self = request.node.cls

    if not ll_disks.attachDisk(
        True, alias=self.disk_name, vm_name=self.vm_name
    ):
        raise exceptions.DiskException(
            "Failed to attach disk %s to VM %s" %
            (self.disk_name, self.vm_name)
        )
    ll_disks.wait_for_disks_status([self.disk_name])


@pytest.fixture(scope='class')
def update_vm(request):
    """
    Update VM
    """
    self = request.node.cls

    if not ll_vms.updateVm(True, self.vm_name, **self.update_vm_params):
        raise exceptions.VMException(
            "Failed to update vm %s with params %s" %
            (self.disk_name, self.update_vm_params)
        )


@pytest.fixture(scope='class')
def create_snapshot(request):
    """
    Create snapshot of VM
    """
    self = request.node.cls

    if not hasattr(self, 'snapshot_description'):
        self.snapshot_description = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
    if not ll_vms.addSnapshot(True, self.vm_name, self.snapshot_description):
        raise exceptions.VMException(
            "Failed to create snapshot of VM %s" % self.vm_name
        )
    ll_vms.wait_for_vm_snapshots(
        self.vm_name, [config.SNAPSHOT_OK], self.snapshot_description
    )
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])


@pytest.fixture(scope='class')
def preview_snapshot(request):
    """
    Create snapshot of VM
    """
    self = request.node.cls

    if not ll_vms.preview_snapshot(
        True, self.vm_name, self.snapshot_description
    ):
        raise exceptions.SnapshotException(
            "Failed to preview snapshot %s" % self.snapshot_description
        )
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])


@pytest.fixture(scope='class')
def undo_snapshot(request):
    """
    Undo snapshot
    """
    self = request.node.cls

    def finalizer():
        if not ll_vms.undo_snapshot_preview(
            True, self.vm_name
        ):
            raise exceptions.SnapshotException(
                "Failed to undo previewed snapshot %s" %
                self.snapshot_description
            )
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def delete_disks(request):
    """
    Delete disks
    """
    self = request.node.cls

    def finalizer():
        for disk in self.disks_to_remove:
            if ll_disks.checkDiskExists(True, disk):
                ll_disks.wait_for_disks_status([disk])
                if not ll_disks.deleteDisk(True, disk):
                    self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
    if not hasattr(self, 'disk_name'):
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
    if not hasattr(self, 'disks_to_remove'):
        self.disks_to_remove = list()


@pytest.fixture(scope='function')
def poweroff_vm(request):
    """
    Power off VM
    """
    self = request.node.cls

    def finalizer():
        if not ll_vms.stop_vms_safely([self.vm_name]):
            logger.error("Failed to power off VM %s", self.vm_name)
            self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
