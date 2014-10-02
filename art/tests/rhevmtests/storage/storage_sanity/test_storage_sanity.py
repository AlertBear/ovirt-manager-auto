import logging
from art.unittest_lib import StorageTest as TestCase, attr
from nose.tools import istest
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.test_handler.tools import tcms  # pylint: disable=E0611
import config

logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '6458'


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
        config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS,
        storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE,
        basename=config.TESTNAME,
        local=config.LOCAL)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    ll_st_domains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


@attr(tier=0)
class TestCase94947(TestCase):
    """
    storage sanity test, create & remove data center
    https://tcms.engineering.redhat.com/case/94947/
    """
    __test__ = True
    tcms_test_case = '94947'

    @istest
    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def create_remove_data_center_test(self):
        """ extends master storage domain
        """
        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        self.assertTrue(found, "Master domain not found!")

        master_domain_name = master_domain['masterDomain']
        if config.EXTEND_LUN is not None:
            logger.info(
                "extending master storage domain %s" % master_domain_name)
            storagedomains.extend_storage_domain(
                master_domain_name,
                config.STORAGE_TYPE,
                config.FIRST_HOST,
                **config.EXTEND_LUN)


@attr(tier=0)
class TestCase94950(TestCase):
    """
    storage sanity test, changing domain status
    https://tcms.engineering.redhat.com/case/94950/
    """
    __test__ = True
    tcms_test_case = '94950'

    @istest
    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def change_domain_status_test(self):
        """ test checks if detaching/attaching storage domains works properly
        including that it is impossible to detach active domain
        """
        found, non_master_storages = ll_st_domains.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)
        logger.info("Detaching active domain - should fail")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                False, config.DATA_CENTER_NAME, 'detach', 'all'),
            "Detached active domain...")

        logger.info("Deactivating non-master domains")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                True, config.DATA_CENTER_NAME, 'deactivate', 'all'),
            "Deactivating non-master domains failed")

        logger.info("Activating non-master domains")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                True, config.DATA_CENTER_NAME, 'activate', 'all'),
            "Activating non-master domains failed")

        logger.info("Deactivating non-master domains")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                True, config.DATA_CENTER_NAME, 'deactivate', 'all'),
            "Deactivating non-master domains failed")

        logger.info("Detaching non-master domains")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                True, config.DATA_CENTER_NAME, 'detach', 'all'),
            "Detaching non-master domains failed")

        # In local DC, once a domain is detached it is removed completely
        # so it cannot be reattached - only run this part of the test
        # for non-local DCs
        if not config.LOCAL:
            logger.info("Attaching non-master domains")
            for storage in non_master_storages['nonMasterDomains']:
                self.assertTrue(
                    ll_st_domains.attachStorageDomain(True,
                                                      config.DATA_CENTER_NAME,
                                                      storage),
                    "Attaching non-master domain failed")
            if config.COMPATIBILITY_VERSION != "3.3":
                logger.info("Activating non-master domains")
                self.assertTrue(
                    ll_st_domains.execOnNonMasterDomains(
                        True, config.DATA_CENTER_NAME, 'activate', 'all'),
                    "Activating non-master domains failed")
            for storage in non_master_storages['nonMasterDomains']:
                self.assertTrue(
                    ll_st_domains.waitForStorageDomainStatus(
                        True, config.DATA_CENTER_NAME, storage, 'active',
                        timeOut=60),
                    "non-master domains didn't become active")


@attr(tier=0)
class TestCase94954(TestCase):
    """
    storage sanity test, changing master domain
    https://tcms.engineering.redhat.com/case/94954/
    """
    __test__ = True
    tcms_test_case = '94954'

    @istest
    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def change_master_domain_test(self):
        """ test checks if changing master domain works correctly
        """
        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        self.assertTrue(found, "Master domain not found!")

        old_master_domain_name = master_domain['masterDomain']

        logger.info("Deactivating master domain")
        self.assertTrue(
            ll_st_domains.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, old_master_domain_name),
            "Cannot deactivate master domain")

        logger.info("Finding new master domain")
        found, new_master = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        logger.info("New master: %s" % new_master)
        self.assertTrue(found, "New master domain not found")

        logger.info("Activating old master domain")
        self.assertTrue(
            ll_st_domains.activateStorageDomain(
                True, config.DATA_CENTER_NAME, old_master_domain_name),
            "Cannot activate old master domain")
