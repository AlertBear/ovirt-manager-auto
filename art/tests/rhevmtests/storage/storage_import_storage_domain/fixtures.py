import pytest
import logging
import config
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
    datacenters as ll_dc,
)
from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import attach_disk, create_vm
from rhevmtests.storage.fixtures import remove_vm  # flake8: noqa

logger = logging.getLogger(__name__)

ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIX = config.STORAGE_TYPE_POSIX
CEPH = config.STORAGE_TYPE_CEPH


@pytest.fixture(scope='class')
def initialize_params(request, storage):
    """
    Clean the environment
    """
    self = request.node.cls

    self.vm_name = getattr(self, 'vm_name', None)
    if not hasattr(self, 'master_domain'):
        status, master_domain = ll_sd.findMasterStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME
        )
        assert status, "Unable to find master storage domain"
    self.host = ll_hosts.get_spm_host(config.HOSTS)
    self.host_ip = ll_hosts.get_host_ip(config.HOSTS[0])
    self.non_master = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_SD
    )
    # initialize for create_vm fixture
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = self.non_master
        self.deep_copy = True


@pytest.fixture()
def deactivate_detach_and_remove_domain_fin(request, storage):

    self = request.node.cls

    def finalizer():
        """
        Deactivate detach and remove storage domain
        """
        domain_to_remove = config.DOMAIN_TO_DETACH_AND_REMOVE
        dc_name = (
            config.DATA_CENTER_NAME if config.DOMAIN_MOVED else
            config.DC_TO_REMOVE_FROM
        )
        if hasattr(self, 'vm_name') and ll_vms.does_vm_exist(self.vm_name):
            testflow.teardown(
                "Remove VM %s", self.vm_name
            )
            assert ll_vms.safely_remove_vms([self.vm_name]), (
                "Failed to remove vm %s", self.vm_name
            )
        testflow.teardown(
            "Detach and remove storage domain %s", domain_to_remove
        )
        spm_host = ll_hosts.get_spm_host(config.HOSTS)
        assert hl_sd.remove_storage_domain(
            domain_to_remove, dc_name, spm_host, engine=config.ENGINE,
            format_disk=True
        ), "Failed to detach and remove storage-domain %s" % domain_to_remove
    request.addfinalizer(finalizer)


@pytest.fixture()
def add_non_master_storage_domain(request, storage):
    """
    Add new non master storage domain
    """
    self = request.node.cls

    self.index = getattr(self, 'index', 0)
    self.dc_name = getattr(self, 'dc_name', config.DATA_CENTER_NAME)
    testflow.setup(
        "Add storage domain %s to data-center %s",
        self.non_master, self.dc_name
    )
    storage_helpers.add_storage_domain(
        self.non_master, self.dc_name, self.index, self.storage
    )
    # initialize for deactivate_detach_and_remove_domain_fin fixture
    # and for remove_storage_domain_fin fixture
    config.DOMAIN_TO_DETACH_AND_REMOVE = self.non_master
    config.DOMAIN_TO_REMOVE = self.non_master
    # initialize for clean_dc fixture
    self.master_domain = self.non_master
    # inizialize for remove_storage_domain_setup fixture
    self.domain_to_remove = self.non_master


@pytest.fixture(scope='class')
def remove_storage_domain_fin(request, storage):

    self = request.node.cls

    def finalizer():
        """
        Remove storage domain
        """
        domain_to_remove = config.DOMAIN_TO_REMOVE
        destroy = getattr(self, 'destroy', False)
        testflow.teardown("Remove storage domain %s", domain_to_remove)
        assert ll_sd.removeStorageDomain(
            True, domain_to_remove, config.HOSTS[0], format='true',
            destroy=destroy
        ), "Failed to remove storage domain %s" % domain_to_remove
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def add_master_storage_domain_to_new_dc(request, storage):
    """
    Add new master storage domain
    """
    self = request.node.cls
    self.new_dc_name = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
    self.master_domain = getattr(
        self, 'master_domain', storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
    )
    testflow.setup(
        "Add storage domain %s to data-center %s",
        self.master_domain, self.new_dc_name
    )
    storage_helpers.add_storage_domain(
        self.master_domain, self.new_dc_name, 0, self.storage
    )
    # initialize for remove_storage_domain_fin fixture
    config.DOMAIN_TO_REMOVE = self.master_domain


