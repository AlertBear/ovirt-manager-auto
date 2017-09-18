import config
import pytest
import logging
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
    datacenters as ll_dc,
    clusters as ll_clusters,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd
)
from utilities import utils
import rhevmtests.storage.helpers as storage_helpers
from art.test_handler import exceptions

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def init_hsm_host(request, storage):
    """
    Selects the first non-SPM host
    """
    self = request.node.cls

    status, hsm_host = ll_hosts.get_any_non_spm_host(
        config.HOSTS, cluster_name=config.CLUSTER_NAME
    )
    assert status, "Failed tp retrieve a non-SPM host on cluster '%s'" % (
                   config.CLUSTER_NAME
    )
    self.host_name = hsm_host['hsmHost']


@pytest.fixture(scope='class')
def get_setup_info(request, storage):
    """
    Ensures that environment is ready for tests, validating that master
    domain is found and has an IP address, retrieves the IP address of
    the engine and the first host found under the second cluster
    """
    self = request.node.cls

    testflow.setup("DC name is: '%s'", config.DATA_CENTER_NAME)
    found, master_domain = ll_sd.findMasterStorageDomain(
        True, config.DATA_CENTER_NAME
    )
    assert found, (
        "Could not find master storage domain on Data center '%s'" % (
            config.DATA_CENTER_NAME
        )
    )
    master_domain = master_domain['masterDomain']
    logger.info("Master domain found : %s", master_domain)

    found, self.master_domain_ip = ll_sd.getDomainAddress(
        True, master_domain
    )
    assert found, (
        "Could not find the IP address for the master storage domain "
        "host '%s'" % master_domain
    )
    self.master_domain_ip = self.master_domain_ip['address']
    logger.info("Master domain ip found : %s", self.master_domain_ip)

    self.engine_ip = utils.getIpAddressByHostName(config.VDC)
    self.first_host_ip = ll_hosts.get_host_ip(self.host_name)


@pytest.fixture(scope='class')
def init_storage_domains_params(request, storage):
    """
    Initialize storage domain parameters
    """
    self = request.node.cls

    self.nfs_sd_path = config.NFS_DOMAINS_KWARGS[0]['path']
    self.nfs_sd_address = config.NFS_DOMAINS_KWARGS[0]['address']

    self.gluster_sd_path = config.GLUSTER_DOMAINS_KWARGS[0]['path']
    self.gluster_sd_address = config.GLUSTER_DOMAINS_KWARGS[0]['address']

    self.sd_lun = config.ISCSI_DOMAINS_KWARGS[0]['lun']
    self.sd_lun_address = config.ISCSI_DOMAINS_KWARGS[0]['lun_address']
    self.sd_lun_target = config.ISCSI_DOMAINS_KWARGS[0]['lun_target']
    if config.UNUSED_FC_LUNS:
        self.sd_fc_lun = config.FC_DOMAINS_KWARGS[0]['fc_lun']


@pytest.fixture(scope='class')
def unblock_connectivity_engine_to_host(request, storage):
    """
    Unblock all connections that were blocked during the test
    """
    self = request.node.cls

    def finalizer():
        def check_dc_and_host_state():
            """Checks whether DC and host used are available"""
            return (
                ll_dc.waitForDataCenterState(
                    config.DATA_CENTER_NAME,
                    timeout=config.DATA_CENTER_INIT_TIMEOUT
                ) and ll_hosts.is_host_up(True, self.host_name)
            )

        if not check_dc_and_host_state():
            testflow.teardown("Unblocking connections, something went wrong")
            try:
                storage_helpers.setup_iptables(
                    self.engine_ip, self.first_host_ip, block=False
                )
            except exceptions.NetworkException, msg:
                logging.info("Connection already unblocked. Reason: %s", msg)

        if not check_dc_and_host_state():
            self.test_failed = True
            testflow.teardown(
                "Could not successfully restore the Data center state and "
                "host within the timeout period"
            )

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def create_dc(request, storage):
    """
    Creates a data center and cluster with no hosts
    """
    self = request.node.cls

    assert ll_dc.addDataCenter(
            True, name=self.new_dc_name, local=False,
            version=self.dc_version
    ), "Failed to create Data center '%s'" % self.new_dc_name


