import config
import pytest
import helpers
from art.unittest_lib.common import testflow
import rhevmtests.storage.helpers as storage_helpers

from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    hosts as ll_hosts,
    jobs as ll_jobs,
    vms as ll_vms
)

from rhevmtests.storage.fixtures import (
    create_vm, remove_vm, add_disk, delete_disks
)


@pytest.fixture(scope='class')
def init_storage_domains(request, storage):
    """
    Initialize specific storage domains
    """
    self = request.node.cls

    for sd in self.storage_domains.keys():
        self.storage_domains[sd] = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, sd
        )[0]


@pytest.fixture(scope='class')
def create_disks_on_selected_storage_domains(request, storage):
    """
    Create disks on specific storage domains
    """
    self = request.node.cls

    def finalizer():
        self.disks_to_remove = self.disks
        delete_disks(request, storage)

    request.addfinalizer(finalizer)

    disk_params = config.disk_args.copy()
    for sd in self.domains_to_create_disks_on:
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, sd
        )[0]
        disk_params['storagedomain'] = self.storage_domain
        add_disk(request, storage)
        self.disks.append(self.disk_name)


@pytest.fixture(scope='class')
def add_disk_to_vm_on_iscsi(request, storage):
    """
    Add disk to VM on ISCSI storage domain
    """
    self = request.node.cls

    vm_disk_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
    testflow.setup(
        "Adding disk %s to VM %s on storage domain %s", vm_disk_2,
        self.vm_name, self.storage_domains[config.ISCSI]
    )
    helpers.add_disk_to_sd(
        vm_disk_2, self.storage_domains[config.ISCSI],
        attach_to_vm=self.vm_name
    )


@pytest.fixture(scope='class')
def init_parameters(request, storage):
    """
    Initializes host ip, disk name, master domain, non master,
    storage domain ip
    """
    self = request.node.cls

    self.host_ip = ll_hosts.get_host_ip(ll_hosts.get_spm_host(config.HOSTS))
    self.disk_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
    found, master_domain = ll_sd.findMasterStorageDomain(
        True, config.DATA_CENTER_NAME,
    )
    assert found, (
        "Couldn't find master domain in data center %s"
        % config.DATA_CENTER_NAME
    )
    self.master_domain = master_domain['masterDomain']
    found, non_master = ll_sd.findNonMasterStorageDomains(
        True, config.DATA_CENTER_NAME,
    )
    assert found, (
        "Couldn't find non master domain in data center %s"
        % config.DATA_CENTER_NAME
    )
    self.non_master = non_master['nonMasterDomains']
    rc, master_address = ll_sd.getDomainAddress(True, self.master_domain)
    assert rc, (
        "Couldn't get storage domain address for storage domain %s"
        % self.master_domain
    )
    self.storage_domain_ip = master_address


@pytest.fixture(scope='class')
def create_vm_on_nfs(request, storage):
    """
    Create a VM on NFS storage
    """

    self = request.node.cls

    setattr(self, 'storage_domain', self.storage_domains[config.NFS])
    create_vm(request, storage, remove_vm)
    self.vm_names.append(self.vm_name)


@pytest.fixture()
def remove_cloned_vm(request, storage):
    """
    Remove cloned VM
    """
    self = request.node.cls

    def finalizer():
        """
        Remove cloned vm
        """
        testflow.teardown("Remove VM %s", self.cloned_vm)
        assert ll_vms.safely_remove_vms([self.cloned_vm]), (
            "Failed to power off and remove VM %s" % self.cloned_vm
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])

    request.addfinalizer(finalizer)
