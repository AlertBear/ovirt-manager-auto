import pytest
import logging

import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
    disks as ll_disks,
    jobs as ll_jobs,
)
import rhevmtests.storage.helpers as storage_helpers
from art.unittest_lib.common import testflow
logger = logging.getLogger(__name__)
STATELESS_SNAPSHOT_DESCRIPTION = 'stateless snapshot'


@pytest.fixture(scope='class')
def create_second_vm(request, storage):
    """
    Create VM and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        if not ll_vms.safely_remove_vms([self.second_vm_name]):
            logger.error(
                "Failed to power off and remove VM %s",
                self.second_vm_name
            )
            self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.second_vm_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    )
    if not hasattr(self, 'installation'):
        self.installation = True
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.second_vm_name
    vm_args['installation'] = self.installation
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException(
            "Failed to create VM %s" % self.second_vm_name
        )


@pytest.fixture()
def poweroff_vm_and_wait_for_stateless_to_remove(request, storage):
    """
    Power off VM and wait for stateless snapshot to be removed
    """
    self = request.node.cls

    def finalizer():
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off VM %s", self.vm_name
        )
        ll_vms.wait_for_snapshot_gone(
            self.vm_name, STATELESS_SNAPSHOT_DESCRIPTION,
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_direct_lun_params(request, storage):
    """
    Initialize direct lun parameters
    """
    self = request.node.cls

    self.disk_alias = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DIRECT_LUN
    )
    self.lun_kwargs = config.BASE_KWARGS.copy()
    self.lun_kwargs["alias"] = self.disk_alias
    self.template_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture(scope='class')
def delete_direct_lun_disk(request, storage):
    """
    Removes direct lun disk
    Created due to direct lun disk status N/A unlike other type disks
    """
    self = request.node.cls

    def finalizer():
        for direct_lun in self.disks_to_remove:
            if ll_disks.checkDiskExists(True, direct_lun):
                testflow.teardown("Deleting disk %s", direct_lun)
                assert ll_disks.deleteDisk(True, direct_lun), (
                    "Failed to delete disk %s" % direct_lun
                )
                ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
    request.addfinalizer(finalizer)
    self.disks_to_remove = list()


@pytest.fixture(scope='class')
def check_initial_storage_domain_params(request, storage):
    """
    Check initial storage domain parameters
    """
    self = request.node.cls

    self.domains = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )

    logger.info(
        'Found data domains of type %s: %s', self.storage, self.domains
    )

    # by default create both disks on the same domain
    self.disk_domains = [self.domains[0], self.domains[0]]

    # set up parameters used by test
    for domain in self.domains:
        self.current_allocated_size[domain] = (
            ll_sd.get_allocated_size(domain)
        )
        self.current_total_size[domain] = (
            ll_sd.get_total_size(domain, config.DATA_CENTER_NAME)
        )
        self.current_used_size[domain] = (
            ll_sd.get_used_size(domain)
        )

        logger.info(
            "Allocated size for %s is %d Total size is %d",
            domain, self.current_allocated_size[domain],
            self.current_total_size[domain]
        )
        self.expected_total_size[domain] = self.current_total_size[domain]
        self.expected_allocated_size[domain] = self.current_allocated_size[
            domain
        ]


@pytest.fixture(scope='class')
def create_disks_fixture(request, storage):
    """
    Creates disks of given types and sizes and updates expected details
    """

    self = request.node.cls
    self.create_disks()


@pytest.fixture(scope='class')
def lun_size_calc(request, storage):
    """
    Calculate lun size and free space
    """

    self = request.node.cls

    self.lun_size, self.lun_free_space = (
        storage_helpers.get_lun_storage_info(config.EXTEND_LUN[0])
    )
    logger.info(
        "LUN size is '%s' and its free space is '%s'",
        str(self.lun_size), str(self.lun_free_space)
    )


@pytest.fixture(scope='class')
def create_2_vms_pre_disk_thin_disk(request, storage):
    """
    Create 2 vms, one with preallocated and one with thin provision disks
    """

    self = request.node.cls

    self.disk_map = zip(
        (True, False), self.disk_sizes,
        (config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW)
    )
    self.vm_names = []
    for sparse, disk_size, disk_format in self.disk_map:
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        self.vm_names.append(self.vm_name)
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.domains[0]
        vm_args['installation'] = False
        vm_args['vmName'] = self.vm_name
        vm_args['volumeType'] = sparse
        vm_args['provisioned_size'] = config.VM_DISK_SIZE
        vm_args['volumeFormat'] = disk_format

        assert ll_vms.createVm(**vm_args), 'unable to create vm %s' % (
            self.vm_name
        )
        self.expected_allocated_size[self.domains[0]] += config.VM_DISK_SIZE
        self.templates_names.append(
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
            )
        )


@pytest.fixture(scope='class')
def initialize_disk_name(request, storage):
    """
    Initialize disk name
    """

    self = request.node.cls

    self.disk_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
