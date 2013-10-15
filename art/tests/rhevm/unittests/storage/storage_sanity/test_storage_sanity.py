import logging
from unittest import TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.low_level.hosts import waitForSPM
from art.test_handler.tools import tcms, bz
from art.rhevm_api.tests_lib.low_level import hosts
import art.rhevm_api.utils.storage_api as st_api
import config

logger = logging.getLogger(__name__)


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
        config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS,
        storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE,
        basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    ll_st_domains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


class TestCase94947(TestCase):
    """
    storage sanity test, create & remove data center
    https://tcms.engineering.redhat.com/case/94947/?from_plan=4038
    """
    __test__ = True
    tcms_plan_id = '4038'
    tcms_test_case = '94947'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
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
                config.DATA_CENTER_TYPE,
                config.FIRST_HOST,
                config.PARAMETERS)


class TestCase94950(TestCase):
    """
    storage sanity test, changing domain status
    https://tcms.engineering.redhat.com/case/94947/?from_plan=4038
    """
    __test__ = True
    tcms_plan_id = '4038'
    tcms_test_case = '94950'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def change_domain_status_test(self):
        """ test checks if detaching/attaching storage domains works properly
        including that it is impossible to detach active domain
        """
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

        logger.info("Attaching non-master domains")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                True, config.DATA_CENTER_NAME, 'attach', 'all'),
            "Attaching non-master domains failed")

        logger.info("Activating non-master domains")
        self.assertTrue(
            ll_st_domains.execOnNonMasterDomains(
                True, config.DATA_CENTER_NAME, 'activate', 'all'),
            "Activating non-master domains failed")


class TestCase94954(TestCase):
    """
    storage sanity test, changing master domain
    https://tcms.engineering.redhat.com/case/94954/?from_plan=4038
    """
    __test__ = True
    tcms_plan_id = '4038'
    tcms_test_case = '94954'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
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


class TestCase68536(TestCase):
    """
    storage sanity test, disconnect SPM from storage
    https://tcms.engineering.redhat.com/case/68536/
    """
    __test__ = True
    tcms_plan_id = '2347'
    tcms_test_case = '68536'
    master_domain_ip = None
    spm = None

    @classmethod
    def setup_class(cls):
        logger.info("DC name : %s", config.DATA_CENTER_NAME)
        cls.spm = hosts.getSPMHost(config.HOSTS)
        logger.info("SPM found : %s",  cls.spm)

        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        master_domain = master_domain['masterDomain']
        logger.info("Master domain found : %s", master_domain)

        found, cls.master_domain_ip = ll_st_domains.getDomainAddress(
            True, master_domain)
        cls.master_domain_ip = cls.master_domain_ip['address']
        logger.info("Master domain ip found : %s", cls.master_domain_ip)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    @bz('1017207')
    def disconnect_SPM_from_storage_test(self):
        """ test checks if disconnecting SPM from storage domain
            works properly
        """

        logger.info("Blocking connectivity from SPM : %s to master domain : "
                    "%s", self.spm, self.master_domain_ip)
        found = st_api.blockOutgoingConnection(self.spm, 'root',
                                               config.VDS_PASSWORD[0],
                                               self.master_domain_ip)
        self.assertTrue(found, "block connectivity to master domain failed")

        logger.info("wait for state : 'Non Operational'")
        state = hosts.waitForHostsStates(True, self.spm,
                                         states=config.HOST_NONOPERATIONAL)
        logger.info("state: %s", state)
        self.assertTrue(state, "Cannot move to Non Operational state")

        logger.info("wait for state : 'Non Responsive'")
        state_is_fenced = \
            hosts.waitForHostsStates(True, self.spm,
                                     states=config.HOST_NONRESPONSIVE)

        logger.info("state: %s", state_is_fenced)
        self.assertFalse(state_is_fenced, "host fenced")

        self.assertTrue(waitForSPM(config.DATA_CENTER_NAME, 120, 10),
                        "wait for SPM")

        new_spm = hosts.getSPMHost(config.HOSTS)
        logger.info('new spm is %s', new_spm)
        self.assertTrue(self.spm != new_spm, "New SPM isn't elected")

    @classmethod
    def teardown_class(cls):
        """
        unblocking the connection from SPM to master domain
        """
        logger.info("unblocking connectivity from SPM : %s to master domain : "
                    "%s", cls.spm, cls.master_domain_ip)
        st_api.unblockOutgoingConnection(cls.spm, 'root',
                                         config.VDS_PASSWORD[0],
                                         cls.master_domain_ip)
