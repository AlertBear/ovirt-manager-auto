import pytest
import logging
import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import remove_vm  # flake8: noqa

logger = logging.getLogger(__name__)

ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIX = config.STORAGE_TYPE_POSIX
CEPH = config.STORAGE_TYPE_CEPH


@pytest.fixture(scope='class')
def initialize_params(request):
    """
    Clean the environment
    """
    self = request.node.cls

    self.test_failed = False
    self.vm_name = getattr(self, 'vm_name', None)
    if not hasattr(self, 'master_domain'):
        status, master_domain = ll_sd.findMasterStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME
        )
        if not status:
            raise exceptions.StorageDomainException(
                "Unable to find master storage domain"
            )
    self.host = ll_hosts.getSPMHost(config.HOSTS)
    self.non_master = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_SD
            )
    # initialize for create_vm fixture
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = self.non_master
        self.deep_copy = True


@pytest.fixture()
def deactivate_detach_and_remove_domain_fin(request):

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
        spm_host = ll_hosts.getSPMHost(config.HOSTS)
        assert hl_sd.remove_storage_domain(
            domain_to_remove, dc_name, spm_host, format_disk=True
        ), "Failed to detach and remove storage-domain %s" % domain_to_remove
    request.addfinalizer(finalizer)


@pytest.fixture()
def add_non_master_storage_domain(request):
    """
    Add new non master storage domain
    """
    self = request.node.cls

    self.index = getattr(self, 'index', 0)
    self.dc_name = getattr(self, 'dc_name', config.DATA_CENTER_NAME)
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
def remove_storage_domain_fin(request):

    self = request.node.cls

    def finalizer():
        """
        Remove storage domain
        """
        domain_to_remove = config.DOMAIN_TO_REMOVE
        destroy = getattr(self, 'destroy', False)
        assert ll_sd.removeStorageDomain(
            True, domain_to_remove, config.HOSTS[0], format='true',
            destroy=destroy
        ), "Failed to remove storage domain %s" % domain_to_remove
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def add_master_storage_domain_to_new_dc(request):
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
    storage_helpers.add_storage_domain(
        self.master_domain, self.new_dc_name, 0, self.storage
    )
    # initialize for remove_storage_domain_fin fixture
    config.DOMAIN_TO_REMOVE = self.master_domain


@pytest.fixture(scope='class')
def add_non_master_storage_domain_to_new_dc(request):
    """
    Add new non master storage domain
    """
    self = request.node.cls
    self.new_dc_name = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
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
    request, secure_deactivate_storage_domain
):
    """
    Deactivate and detach storage-domain
    """
    self = request.node.cls

    testflow.setup(
        "Detach storage domain %s", self.domain_to_detach
    )
    assert hl_sd.detach_domain(
        self.dc_to_detach_from, self.domain_to_detach
    ), "Unable to detach %s" % self.domain_to_detach


@pytest.fixture()
def secure_deactivate_storage_domain(request):
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
        self.dc_to_detach_from, self.domain_to_detach
    ), "Failed to detach domain %s" % self.domain_to_detach


@pytest.fixture()
def create_gluster_or_posix_export_domain(request, attach_export_domain):
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
            format_disk=True
        ), "Failed to detach and remove storage-domain %s" % self.export_domain
    request.addfinalizer(finalizer)

    self.export_domain = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    self.host = ll_hosts.getSPMHost(config.HOSTS)
    if self.storage == POSIX:
        self.export_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[1]
        self.export_path = config.UNUSED_DATA_DOMAIN_PATHS[1]
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
            config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[1]
        )
        self.export_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[1]
        self.vfs_type = config.ENUMS['vfs_type_glusterfs']
        self.storage_type = GLUSTER

        assert hl_sd.addGlusterDomain(
            self.host, self.export_domain, config.DATA_CENTER_NAME,
            self.export_address, self.export_path,
            vfs_type=self.vfs_type, sd_type=self.sd_type
        ), "Creating GlusterFS domain '%s' failed" % self.export_domain
    test_utils.wait_for_tasks(
        config.VDC, config.VDC_ROOT_PASSWORD, config.DATA_CENTER_NAME
    )
    hl_sd.remove_storage_domain(
        self.export_domain, config.DATA_CENTER_NAME, self.host, False,
        config.VDC, config.VDC_PASSWORD
    )


@pytest.fixture()
def attach_export_domain(request):
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
def remove_template_setup(request):
    """
    Remove template from the data-center
    """
    self = request.node.cls

    assert ll_templates.removeTemplate(True, self.template_name), (
        "Failed to remove template %s" % self.template_name
    )


@pytest.fixture()
def remove_storage_domain_setup(request):
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

    spm_host = ll_hosts.getSPMHost(config.HOSTS)

    assert ll_sd.removeStorageDomain(
        True, domain_to_remove, spm_host, **remove_param
    ), "Failed to remove storage domain %s" % domain_to_remove
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_DOMAIN])
