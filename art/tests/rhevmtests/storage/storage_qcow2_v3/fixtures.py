import config
import pytest
import logging
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
    datacenters as ll_dc,
    clusters as ll_clusters,
    jobs as ll_jobs,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd
)
from rhevmtests.storage import helpers as storage_helpers
logger = logging.getLogger(__name__)
from art.unittest_lib.common import StorageTest as TestCase  # noqa


@pytest.fixture(scope='class')
def init_hsm_host(request):
    """
    Selects the first non-SPM host
    """
    self = request.node.cls

    status, hsm_host = ll_hosts.get_any_non_spm_host(
        config.HOSTS, cluster_name=config.CLUSTER_NAME
    )
    assert status, "Failed to retrieve a non-SPM host on cluster '%s'" % (
        config.CLUSTER_NAME
    )
    self.host_name = hsm_host['hsmHost']


@pytest.fixture(scope='class')
def init_spm_host(request):
    """
    Selects the first non-SPM host
    """
    self = request.node.cls

    self.spm_host = ll_hosts.get_spm_host(config.HOSTS)
    assert self.spm_host, "Failed tp retrieve SPM host on cluster '%s'" % (
        config.CLUSTER_NAME
    )


@pytest.fixture(scope='class')
def create_dc_with_no_hosts(request):
    """
    Creates a data center with no hosts
    """
    self = request.node.cls

    assert ll_dc.addDataCenter(
        True, name=self.new_dc_name, local=False, version=self.dc_version
    ), "Failed to create data center '%s'" % self.new_dc_name


@pytest.fixture(scope='class')
def create_cluster_with_no_hosts(request):
    """
    Creates a cluster with no hosts
    """
    self = request.node.cls

    self.host_ip = ll_hosts.get_host_ip(self.host_name)
    logger.info(
        "Retrieve the first host from the 2nd cluster (in original Data "
        "center)"
    )
    assert ll_clusters.addCluster(
        True, name=self.cluster_name, cpu=config.CPU_NAME,
        data_center=self.new_dc_name, version=self.cluster_version
    ), "Failed to create Cluster '%s'" % self.cluster_name


@pytest.fixture(scope='class')
def create_one_or_more_storage_domains_same_type_for_upgrade(request):
    """
    Creates one or more storage domain for upgrade tests
    """
    self = request.node.cls

    self.sd_names = []
    for sd in range(self.new_storage_domains_count):

            self.storage_domain = (
                'upgrade_%s_to_%s' % self.name_pattern + self.storage + str(sd)
            )

            storage_helpers.add_storage_domain(
                self.storage_domain, self.new_dc_name, sd,
                self.storage
            )


@pytest.fixture(scope='class')
def deactivate_and_remove_non_master_domains(request):
    """
    Remove storage domains created for the test
    """
    self = request.node.cls

    def finalizer():
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, self.new_dc_name
        )
        assert found, (
            "Could not find master storage domain on data center '%s'"
            % self.new_dc_name
        )
        master_domain = master_domain['masterDomain']
        testflow.teardown(
            "Data center's %s master domain is %s", self.new_dc_name,
            master_domain
        )

        for sd_name in self.sd_names:
            if ll_sd.checkIfStorageDomainExist(True, sd_name):
                if not sd_name == master_domain:
                    testflow.teardown(
                        "deactivating storage domain %s", sd_name
                    )
                    assert ll_sd.deactivateStorageDomain(
                        True, self.new_dc_name, sd_name
                    ), "Failed to deactivate storage domain %s" % sd_name
                    testflow.teardown("Removing storage domain %s ", sd_name)
                    assert hl_sd.remove_storage_domain(
                        sd_name, self.new_dc_name, self.host_name,
                        engine=config.ENGINE, format_disk=True
                    ), "Failed to remove storage domain %s" % sd_name
        self.storage_domain = master_domain
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def remove_unattached_domain(request):
    """
    Remove the unattached domain left after DC removal
    """
    self = request.node.cls

    def finalizer():
        if ll_sd.checkIfStorageDomainExist(True, self.storage_domain):
            testflow.teardown("Remove storage domain %s", self.storage_domain)
            assert ll_sd.removeStorageDomain(
                True, self.storage_domain, self.host_name, format='true',
            ), ("Failed to remove storage domain %s", self.storage_domain)

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_dc_parameters_for_upgrade(request):
    """
    Initializing DC parameters for 4.0 to 4.1 upgrade
    """

    self = request.node.cls

    self.name_pattern = '4_0', '4_1'
    self.new_dc_name = 'dc_upgrade_%s_to_%s' % self.name_pattern
    self.cluster_name = 'cluster_upgrade_%s_to_%s' % self.name_pattern
    self.nfs_sd_name = "sd_upgrade_%s_to_%s_nfs" % self.name_pattern
    self.iscsi_sd_name = "sd_upgrade_%s_to_%s_iscsi" % self.name_pattern
    self.gluster_sd_name = "sd_upgrade_%s_to_%s_gluster" % self.name_pattern
    self.fcp_sd_name = "sd_upgrade_%s_to_%s_fcp" % self.name_pattern
    self.cluster_version = '4.0'
    self.cluster_upgraded_version = '4.1'
    self.dc_version = '4.0'
    self.dc_upgraded_version = '4.1'
    self.storage_format = 'v3'
    self.upgraded_storage_format = 'v4'


@pytest.fixture(scope='class')
def remove_another_vm(request):
    """
    Remove another VM created during the test
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Remove VM %s", self.new_vm_name)
        assert ll_vms.safely_remove_vms([self.new_vm_name]), (
            "Failed to power off and remove VM %s" % self.new_vm_name
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def init_test_vm_name(request):
    """
    Initialize test vm name
    """

    self = request.node.cls

    self.new_vm_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    self.vm_names = list()
    self.vm_names.append(self.new_vm_name)


@pytest.fixture(scope='class')
def init_test_template_name(request):
    """
    Initialize test template name
    """

    self = request.node.cls

    self.template_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture(scope='class')
def init_base_params(request):
    """
    Initialize base class parameters
    """

    self = request.node.cls

    if not hasattr(self, 'new_storage_domains_count'):
        self.new_storage_domains_count = 1
    self.host_name = None
    self.storage_domain = None
    self.name_pattern = None
    self.new_dc_name = None
    self.nfs_sd_name = None
    self.iscsi_sd_name = None
    self.gluster_sd_name = None
    self.fcp_sd_name = None
    self.cluster_version = None
    self.cluster_upgraded_version = None
    self.dc_version = None
    self.dc_upgraded_version = None
    self.storage_format = None
    self.upgraded_storage_format = None
    self.disk_count = None
    self.template_name = config.TEMPLATE_NAME[0]