@pytest.fixture(scope='class')
def add_non_master_storage_domain_to_new_dc(request, storage):
    """
    Add new non master storage domain
    """
    self = request.node.cls
    self.new_dc_name = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
    testflow.setup(
        "Add storage domain %s to data-center %s",
        self.non_master, self.dc_name
    )
    storage_helpers.add_storage_domain(
        self.non_master, self.new_dc_name, 1, self.storage
    )
    # initialization for secure_deactivate_and_detach_storage_domain
    self.dc_to_detach_from = self.new_dc_name
    # initialization for deactivate_detach_and_remove_domain_fin
    config.DOMAIN_TO_DETACH_AND_REMOVE = self.non_master
    config.DC_TO_REMOVE_FROM = self.new_dc_name


@pytest.fixture()
def secure_deactivate_and_detach_storage_domain(
    request, secure_deactivate_storage_domain, storage
):
    """
    Deactivate and detach storage-domain
    """
    self = request.node.cls

    testflow.setup(
        "Detach storage domain %s", self.domain_to_detach
    )
    assert hl_sd.detach_domain(
        self.dc_to_detach_from, self.domain_to_detach, config.ENGINE
    ), "Unable to detach %s" % self.domain_to_detach


@pytest.fixture()
def secure_deactivate_storage_domain(request, storage):
    """
    Deactivate storage-domain
    """
    self = request.node.cls

    self.domain_to_detach = getattr(
        self, 'domain_to_detach', self.non_master
    )
    self.dc_to_detach_from = getattr(
        self, 'dc_to_detach_from', config.DATA_CENTER_NAME
    )
    testflow.setup(
        "Deactivate storage domain %s", self.non_master
    )
    assert hl_sd.deactivate_domain(
        self.dc_to_detach_from, self.domain_to_detach, config.ENGINE
    ), "Failed to detach domain %s" % self.domain_to_detach


@pytest.fixture()
def create_gluster_or_posix_export_domain(
    request, storage, attach_export_domain
):
    """
    Create export domain and remove it
    """
    self = request.node.cls

    def finalizer():
        """
        Detach and remove the export domain
        """
        testflow.teardown(
            "Deactivate and remove storage domain %s", self.export_domain
        )
        assert hl_sd.remove_storage_domain(
            self.export_domain, config.DATA_CENTER_NAME, self.host,
            engine=config.ENGINE, format_disk=True
        ), "Failed to detach and remove storage-domain %s" % self.export_domain
    request.addfinalizer(finalizer)

    self.export_domain = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    self.host = ll_hosts.get_spm_host(config.HOSTS)
    if self.storage == POSIX:
        self.export_address = config.NFS_DOMAINS_KWARGS[1]['address']
        self.export_path = config.NFS_DOMAINS_KWARGS[1]['path']
        self.vfs_type = NFS
        self.nfs_version = 'v4.1'
        self.storage_type = POSIX

        assert hl_sd.addPosixfsDataDomain(
            self.host, self.export_domain, config.DATA_CENTER_NAME,
            self.export_address, self.export_path, vfs_type=self.vfs_type,
            sd_type=self.sd_type, nfs_version=self.nfs_version
        ), "Creating POSIX domain '%s' failed" % self.export_domain

    elif self.storage == GLUSTER:
        self.export_address = (
            config.GLUSTER_DOMAINS_KWARGS[1]['address']
        )
        self.export_path = config.GLUSTER_DOMAINS_KWARGS[1]['path']
        self.vfs_type = config.ENUMS['vfs_type_glusterfs']
        self.storage_type = GLUSTER

        assert hl_sd.addGlusterDomain(
            self.host, self.export_domain, config.DATA_CENTER_NAME,
            self.export_address, self.export_path,
            vfs_type=self.vfs_type, sd_type=self.sd_type
        ), "Creating GlusterFS domain '%s' failed" % self.export_domain
    test_utils.wait_for_tasks(
        config.ENGINE, config.DATA_CENTER_NAME
    )
    hl_sd.remove_storage_domain(
        self.export_domain, config.DATA_CENTER_NAME, self.host,
        engine=config.ENGINE
    )


@pytest.fixture()
def attach_export_domain(request, storage):
    """
    Attach export domain to the data-center
    """
    def finalizer():
        testflow.teardown(
            "Attach storage domain %s", config.EXPORT_DOMAIN_NAME
        )
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_template_setup(request, storage):
    """
    Remove template from the data-center
    """
    self = request.node.cls

    assert ll_templates.remove_template(True, self.template_name), (
        "Failed to remove template %s" % self.template_name
    )


@pytest.fixture()
def remove_storage_domain_setup(request, storage):
    """
    Remove storage domain from the data-center
    """
    self = request.node.cls

    domain_to_remove = getattr(
        self, 'domain_to_remove', ll_sd.get_master_storage_domain_name(
            datacenter_name=config.DATA_CENTER_NAME
        )
    )
    remove_param = getattr(self, 'remove_param', {'format', 'true'})

    spm_host = ll_hosts.get_spm_host(config.HOSTS)
    testflow.setup("Remove storage domain %s", domain_to_remove)
    assert ll_sd.removeStorageDomain(
        True, domain_to_remove, spm_host, **remove_param
    ), "Failed to remove storage domain %s" % domain_to_remove
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_DOMAIN])
    test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)


