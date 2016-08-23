import pytest
from rhevmtests.storage import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    jobs as ll_jobs,
)
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import add_disk_permutations  # flake8: noqa


@pytest.fixture()
def add_disks_permutation(request, storage, add_disk_permutations):
    """
    Add disks to remove list for finalizer
    """
    self = request.node.cls

    self.disks_to_remove = self.disk_names


@pytest.fixture()
def create_second_vm(request, storage):
    """
    Add a second VM
    """
    self = request.node.cls

    def finalizer():
        """
        Remove the VM
        """
        testflow.teardown("Remove VM %s", self.vm_name_2)
        assert ll_vms.safely_remove_vms([self.vm_name_2]), (
            "Failed to power off and remove VM %s" % self.vm_name_2
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])

    request.addfinalizer(finalizer)
    self.vm_name_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.vm_name_2
    vm_args['deep_copy'] = False
    testflow.setup("Creating VM %s", self.vm_name_2)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name_2
    )


@pytest.fixture()
def poweroff_vms(request, storage):
    """
    Power off VMs
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Power off VMs %s", self.vms_to_poweroff)
        assert ll_vms.stop_vms_safely(self.vms_to_poweroff), (
            "Failed to power off VMs %s" % self.vms_to_poweroff
        )
    request.addfinalizer(finalizer)

    self.vms_to_poweroff = getattr(self, 'vms_to_poweroff', list())
