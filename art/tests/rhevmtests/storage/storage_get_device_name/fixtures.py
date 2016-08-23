import pytest
import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
)
from rhevmtests.storage.fixtures import (
    add_disk_permutations,
    remove_vms,
)  # flake8: noqa
import rhevmtests.storage.helpers as storage_helpers


@pytest.fixture()
def add_disks_permutation(request, storage, add_disk_permutations):
    """
    Add disks to remove list for finalizer
    """
    self = request.node.cls

    self.disks_to_remove = self.disk_names


@pytest.fixture()
def create_vms_for_test(request, storage, remove_vms):
    """
    Create VMs for test and initialize parameters
    """
    self = request.node.cls

    self.vm_names = list()
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage
        )[0]

    for idx in xrange(2):
        vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = vm_name
        testflow.setup("Creating VM %s", vm_name)
        assert storage_helpers.create_vm_or_clone(**vm_args), (
            "Failed to create VM %s" % vm_name
        )
        self.vm_names.append(vm_name)
