import logging
import config

from art.core_api.apis_exceptions import EntityNotFound
from art.test_handler.tools import tcms
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.low_level import datacenters as ll_datacenters
from art.rhevm_api.tests_lib.low_level import hosts, clusters, storagedomains

logger = logging.getLogger(__name__)


@attr(tier=0)
class TestCase99062(TestCase):
    """
    storage sanity test, clean up the environment
    https://tcms.engineering.redhat.com/case/99062/?from_plan=4038

    This test case expects one host
    """
    __test__ = True
    tcms_plan_id = '6458'
    tcms_test_case = '99062'
    host = config.HOSTS[0]

    def setUp(self):
        """Build the environment"""
        datacenters.build_setup(
            config=config.PARAMETERS,
            storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE,
            basename=config.BASENAME)

        SHARED_ISO = config.STORAGE['PARAMETERS.shared_iso_domain']

        assert hl_sd.addNFSDomain(
            host=self.host,
            storage=SHARED_ISO['shared_iso_domain_name'],
            data_center=config.DATA_CENTER_NAME,
            address=config.PARAMETERS['shared_iso_domain_address'],
            path=config.PARAMETERS['shared_iso_domain_path'],
            sd_type=config.ENUMS['storage_dom_type_iso'])

        status, masterDomain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert status
        self.master_domain = masterDomain['masterDomain']

        status, nonMasterDomains = storagedomains.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)
        assert status
        self.non_master_domains = nonMasterDomains['nonMasterDomains']

        self.iso_domains = storagedomains.findIsoStorageDomains(
            config.DATA_CENTER_NAME)
        assert self.iso_domains

        self.export_domains = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)
        assert self.export_domains

    @tcms(tcms_plan_id, tcms_test_case)
    def test_cleanup(self):
        """
        Verifies the environment can be clean up properly
        """
        assert clusters.searchForCluster(
            True, query_key='name', query_val=config.CLUSTER_NAME,
            key_name='name')
        assert clusters.isHostAttachedToCluster(
            True, self.host, config.CLUSTER_NAME)
        assert hosts.isHostUp(True, self.host)

        logger.info("Deactivating and deleting storage domains")
        for sd in self.non_master_domains + self.iso_domains \
                + self.export_domains:
            if sd in self.non_master_domains:
                format = 'true'
            else:
                format = 'false'
            assert storagedomains.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, sd)
            assert storagedomains.detachStorageDomain(
                True, config.DATA_CENTER_NAME, sd)
            assert storagedomains.removeStorageDomain(
                True, sd, self.host, format=format)

        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.master_domain)

        logger.info("Removing datacenter and storage domain")
        assert ll_datacenters.removeDataCenter(True, config.DATA_CENTER_NAME)

        assert ll_datacenters.searchForDataCenter(
            False, query_key='name', query_val=config.DATA_CENTER_NAME,
            key_name='name')

        assert storagedomains.removeStorageDomain(
            True, self.master_domain, self.host, format='true')

        logger.info("Deactivating host %s", self.host)
        assert hosts.deactivateHost(True, self.host)

        assert hosts.isHostInMaintenance(True, self.host)

        logger.info("Removing host %s", self.host)
        assert hosts.removeHost(True, self.host)

        self.assertRaises(
            EntityNotFound,
            hosts.HOST_API.find,
            self.host)

        logger.info("Removing cluster %s", config.CLUSTER_NAME)
        assert clusters.removeCluster(True, config.CLUSTER_NAME)

        assert clusters.searchForCluster(
            False, query_key='name', query_val=config.CLUSTER_NAME,
            key_name='name')
