import config
import pytest
import itertools
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    jobs as ll_jobs,
    templates as ll_templates,
    vms as ll_vms,
)
from art.unittest_lib import testflow


@pytest.fixture(scope='class')
def initialize_params(request, storage):
    """
    Initialize disk parameters
    """
    self = request.node.cls

    if not hasattr(self, 'disk_keywords'):
        self.disk_keywords = config.DISK_KWARGS.copy()


@pytest.fixture(scope='class')
def initialize_template_name(request, storage):
    """
    Initialize template_name parameter
    """
    self = request.node.cls

    self.template_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture()
def create_test_vms(request, storage, remove_vms):
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
def remove_vm_setup(request, storage):
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
def remove_test_templates(request, storage):
    """
    Remove VM
    """
    self = request.node.cls

    def finalizer():
        for template in [self.template_thin, self.template_preallocated]:
            if ll_templates.check_template_existence(template):
                testflow.teardown("Removing template %s", template)
                assert ll_templates.remove_template(True, template), (
                    "Failed to remove template '%s'", template
                )
    request.addfinalizer(finalizer)
    self.template_thin = self.template_thin_name % self.polarion_test_id
    self.template_preallocated = (
        self.template_preallocated_name % self.polarion_test_id
    )


@pytest.fixture(scope='class')
def create_second_vm(request, storage):
    """
    Create VM and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Remove VM %s", self.vm_name_2)
        assert ll_vms.safely_remove_vms([self.vm_name_2]), (
            "Failed to power off and remove VM %s" % self.vm_name_2
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
    request.addfinalizer(finalizer)

    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.vm_name_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.vm_name_2
    testflow.setup("Creating VM %s", self.vm_name_2)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name_2
    )


@pytest.fixture(scope='class')
def create_disks_to_vm(request, storage):
    """
    Create 4 disks and attach them to the VM
    """
    self = request.node.cls

    self.disk_aliases = list()

    for disk in xrange(4):
        disk_args = config.disk_args.copy()
        disk_args['interface'] = config.INTERFACE_VIRTIO
        disk_args['alias'] = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        disk_args['wait'] = False
        disk_args['storagedomain'] = self.storage_domain
        testflow.setup(
            "Add disk %s to VM %s", disk_args['alias'], self.vm_name
        )
        assert ll_vms.addDisk(True, vm=self.vm_name, **disk_args), (
            "Failed to create disk %s" % disk_args['alias']
        )
        self.disk_aliases.append(disk_args['alias'])

    assert ll_disks.wait_for_disks_status(self.disk_aliases), (
        "Failed to wait for disk %s status OK" % self.disk_aliases
    )


@pytest.fixture(scope='class')
def create_disks_to_vm_by_interface(request, storage):
    """
    Create a VM and as many disks as interfaces to test and attach them
    to the VM
    """
    self = request.node.cls

    lun_disks = getattr(self, 'lun_disks', False)

    self.permutations = (
        filter(
            lambda w: w[0] != w[1],
            itertools.permutations(config.TEST_INTERFACES, 2)
        )
    )
    for disk_interface, index in zip(config.TEST_INTERFACES, xrange(2)):
        disk_args = config.disk_args.copy()
        disk_args['interface'] = disk_interface
        disk_args['alias'] = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        disk_args['storagedomain'] = self.storage_domain
        testflow.setup("Add disk %s ", disk_args['alias'])
        if lun_disks:
            del disk_args['storagedomain']
            disk_args['type_'] = config.STORAGE_TYPE_ISCSI
            disk_args['lun_address'] = (
                config.ISCSI_DOMAINS_KWARGS[index]['lun_address']
            )
            disk_args['lun_target'] = (
                config.ISCSI_DOMAINS_KWARGS[index]['lun_target']
            )
            disk_args['lun_id'] = config.ISCSI_DOMAINS_KWARGS[index]['lun']
            assert ll_disks.addDisk(True, **disk_args), (
                "Unable to create disk %s" % disk_args['alias']
            )
            assert ll_disks.attachDisk(
                True, alias=disk_args['alias'], vm_name=self.vm_name,
                active=True
            ), "Unable to attach disk %s to vm %s" % (
                disk_args['alias'], self.vm_name
            )
        else:
            testflow.setup("Add disk %s ", disk_args['alias'])
            assert ll_vms.addDisk(True, vm=self.vm_name, **disk_args), (
                "Unable to create disk %s" % disk_args['alias']
            )
            assert ll_disks.wait_for_disks_status(self.disk_aliases), (
                "Failed to wait for disk %s status OK" % self.disk_aliases
            )
        self.disk_aliases.append(disk_args['alias'])
