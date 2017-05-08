"""
Fixtures for reduce_luns_from_storage_domain module
"""
import pytest
import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    disks as ll_disks,
    vms as ll_vms
)
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools
)
from rhevmtests.fixtures import (
    create_lun_on_storage_server, remove_lun_from_storage_server
)


@pytest.fixture(scope='class')
def set_disk_params(request):
    """
    Set disk size
    """
    self = request.node.cls
    size_diff = getattr(self, 'size_diff', 5)
    self.disk_size = ll_sd.get_free_space(
        self.new_storage_domain
    ) - size_diff * config.GB
    assert self.disk_size, "Failed to get storage domain %s size" % (
        self.new_storage_domain
    )
    self.add_disk_params = {'sparse': False, 'format': config.RAW_DISK}


@pytest.fixture(scope='class')
def init_domain_disk_param(request):
    """
    Initialize VM parameters
    """
    self = request.node.cls

    # In some cases we would like the disk to be created on an existing SD (for
    # example, in disk migration tests)
    if hasattr(self, 'existing_domain'):
        existing_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.storage_domain = existing_domains[0] if existing_domains[0] != (
            self.new_storage_domain
        ) else existing_domains[1]
    else:
        self.storage_domain = self.new_storage_domain


@pytest.fixture(scope='class')
def attach_disk_to_second_vm(request):
    """
    Attach shared disk to second VM
    """
    self = request.node.cls

    attach_kwargs = config.attach_disk_params.copy()
    testflow.setup(
        "Attaching shared disk %s to VM %s", self.disk_name, self.vm_name_2
    )
    assert ll_disks.attachDisk(
        True, alias=self.disk_name, vm_name=self.vm_name_2, **attach_kwargs
    ), ("Failed to attach disk %s to VM %s" % (self.disk_name, self.vm_name_2))
    ll_disks.wait_for_disks_status([self.disk_name])


@pytest.fixture(scope='class')
def set_shared_disk_params(request):
    """
    Set shared disk params
    """
    self = request.node.cls

    self.storage_domain = self.new_storage_domain

    # shared disk cannot be sparse
    self.add_disk_params = {
        'shareable': True, 'sparse': False, 'format': config.RAW_DISK
    }


@pytest.fixture(scope='class')
def poweroff_vms(request):
    """
    Power off VMs
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Power off VMs %s", [self.vm_name, self.vm_name_2])
        assert ll_vms.stop_vms_safely([self.vm_name, self.vm_name_2]), (
            "Failed to power off VMs %s" % [self.vm_name, self.vm_name_2]
        )
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def create_second_lun(request):
    """
    Create second LUN on storage server
    """
    create_lun_on_storage_server(request)
    append_to_luns_to_resize(request)


@pytest.fixture(scope='class')
def remove_second_lun(request):
    """
    Remove second LUN from storage server
    """
    remove_lun_from_storage_server(request)


@pytest.fixture(scope='class')
def append_to_luns_to_resize(request):
    """
    Initialize LUNs to extend list
    """
    self = request.node.cls

    def finalizer():
        del config.LUNS_TO_RESIZE[:]
        del config.LUNS_IDENTIFIERS[:]
    request.addfinalizer(finalizer)
    config.LUNS_TO_RESIZE.append(self.new_lun_id)
    config.LUNS_IDENTIFIERS.append(self.new_lun_identifier)


@pytest.fixture(scope='class')
def remove_vms_pool(request):
    """
    Detach and remove VMs pool
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing VMs pool: %s", self.pool_name)
        assert hl_vmpools.remove_whole_vm_pool(vmpool=self.pool_name), (
            "Failed to remove VMs pool %s" % self.vm_pool
        )
    request.addfinalizer(finalizer)