@pytest.fixture(scope='class')
def create_cluster(request, storage):
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
def create_storage_domains_for_upgrade(request, storage):
    """
    Creates storage domains for upgrade tests
    """
    self = request.node.cls

    self.sd_names = []
    if config.NFS in self.storage_types_for_exec:
        self.nfs_sd_name = 'upgrade_%s_to_%s_NFS' % self.name_pattern
        testflow.setup("Adding NFS storage domain needed for tests")
        testflow.setup(
            "Address: %s, Path: %s", self.nfs_sd_address, self.nfs_sd_path
        )
        assert hl_sd.addNFSDomain(
            self.host_name, self.nfs_sd_name, self.new_dc_name,
            self.nfs_sd_address, self.nfs_sd_path,
            storage_format=self.storage_format
        ), "Failed to create NFS Storage domain '%s'" % self.nfs_sd_name
        testflow.setup(
            "NFS storage domain %s was created successfully", self.nfs_sd_name
        )
        self.sd_names.append(self.nfs_sd_name)
    if config.ISCSI in self.storage_types_for_exec:
        self.iscsi_sd_name = 'upgrade_%s_to_%s_iSCSI' % self.name_pattern
        testflow.setup("Adding iSCSI storage domain needed for tests")
        assert hl_sd.add_iscsi_data_domain(
            self.host_name, self.iscsi_sd_name, self.new_dc_name, self.sd_lun,
            self.sd_lun_address, self.sd_lun_target,
            storage_format=self.storage_format, override_luns=True
        ), "Failed to create iSCSI Storage domain '%s'" % self.iscsi_sd_name
        testflow.setup(
            "iSCSI storage domain %s was created successfully",
            self.iscsi_sd_name
        )
        self.sd_names.append(self.iscsi_sd_name)
    if config.GLUSTER in self.storage_types_for_exec:
        self.gluster_sd_name = 'upgrade_%s_to_%s_gluster' % self.name_pattern
        testflow.setup("Adding Gluster storage domain needed for tests")
        testflow.setup(
            "Address: %s, Path: %s", self.gluster_sd_address,
            self.gluster_sd_path
        )
        assert hl_sd.addGlusterDomain(
            self.host_name, self.gluster_sd_name, self.new_dc_name,
            self.gluster_sd_address, self.gluster_sd_path,
            vfs_type=config.ENUMS['vfs_type_glusterfs']
        ), (
            "Failed to create Gluster Storage domain '%s'" %
            self.gluster_sd_name
        )
        testflow.setup(
            "Gluster storage domain %s was created successfully",
            self.gluster_sd_name
        )
        self.sd_names.append(self.gluster_sd_name)
    """checks if FC LUNs exists:"""
    if config.UNUSED_FC_LUNS:
        if config.FCP in self.storage_types_for_exec:
            self.fcp_sd_name = 'upgrade_%s_to_%s_FCP' % self.name_pattern
            testflow.setup("Adding FCP storage domain needed for tests")
            assert hl_sd.add_fcp_data_domain(
                self.host_name, self.fcp_sd_name, self.new_dc_name,
                self.sd_fc_lun, override_luns=True
            ), "Failed to create FCP Storage domain '%s'" % self.fcp_sd_name
            testflow.setup(
                "FCP storage domain %s was created successfully",
                self.fcp_sd_name
            )
            self.sd_names.append(self.fcp_sd_name)


@pytest.fixture(scope='class')
def deactivate_and_remove_non_master_domains(request, storage):
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
                if sd_name != master_domain:
                    testflow.teardown(
                        "deactivating storage domain %s", sd_name
                    )
                    assert ll_sd.deactivateStorageDomain(
                        True, self.new_dc_name, sd_name
                    ), ("Failed to deactivate storage domain %s" % sd_name)
                    testflow.teardown("Removing storage domain %s", sd_name)
                    assert hl_sd.remove_storage_domain(
                        sd_name, self.new_dc_name, self.host_name,
                        engine=config.ENGINE, format_disk=True
                    ), ("Failed to remove storage domain %s", sd_name)
        self.storage_domain = master_domain
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def remove_unattached_domain(request, storage):
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
    self.storage_domain = None
