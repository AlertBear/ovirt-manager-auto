import pytest
import config
import rhevmtests.storage.helpers as helpers
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)

VM_NAMES = config.VM_NAMES


@pytest.fixture(scope='class')
def initialize_vm(request, storage):
    """
    Initialize VM name
    """
    self = request.node.cls

    if not hasattr(self, 'vm_name'):
        self.vm_name = VM_NAMES[self.storage]


@pytest.fixture(scope='class')
def create_server_vm_with_snapshot(request, storage):
    """
    Create server VM with snapshot
    """
    self = request.node.cls

    helpers.create_vm_or_clone(
        True, self.vm_server, diskInterface=config.VIRTIO_SCSI,
        type=config.VM_TYPE_SERVER, installation=False
    )
    self.vm_names.append(self.vm_server)
    assert ll_vms.addSnapshot(True, self.vm_server, self.snapshot_server), (
        "Failed to create snapshot of VM %s" % self.vm_server
    )


@pytest.fixture(scope='class')
def remove_additional_nic(request, storage):
    """
    Remove nic
    """
    self = request.node.cls

    def finalizer():
        ll_vms.stop_vms_safely([self.vm_name])
        assert ll_vms.removeNic(True, self.vm_name, "nic2")
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def remove_additional_snapshot(request, storage):
    """
    Remove snapshot
    """
    self = request.node.cls

    def finalizer():
        ll_vms.stop_vms_safely([self.vm_name])
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_to_remove
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_cloned_vm(request, storage):
    """
    Remove cloned VM
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Remove cloned VM %s", self.cloned_vm)
        assert ll_vms.safely_remove_vms([self.cloned_vm]), (
            "Failed to remove cloned VM %s" % self.cloned_vm
        )
    request.addfinalizer(finalizer)
    if not hasattr(self, 'cloned_vm'):
        self.cloned_vm = helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
