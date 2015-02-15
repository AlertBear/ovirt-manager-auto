import logging
from art.rhevm_api.tests_lib.high_level.storagedomains import (
    addISCSIDataDomain,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    getSPMHost, waitForSPM, select_host_as_spm,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    get_total_size, removeStorageDomains, wait_for_change_total_size,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.test_handler.tools import tcms  # pylint: disable=E0611
import config

logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '6458'

SPM_TIMEOUT = 600
SPM_SLEEP = 5
MIN_UNUSED_LUNS = 2


def setup_module():
    """
    Creates datacenter, adds hosts, clusters, and storage domains depending
    on config file
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config=config.PARAMETERS,
                                storage=config.PARAMETERS,
                                storage_type=config.STORAGE_TYPE,
                                basename=config.TESTNAME,
                                local=config.LOCAL)


def teardown_module():
    """
    Removes created datacenter, storage domains etc.
    """
    if not config.GOLDEN_ENV:
        ll_st_domains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                      vdc=config.VDC,
                                      vdc_password=config.VDC_PASSWORD)


@attr(tier=0)
class TestCase94947(TestCase):
    """
    storage sanity test, create and extend a Data domain
    https://tcms.engineering.redhat.com/case/94947/
    """
    __test__ = TestCase.storage in config.BLOCK_TYPES
    tcms_test_case = '94947'
    bz = {'1186410': {'engine': ['rest', 'sdk'], 'version': ['3.5']}}

    def setUp(self):
        """
        Creates a storage domain
        """
        waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP)
        self.spm_host = getSPMHost(config.HOSTS)

        self.assertTrue(len(config.UNUSED_LUNS) >= MIN_UNUSED_LUNS,
                        "There are less than %s unused LUNs, aborting test"
                        % MIN_UNUSED_LUNS)
        self.sd_name = self.tcms_test_case + "_iSCSI_Domain"
        logger.info("The unused LUNs found are: '%s'", config.UNUSED_LUNS)
        status_attach_and_activate = addISCSIDataDomain(
            self.spm_host, self.sd_name,
            config.DATA_CENTER_NAME, config.UNUSED_LUNS["lun_list"][0],
            config.UNUSED_LUNS["lun_addresses"][0],
            config.UNUSED_LUNS["lun_targets"][0], override_luns=True
        )
        self.assertTrue(status_attach_and_activate,
                        "The domain was not added and activated "
                        "successfully")
        wait_for_jobs()
        self.domain_size = get_total_size(self.sd_name)
        logger.info("Total size for domain '%s' is '%s'", self.sd_name,
                    self.domain_size)

    def tearDown(self):
        """
        Removes storage domain created with setUp
        """
        logger.info("Removing Storage domain '%s'", self.sd_name)
        self.assertTrue(removeStorageDomains(True, self.sd_name,
                                             self.spm_host),
                        "Failed to remove domain '%s'" % self.sd_name)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_create_and_extend_storage_domain(self):
        """
        Creates and extends a storage domain
        """
        extend_lun = {
            "lun_list": [config.UNUSED_LUNS["lun_list"][1]],
            "lun_addresses": [config.UNUSED_LUNS["lun_addresses"][1]],
            "lun_targets": [config.UNUSED_LUNS["lun_targets"][1]],
            "override_luns": True
        }
        logger.info("Extending storage domain %s", self.sd_name)
        storagedomains.extend_storage_domain(self.sd_name, config.STORAGE_TYPE,
                                             self.spm_host, **extend_lun)
        wait_for_change_total_size(self.sd_name, self.domain_size)
        extended_sd_size = get_total_size(self.sd_name)
        logger.info("Total size for domain '%s' is '%s'", self.sd_name,
                    extended_sd_size)
        self.assertTrue(extended_sd_size > self.domain_size,
                        "The extended storage domain size hasn't increased")


@attr(tier=1)
class TestCase94950(TestCase):
    """
    storage sanity test, changing domain status
    https://tcms.engineering.redhat.com/case/94950/
    """
    __test__ = True
    tcms_test_case = '94950'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_change_domain_status_test(self):
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
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
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
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
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


@attr(tier=1)
class TestCase94954(TestCase):
    """
    storage sanity test, changing master domain
    https://tcms.engineering.redhat.com/case/94954/
    """
    __test__ = True
    tcms_test_case = '94954'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_change_master_domain_test(self):
        """ test checks if changing master domain works correctly
        """
        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        self.assertTrue(found, "Master domain not found!")

        old_master_domain_name = master_domain['masterDomain']

        logger.info("Deactivating master domain")
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
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


@attr(tier=0)
class TestCase288461(TestCase):
    """
    TCMS Test Case 288461 - Manually Re-assign SPM
    """
    __test__ = True
    tcms_test_plan = '9953'
    tcms_test_case = '288461'
    original_spm_host = None

    def setUp(self):
        logger.info("Waiting for SPM host to be elected on current Data "
                    "center")
        if not waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
            raise exceptions.HostException("SPM is not set on the current "
                                           "Data center")

        logger.info("Getting current SPM host and HSM hosts")
        self.original_spm_host = getSPMHost(config.HOSTS)
        self.hsm_hosts = [host for host in config.HOSTS if host !=
                          self.original_spm_host]
        if not self.original_spm_host:
            raise exceptions.HostException("Current SPM host could not be "
                                           "retrieved")
        if not self.hsm_hosts:
            raise exceptions.HostException("Did not find any HSM hosts")
        logger.info("Found SPM host: '%s', HSM hosts: '%s",
                    self.original_spm_host, self.hsm_hosts)

    def tearDown(self):
        if self.original_spm_host:
            logger.info("Waiting for SPM host to be elected")
            if not waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
                raise exceptions.HostException("SPM is not set on the current "
                                               "Data center")
            logger.info("Setting the original SPM host '%s' back as SPM",
                        self.original_spm_host)
            if not select_host_as_spm(True, self.original_spm_host,
                                      config.DATA_CENTER_NAME):
                raise exceptions.HostException("Did not successfully revert "
                                               "the SPM to host '%s'" %
                                               self.original_spm_host)

    @tcms(tcms_test_plan, tcms_test_case)
    def test_reassign_spm(self):
        """
        Assign first HSM host to be the SPM
        """
        self.new_spm_host = self.hsm_hosts[0]
        logger.info("Selecting HSM host '%s' as SPM", self.new_spm_host)
        self.assertTrue(select_host_as_spm(True, self.new_spm_host,
                                           config.DATA_CENTER_NAME),
                        "Unable to set host '%s' as SPM" % self.new_spm_host)
