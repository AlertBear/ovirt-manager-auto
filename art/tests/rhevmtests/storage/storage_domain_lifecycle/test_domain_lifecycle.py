import logging

from art.unittest_lib.common import testflow

import pytest
from sys import modules
import config

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    storagedomains as ll_sd,
    clusters as ll_clusters
)

from fixtures import (
    get_setup_info, unblock_connectivity_engine_to_host, init_hsm_host,
    init_storage_domains_params, create_dc, create_cluster,
    create_storage_domains_for_upgrade, remove_unattached_domain,
    deactivate_and_remove_non_master_domains
)

from rhevmtests.storage.fixtures import (
    move_host_to_another_cluster, clean_dc, create_storage_domain,
)

from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
    storages,
)
from art.unittest_lib import StorageTest as TestCase

from rhevmtests.storage import helpers as storage_helpers


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

__THIS_MODULE = modules[__name__]


@pytest.mark.usefixtures(
    init_hsm_host.__name__,
    get_setup_info.__name__
)
class BaseTestCase(TestCase):
    """
    Implement the common setup for this feature
    """
    __test__ = False
    polarion_test_case = None
    master_domain_ip = None
    engine_ip = None


@pytest.mark.usefixtures(
    unblock_connectivity_engine_to_host.__name__
)
class TestCase11598(BaseTestCase):
    """
    * Block connection from engine to host.
    * Wait until host goes to non-responsive.
    * Unblock connection.
    * Check that the host is up again.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11598'

    @polarion("RHEVM3-11598")
    @tier4
    def test_disconnect_engine_from_host(self):
        """
        Block connection from one engine to host.
        Wait until host goes to non-responsive.
        Unblock connection.
        Check that the host is up again.
        """
        assert storage_helpers.block_and_wait(
            self.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.first_host_ip, self.host_name, config.HOST_NONRESPONSIVE
        )

        assert storage_helpers.unblock_and_wait(
            self.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.first_host_ip, self.host_name
        )


@pytest.mark.usefixtures(
    init_hsm_host.__name__,
    create_storage_domain.__name__,
)
class TestCase11784(TestCase):
    """
    Create storage domains from all types and attach them to datacenter
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Multiple_Storage_Domains_General
    """
    __test__ = True
    polarion_test_case = '11784'

    @polarion("RHEVM3-11784")
    @tier3
    def test_add_another_storage_domain_test(self):
        """
        Sets up storage parameters, creates storage domain and check that both
        storage domains were automatically activated after attaching them
        """
        pass


@pytest.mark.usefixtures(
    init_hsm_host.__name__,
    init_storage_domains_params.__name__,
    create_dc.__name__,
    create_cluster.__name__,
    move_host_to_another_cluster.__name__,
    remove_unattached_domain.__name__,
    clean_dc.__name__,
    deactivate_and_remove_non_master_domains.__name__,
)
@storages((config.NOT_APPLICABLE,))
class TestUpgrade(TestCase):
    """
    Base class for upgrade testing
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Storage_Domain_Live_Upgrade
    """
    __test__ = False
    host_name = None
    storage_types_for_exec = config.STORAGES_MATRIX
    storage_domain = None
    name_pattern = None
    new_dc_name = None
    nfs_sd_name = None
    iscsi_sd_name = None
    gluster_sd_name = None
    fcp_sd_name = None
    cluster_version = None
    cluster_upgraded_version = None
    dc_version = None
    dc_upgraded_version = None
    storage_format = None
    upgraded_storage_format = None
    domain_kw = ['data_domain_address', 'lun', 'data_domain_address']
    polarion_test_case = '11743'

    @polarion("RHEVM3-11743")
    @tier2
    def test_data_center_upgrade(self):
        """
        Upgarde a DC with mixed types storage domains and a VM with disk on
        each domain
        """

        for sd_name in self.sd_names:
            vm_name = (
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_VM
                )
            )
            create_vm_args = config.create_vm_args.copy()
            create_vm_args['vmName'] = vm_name
            create_vm_args['installation'] = False
            create_vm_args['cluster'] = self.cluster_name
            create_vm_args['storageDomainName'] = sd_name
            testflow.setup("Creating VM %s", vm_name)
            assert storage_helpers.create_vm_or_clone(**create_vm_args), (
                "Failed to create VM %s" % vm_name
            )
        testflow.setup(
            "Upgrading cluster %s from version %s to version %s ",
            self.cluster_name, self.cluster_version,
            self.cluster_upgraded_version
        )
        assert ll_clusters.updateCluster(
            True, self.cluster_name,
            version=self.cluster_upgraded_version,
        ), "Failed to upgrade compatibility version of cluster"
        testflow.setup(
            "Upgrading Data Center %s from version %s to version %s ",
            self.new_dc_name, self.dc_version, self.dc_upgraded_version
        )
        ll_dc.update_datacenter(
            True, datacenter=self.new_dc_name,
            version=self.dc_upgraded_version
        )
        sds = ll_sd.getDCStorages(self.new_dc_name, get_href=False)
        for sd_obj in sds:
            was_upgraded = ll_sd.checkStorageFormatVersion(
                True, sd_obj.get_name(), self.upgraded_storage_format
            )
            logger.info(
                "Checking that %s was upgraded: %s", sd_obj.get_name(),
                was_upgraded
            )
            assert was_upgraded


@pytest.mark.usefixtures(
    create_storage_domains_for_upgrade.__name__
)
class TestUpgrade_36_to_40(TestUpgrade):
    """
    Initializing DC parameters for 3.6 to 4.0 upgrade
    """
    __test__ = True
    name_pattern = '3_6', '4_0'
    new_dc_name = 'dc_upgrade_%s_to_%s' % name_pattern
    cluster_name = 'cluster_upgrade_%s_to_%s' % name_pattern
    nfs_sd_name = "sd_upgrade_%s_to_%s_nfs" % name_pattern
    iscsi_sd_name = "sd_upgrade_%s_to_%s_iscsi" % name_pattern
    gluster_sd_name = "sd_upgrade_%s_to_%s_gluster" % name_pattern
    fcp_sd_name = "sd_upgrade_%s_to_%s_fcp" % name_pattern
    cluster_version = '3.6'
    cluster_upgraded_version = '4.0'
    dc_version = '3.6'
    dc_upgraded_version = '4.0'
    storage_format = 'v3'
    upgraded_storage_format = 'v3'


@pytest.mark.usefixtures(
    create_storage_domains_for_upgrade.__name__
)
class TestUpgrade_40_to_41(TestUpgrade):
    """
    Initializing DC parameters for 4.0 to 4.1 upgrade
    """
    __test__ = True
    name_pattern = '4_0', '4_1'
    new_dc_name = 'dc_upgrade_%s_to_%s' % name_pattern
    cluster_name = 'cluster_upgrade_%s_to_%s' % name_pattern
    nfs_sd_name = "sd_upgrade_%s_to_%s_nfs" % name_pattern
    iscsi_sd_name = "sd_upgrade_%s_to_%s_iscsi" % name_pattern
    gluster_sd_name = "sd_upgrade_%s_to_%s_gluster" % name_pattern
    fcp_sd_name = "sd_upgrade_%s_to_%s_fcp" % name_pattern
    cluster_version = '4.0'
    cluster_upgraded_version = '4.1'
    dc_version = '4.0'
    dc_upgraded_version = '4.1'
    storage_format = 'v3'
    upgraded_storage_format = 'v4'
