import pytest
import logging
import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
)
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)


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


@pytest.fixture(scope='function')
def poweroff_vm_and_wait_for_stateless_to_remove(request):
    """
    Power off VM
    """
    self = request.node.cls

    def finalizer():
        if not ll_vms.stop_vms_safely([self.vm_name]):
            logger.error("Failed to power off VM %s", self.vm_name)
            self.test_failed = True
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
        self.teardown_exception()
    request.addfinalizer(finalizer)
