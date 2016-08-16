import pytest
import logging
import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    storagedomains as ll_sd,
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
    self.storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )[0]
    self.vm_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    )
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
    if self.storage_domain is None:
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.disk_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DISK
    )
    if not ll_disks.addDisk(
        True, provisioned_size=self.disk_size,
        storagedomain=self.storage_domain, alias=self.disk_name,
        format=config.COW_DISK, sparse=True
    ):
        raise exceptions.DiskException(
            "Failed to create disk %s" % self.disk_name
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
            "Failed to disable virtio-scsi support of vm %s" %
            self.disk_name
        )


@pytest.fixture(scope='class')
def delete_disk(request):
    """
    Delete disk
    """
    self = request.node.cls

    def finalizer():
        if ll_disks.checkDiskExists(True, self.disk_name):
            ll_disks.wait_for_disks_status([self.disk_name])
            if not ll_disks.deleteDisk(True, self.disk_name):
                self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
    if self.disk_name is None:
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
