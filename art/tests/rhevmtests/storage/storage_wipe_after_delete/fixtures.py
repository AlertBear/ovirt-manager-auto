import pytest
import config

from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms,
)


@pytest.fixture()
def update_storage_domain_wipe_after_delete(request, storage):
    """
    Enable wipe_after_delete for storage domain
    """
    self = request.node.cls

    assert ll_sd.updateStorageDomain(
        True, self.storage_domain, wipe_after_delete=True
    ), "Error editing storage domain %s" % self.storage_domain


@pytest.fixture()
def add_disk_start_vm(request, storage):
    """
    Add disk with wipe_after_delete and start the vm
    """
    self = request.node.cls

    assert ll_vms.addDisk(
        True, self.vm_name, config.DISK_SIZE,
        storagedomain=self.storage_domain, sparse=True,
        wipe_after_delete=True, interface=config.VIRTIO,
        alias=self.disk_name
    ), "Error adding disk to vm %s" % self.vm_name
    ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
    ll_vms.waitForVMState(self.vm_name)
