import pytest
import logging
from rhevmtests.storage import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
    jobs as ll_jobs,
)
import rhevmtests.storage.helpers as storage_helpers
from art.unittest_lib import testflow

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def initialize_params(request, storage):
    """
    Initialize parameters
    """
    self = request.node.cls

    self.vm_names = list()
    self.template_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
    )
    self.first_snapshot_description = (
        storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
    )


@pytest.fixture(scope='class')
def create_source_vm(request, storage):
    """
    Create a VM that will be restored from backup VM
    """
    self = request.node.cls

    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.src_vm = storage_helpers.create_unique_object_name(
        self.__name__, 'source_vm'
    )
    if not hasattr(self, 'deep_copy'):
        self.deep_copy = False
    testflow.setup(
        "Creating vm %s on storage domain %s",
        self.src_vm, self.storage_domain
    )
    args = config.create_vm_args.copy()
    args['storageDomainName'] = self.storage_domain
    args['vmName'] = self.src_vm
    args['deep_copy'] = self.deep_copy
    if not storage_helpers.create_vm_or_clone(**args):
        raise exceptions.VMException(
            "Failed to create or clone VM '%s'" % self.src_vm
        )
    self.vm_names.append(self.src_vm)

    testflow.setup("Creating snapshot of source VM %s", self.src_vm)
    assert ll_vms.addSnapshot(
        True, self.src_vm, self.first_snapshot_description
    ), ("Failed to create snapshot on VM '%s'" % self.src_vm)


@pytest.fixture(scope='class')
def create_backup_vm(request, storage):
    """
    Create a VM that will act as a backup VM
    """
    self = request.node.cls

    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage
        )[0]
    self.backup_vm = storage_helpers.create_unique_object_name(
        self.__name__, 'backup_vm'
    )
    if not hasattr(self, 'deep_copy'):
        self.deep_copy = False
    testflow.setup(
        "Creating vm %s on storage domain %s",
        self.backup_vm, self.storage_domain
    )
    args = config.create_vm_args.copy()
    args['storageDomainName'] = self.storage_domain
    args['vmName'] = self.backup_vm
    args['deep_copy'] = self.deep_copy
    if not storage_helpers.create_vm_or_clone(**args):
        raise exceptions.VMException(
            "Failed to create or clone VM '%s'" % self.backup_vm
        )
    self.vm_names.append(self.backup_vm)


@pytest.fixture(scope='class')
def attach_backup_disk(request, storage):
    """
    Attach a backup disk to VM
    """
    self = request.node.cls

    if self.attach_backup_disk:
        testflow.setup("Attach backup disk from source VM to backup VM")
        assert ll_vms.attach_backup_disk_to_vm(
            self.src_vm, self.backup_vm, self.first_snapshot_description
        ), ("Failed to attach backup disk to backup vm %s" % self.backup_vm
            )


@pytest.fixture(scope='class')
def finalizer(request, storage):
    """
    Clean the environment
    """
    self = request.node.cls

    def fin():
        """
        Remove created VMs
        """
        testflow.teardown("Removing VMs: %s", ', '.join(self.vm_names))
        if not ll_vms.stop_vms_safely(self.vm_names):
            logger.error(
                "Failed to power off VMs %s", ', '.join(self.vm_names)
            )
        for disk in ll_vms.getVmDisks(self.backup_vm):
            if not ll_vms.removeDisk(True, self.backup_vm, disk.get_alias()):
                logger.error(
                    "Failed to remove disk '%s' from VM '%s'",
                    disk.get_alias(), self.backup_vm
                )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        if not ll_vms.safely_remove_vms(self.vm_names):
            logger.error(
                "Failed to power off and remove VMs %s",
                ', '.join(self.vm_names)
            )
    request.addfinalizer(fin)
