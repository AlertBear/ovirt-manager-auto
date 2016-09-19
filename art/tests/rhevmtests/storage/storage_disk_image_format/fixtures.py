import config
import logging
import pytest
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    storagedomains as ll_sds,
    templates as ll_templates,
    vms as ll_vms,
)
from art.unittest_lib import testflow
from rhevmtests.storage.fixtures import (
    remove_vms
)  # flake8: noqa

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def initialize_params(request):
    """
    Initialize disk parameters
    """
    self = request.node.cls

    if not hasattr(self, 'disk_keywords'):
        self.disk_keywords = config.DISK_KWARGS.copy()
    if not hasattr(self, 'template_name'):
        self.template_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_TEMPLATE
        )


@pytest.fixture()
def create_test_vms(request, remove_vms):
    """
    Create one vm with thin provisioned disk and other one with
    preallocated disk
    """
    self = request.node.cls

    self.vm_thin = "vm_thin_disk_image_" + self.polarion_test_id
    self.vm_prealloc = "vm_prealloc_disk_image_" + self.polarion_test_id
    self.vm_names = [self.vm_thin, self.vm_prealloc]
    # Define the disk objects' retriever function
    self.retrieve_disk_obj = lambda x: ll_vms.getVmDisks(x)

    vm_thin_args = config.create_vm_args.copy()
    vm_prealloc_args = config.create_vm_args.copy()
    self.default_disks = {
        self.vm_thin: True,
        self.vm_prealloc: False,
    }
    thin_keywords = {
        "vmName": self.vm_thin,
        "volumeFormat": config.COW_DISK,
        "volumeType": True,  # sparse
    }
    self.disk_keywords = config.DISK_KWARGS.copy()
    self.disk_keywords['storageDomainName'] = self.storage_domain
    vm_thin_args.update(thin_keywords)
    vm_thin_args.update(self.disk_keywords)

    prealloc_keywords = {
        "vmName": self.vm_prealloc,
        "volumeFormat": config.RAW_DISK,
        "volumeType": False,  # preallocated
    }
    vm_prealloc_args.update(prealloc_keywords)
    vm_prealloc_args.update(self.disk_keywords)

    assert storage_helpers.create_vm_or_clone(**vm_thin_args)
    assert storage_helpers.create_vm_or_clone(**vm_prealloc_args)

    self.disk_thin = ll_vms.getVmDisks(self.vm_thin)[0].get_id()
    self.disk_prealloc = ll_vms.getVmDisks(self.vm_prealloc)[0].get_id()
    self.snapshot_desc = "snapshot_disk_image_format"


@pytest.fixture(scope='class')
def remove_vm_setup(request):
    """
    Remove VM
    """
    self = request.node.cls

    testflow.setup("Remove VM %s", self.vm_name)
    assert ll_vms.safely_remove_vms([self.vm_name]), (
        "Failed to power off and remove VM %s" % self.vm_name
    )
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])


@pytest.fixture()
def remove_test_templates(request):
    """
    Remove VM
    """
    self = request.node.cls

    def finalizer():
        for template in [self.template_thin, self.template_preallocated]:
            if ll_templates.check_template_existence(template):
                testflow.teardown("Removing template %s", template)
                assert ll_templates.removeTemplate(True, template), (
                    "Failed to remove template '%s'", template
                )
    request.addfinalizer(finalizer)
    self.template_thin = self.template_thin % self.polarion_test_id
    self.template_preallocated = (
        self.template_preallocated % self.polarion_test_id
    )
