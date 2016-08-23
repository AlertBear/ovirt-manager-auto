import config
import logging
import pytest
import rhevmtests.storage.helpers as storage_helpers
import helpers
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    templates as ll_templates,
    vms as ll_vms,
)

logger = logging.getLogger(__name__)

REMOVE_TEMPLATE_TIMEOUT = 300


@pytest.fixture(scope='class')
def initialize_vm(request, storage):
    """
    Initialize VM name
    """
    self = request.node.cls

    if not hasattr(self, 'vm_name'):
        self.vm_name = config.VM_NAMES[storage]


@pytest.fixture(scope='class')
def create_disks(request, storage):
    """
    Create disks
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Removing disks: %s", ', '.join(config.FLOATING_DISKS)
        )
        helpers.clean_all_copied_disks(config.FLOATING_DISKS)

    request.addfinalizer(finalizer)
    config.FLOATING_DISKS = list()
    testflow.setup("Creating disks for test")
    disks = (
        storage_helpers.start_creating_disks_for_test(
            sd_name=self.storage_domain
        )
    )
    disk_names = [disk['disk_name'] for disk in disks]
    ll_disks.wait_for_disks_status(disk_names)
    for disk_alias in disk_names:
        config.FLOATING_DISKS.append(
            ll_disks.get_disk_obj(disk_alias).get_id()
        )
    config.DISKS_BEFORE_COPY = ll_disks.get_non_ovf_disks()


@pytest.fixture()
def remove_disks(request, storage):
    """
    Remove disks
    """
    self = request.node.cls

    def finalizer():
        helpers.clean_all_copied_disks(self.new_disks)

    request.addfinalizer(finalizer)
    self.new_disks = []


@pytest.fixture()
def remove_vm(request, storage):
    """
    Remove VMs
    """
    def finalizer():
        testflow.teardown("Removing VM %s", config.VMS_TO_REMOVE)
        ll_vms.safely_remove_vms(config.VMS_TO_REMOVE)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
    request.addfinalizer(finalizer)
    config.VMS_TO_REMOVE = list()


@pytest.fixture()
def create_test_vm(request, storage, remove_vm):
    """
    Create new VM
    """
    self = request.node.cls

    self.test_vm_name = storage_helpers.create_unique_object_name(
        "test_copy_disk_%s" % storage, config.OBJECT_TYPE_VM
    )
    testflow.setup("Creating new VM %s", self.test_vm_name)
    ll_vms.createVm(
        True, self.test_vm_name, self.test_vm_name,
        cluster=config.CLUSTER_NAME, nic=config.NIC_NAME[0],
        user=config.VM_USER, password=config.VM_PASSWORD,
        network=config.MGMT_BRIDGE, useAgent=True,
        display_type=config.DISPLAY_TYPE,
        type=config.VM_TYPE_DESKTOP,
    )
    config.VMS_TO_REMOVE.append(self.test_vm_name)


@pytest.fixture(scope='class')
def remove_template(request, storage):
    """
    Remove template
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing  template %s", self.template_name)
        assert ll_templates.remove_template(
            True, self.template_name, timeout=REMOVE_TEMPLATE_TIMEOUT
        ), "Failed to remove template %s" % self.template_name

    request.addfinalizer(finalizer)
