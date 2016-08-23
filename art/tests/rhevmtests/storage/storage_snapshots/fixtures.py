import logging
import pytest
import helpers
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    templates as ll_templates,
)
from art.rhevm_api.tests_lib.high_level import (
    vms as hl_vms,
)
from art.rhevm_api.utils import test_utils
from rhevmtests.storage import config
from rhevmtests.storage import helpers as storage_helpers


logger = logging.getLogger(__name__)


@pytest.fixture()
def create_memory_snapsot_running_process(request, storage):
    """
    Start VM, run process on VM and create RAM snapshot
    """
    self = request.node.cls

    self.memory_snapshot = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SNAPSHOT
    )
    testflow.step("Starting cat process on VM %s", self.vm_name)
    pid = helpers.start_cat_process_on_vm(
        self.vm_name, self.cmdlines[0]
    )
    assert pid, (
        "Failed to start cat process on VM %s" % self.vm_name
    )
    logger.info("PID for first cat process is: %s", pid)
    self.pids = [pid]

    if self.persist_network:
        vm_ip = hl_vms.get_vm_ip(self.vm_name, start_vm=False)
        logger.info("Setting persistent network on VM %s", self.vm_name)
        assert test_utils.setPersistentNetwork(vm_ip, config.VM_PASSWORD), (
            "Failed to seal VM %s" % self.vm_name
        )

    testflow.step(
        "Creating snapshot %s with RAM state", self.memory_snapshot
    )
    assert ll_vms.addSnapshot(
        True, self.vm_name, self.memory_snapshot, persist_memory=True
    ), (
        "Unable to create RAM snapshot %s on VM %s"
        % (self.memory_snapshot, self.vm_name)
    )
    logger.info("Wait for snapshot %s to be created", self.memory_snapshot)
    ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
    logger.info("Snapshot created successfully")


@pytest.fixture()
def initialize_prepare_environment(request, storage):
    """
    Set attributes for test
    """

    self = request.node.cls

    self.mounted_paths = []
    self.snapshot_description = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SNAPSHOT
    )


@pytest.fixture()
def add_disks_different_sd(request, storage):
    """
    Create self.disks_count number of disks on the second storage domain
    """
    self = request.node.cls

    for index in range(self.disks_count):
        alias = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
        testflow.step("Adding disk %s to VM %s", alias, self.vm_name)
        assert ll_vms.addDisk(
            True, vm=self.vm_name, provisioned_size=3 * config.GB,
            wait=True, storagedomain=self.storage_domains[1],
            type=config.DISK_TYPE_DATA,
            interface=config.VIRTIO, format=config.COW_DISK,
            sparse='true', alias=alias
        )


@pytest.fixture(scope='class')
def add_two_vms_from_template(request, storage):
    """
    Create two vms, one thin and the other cloned, from a template
    """

    self = request.node.cls

    self.vm_names = list()
    self.vm_thin = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    testflow.step("Creating thin provisioned VM %s", self.vm_thin)
    assert ll_vms.addVm(
        True, name=self.vm_thin, description='',
        cluster=config.CLUSTER_NAME,
        storagedomain=self.storage_domain, template=self.template_name
    ), (
        "Failed to create new VM %s from template %s as thin copy" %
        (self.vm_thin, self.template_name)
    )
    self.vm_names.append(self.vm_thin)
    ll_templates.waitForTemplatesStates(self.template_name)
    self.vm_clone = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    testflow.step("Creating cloned VM %s", self.vm_clone)
    assert ll_vms.addVm(
        True, name=self.vm_clone, description='',
        cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain,
        template=self.template_name, disk_clone='True'
    ), (
        "Failed to create new VM %s from template %s as deep copy" %
        (self.vm_clone, self.template_name)
    )
    self.vm_names.append(self.vm_clone)
    if self.live_snapshot:
        ll_vms.start_vms(self.vm_names, config.MAX_WORKERS)


@pytest.fixture()
def pids_list(request, storage):
    self = request.cls
    self.pids = []