@pytest.fixture()
def attach_and_activate_storage_domain(request, storage):
    """
    Deactivate storage-domain
    """
    self = request.node.cls

    testflow.setup(
        "Attach and activate domain %s" % self.non_master
    )

    assert hl_sd.attach_and_activate_domain(
        config.DATA_CENTER_NAME, self.non_master
    ), "Failed to attach and activate domain %s" % self.non_master


@pytest.fixture(scope='class')
def attach_disk_to_cloned_vm(request, storage):
    """
    Attach a disk to a VM cloned from template
    """
    self = request.node.cls

    self.vm_to_attach_disk = self.vm_from_template
    attach_disk(request, storage)


@pytest.fixture()
def initialize_disk_params(request, storage):
    """
    Initialize disk parameters for add operation
    """
    self = request.node.cls

    self.add_disk_params = {
        'format': config.RAW_DISK, 'sparse': False, 'active': True,
        'storagedomain': ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, NFS
        )[0]
    }


@pytest.fixture()
def delete_snapshot_setup(request, storage):
    """
    Delete the snapshot created in the test
    """

    self = request.node.cls

    testflow.setup("Deleting snapshot %s", self.snapshot_description)
    assert ll_vms.removeSnapshot(
        True, self.vm_name, self.snapshot_description
    ), "Failed to remove snapshot %s" % self.snapshot_description


@pytest.fixture()
def create_vm_func_lvl(request, storage):
    """
    Create VM
    """
    create_vm(request, storage, remove_vm)


@pytest.fixture()
def block_connection_to_sd(request, storage):
    """
    Block connection from all hosts to storage domain address
    """
    # Block connection from all hosts to all available adresses of the
    # storage domain in order to be able to destroy it without deactivate it,
    # done to prevent from ovf update process to run

    self = request.node.cls

    def finalizer():
        for host_ip in self.host_ips:
            for address in self.non_master_address:
                testflow.teardown(
                    "Verify connection Unblocked between %s to %s",
                    host_ip, address
                )
                storage_helpers.unblockOutgoingConnection(
                    host_ip, config.HOSTS_USER, config.HOSTS_PW, address
                ), "Failed to unblock connection between %s to %s" % (
                    host_ip, address
                )
    request.addfinalizer(finalizer)

    found, address = ll_sd.getDomainAddress(True, self.non_master)
    assert found, "IP for storage domain %s not found" % (
        self.storage_domain
    )
    self.non_master_address = address['address']
    self.host_ips = list()

    for host in config.HOSTS:
        host_ip = ll_hosts.get_host_ip(host)
        for address in self.non_master_address:
            testflow.setup(
                "Block connection between %s to %s", host_ip, address
            )
            assert storage_helpers.blockOutgoingConnection(
                host_ip, config.HOSTS_USER, config.HOSTS_PW, address
            ), "Failed to block connection between %s to %s" % (
                host_ip, address
            )
        self.host_ips.append(host_ip)

    testflow.setup(
        "Wait for storage domain %s status %s",
        self.non_master, config.SD_INACTIVE
    )
    assert ll_sd.wait_for_storage_domain_status(
        True, config.DATA_CENTER_NAME, self.non_master, config.SD_INACTIVE
    )


@pytest.fixture()
def unblock_connection_to_sd(request, storage):
    """
    Unblock connection from all hosts to storage domain address
    """
    self = request.node.cls
    for host_ip in self.host_ips:
        for address in self.non_master_address:
            testflow.setup(
                "Unblock connection between %s to %s", host_ip, address
            )
            assert storage_helpers.unblockOutgoingConnection(
                host_ip, config.HOSTS_USER, config.HOSTS_PW, address
            ), "Failed to unblock connection between %s to %s" % (
                host_ip, address
            )
    hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)
    test_utils.wait_for_tasks(
        config.ENGINE, config.DATA_CENTER_NAME
    )


@pytest.fixture()
def wait_for_dc_state(request, storage):
    """
    Wait until Data center is in status OK finalizer
    """
    def finalizer():
        testflow.teardown(
            "Wait until Data center %s is in status OK",
            config.DATA_CENTER_NAME
        )
        assert ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME), (
            "Data center %s failed to reach state OK" % config.DATA_CENTER_NAME
        )

    request.addfinalizer(finalizer)
