import pytest
import rhevmtests.helpers as rhevm_helpers
import rhevmtests.storage.helpers as storage_helpers
import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
)
from rhevmtests.storage.fixtures import (
    attach_disk, start_vm, create_vm

)

from rhevmtests.storage.fixtures import remove_vm  # noqa F401


@pytest.fixture(scope='class')
def get_second_storage_domain(request):
    """
    Get storage domains by given type
    """
    self = request.node.cls

    testflow.setup("Getting second storage domain information")
    self.second_storage_domain = (
        ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    )
    assert self.second_storage_domain, "Failed to get second storage domain"


@pytest.fixture(scope='function')
def create_vm_for_test(request):
    """
    Create a VM
    """

    def finalizer():
        """
        Remove the VM
        """
        remove_vm(request)
    request.addfinalizer(finalizer)
    create_vm(request, None)


@pytest.fixture(scope='function')
def start_vm_for_test(request):
    """
    Start a VM
    """
    start_vm(request)


@pytest.fixture(scope='function')
def add_disks(request):
    """
    Create thin provision and preallocated disks
    """
    self = request.node.cls

    self.disk_names = []
    for key, val in sorted(config.DISK_ALLOCATIONS.items()):
        disk_params = config.disk_args.copy()
        disk_name = storage_helpers.create_unique_object_name(
            '%s' % val, config.OBJECT_TYPE_DISK
        )
        testflow.setup(
            'Creating a %s %s GB disk on domain %s',
            str(val), config.DISK_SIZE / config.GB, self.new_storage_domain
        )
        disk_params['storagedomain'] = self.new_storage_domain
        disk_params['sparse'] = key
        disk_params['provisioned_size'] = config.DISK_SIZE
        disk_params['alias'] = disk_name
        disk_params['format'] = config.DISK_FORMAT_RAW if not key else (
            config.DISK_FORMAT_COW
        )
        assert ll_disks.addDisk(True, **disk_params), (
            "Failed to create disk %s" % disk_name
        )
        self.disk_names.append(disk_name)
    testflow.setup('Waiting for disks to be OK')
    assert ll_disks.wait_for_disks_status(self.disk_names), (
        "Disks %s failed to reach status OK" % self.disk_names
    )


@pytest.fixture(scope='function')
def attach_disks(request):
    """
    Attach disks to VM
    """
    self = request.node.cls

    for disk in self.disk_names:
        self.disk_name = disk
        attach_disk(request)


@pytest.fixture(scope='class')
def init_storage_manager(request):
    """
    Initialize storage manager instance
    """

    self = request.node.cls

    manager = config.ISCSI_STORAGE_MANAGER[0] if self.storage == (
        config.STORAGE_TYPE_ISCSI
    ) else config.FCP_STORAGE_MANAGER[0]

    # Initialize the storage manager with iscsi as the storage type since
    # storage_api has only iscsi manager which is good also for fc
    self.storage_manager = (
        rhevm_helpers.get_storage_manager(
            config.STORAGE_TYPE_ISCSI, manager, config.STORAGE_CONFIG
        )
    )
    self.storage_server = config.STORAGE_SERVER[manager]
    assert self.storage_manager, (
        "Failed to retrieve storage server" % self.new_storage_domain
    )