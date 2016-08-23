import pytest
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
)
from art.unittest_lib import testflow

from rhevmtests.storage import config
from rhevmtests.storage import helpers as storage_helpers


@pytest.fixture()
def add_disks(request, storage):
    """
    Add self.disk_count number of disks and attach them to the VM
    """
    self = request.node.cls

    self.disks_names = []
    testflow.setup("Creating and attaching %s disks", self.disk_count)
    for _ in range(self.disk_count):
        disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        assert ll_disks.addDisk(
            True, alias=disk_name, provisioned_size=config.GB,
            storagedomain=self.storage_domain, format=config.COW_DISK,
            sparse=True,
        ), "Unable to create disk %s" % disk_name
        self.disks_names.append(disk_name)
    assert ll_disks.wait_for_disks_status(self.disks_names), (
        "Failed to wait for disks %s status to be OK" % self.disks_names
    )
    assert storage_helpers.prepare_disks_for_vm(
        self.vm_name, self.disks_names
    ), "Failure to prepare disks %s for VM %s" % (
        self.disks_names, self.vm_name
    )


@pytest.fixture()
def initialize_test_variables(request, storage):
    """
    Get the boot disk and the vm executor
    """
    self = request.node.cls

    self.boot_disk = ll_vms.get_vm_bootable_disk(self.vm_name)
    self.vm_executor = storage_helpers.get_vm_executor(self.vm_name)
