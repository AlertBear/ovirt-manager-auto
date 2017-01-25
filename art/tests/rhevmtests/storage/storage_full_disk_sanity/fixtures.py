import pytest
import logging
import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
    disks as ll_disks,
    jobs as ll_jobs,
)
import rhevmtests.storage.helpers as storage_helpers
from art.unittest_lib.common import testflow
logger = logging.getLogger(__name__)
STATELESS_SNAPSHOT_DESCRIPTION = 'stateless snapshot'


@pytest.fixture(scope='class')
def create_second_vm(request):
    """
    Create VM and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        if not ll_vms.safely_remove_vms([self.second_vm_name]):
            logger.error(
                "Failed to power off and remove VM %s",
                self.second_vm_name
            )
            self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.second_vm_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    )
    if not hasattr(self, 'installation'):
        self.installation = True
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.second_vm_name
    vm_args['installation'] = self.installation
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException(
            "Failed to create VM %s" % self.second_vm_name
        )


@pytest.fixture()
def poweroff_vm_and_wait_for_stateless_to_remove(request):
    """
    Power off VM and wait for stateless snapshot to be removed
    """
    self = request.node.cls

    def finalizer():
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off VM %s", self.vm_name
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
        ll_vms.wait_for_snapshot_gone(
            self.vm_name, STATELESS_SNAPSHOT_DESCRIPTION,
        )
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_direct_lun_params(request):
    """
    Initialize direct lun parameters
    """
    self = request.node.cls

    self.disk_alias = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DIRECT_LUN
    )
    self.lun_kwargs = config.BASE_KWARGS.copy()
    self.lun_kwargs["alias"] = self.disk_alias
    self.template_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture(scope='class')
def delete_direct_lun_disk(request):
    """
    Removes direct lun disk
    Created due to direct lun disk status N/A unlike other type disks
    """
    self = request.node.cls

    def finalizer():
        if ll_disks.checkDiskExists(True, self.disk_alias):
            testflow.teardown("Deleting disk %s", self.disk_alias)
            assert ll_disks.deleteDisk(True, self.disk_alias), (
                "Failed to delete disk %s" % self.disk_alias
            )
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
    request.addfinalizer(finalizer)
