import config
import logging
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.low_level.hosts import waitForSPM
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import hosts
import art.rhevm_api.utils.storage_api as st_api

logger = logging.getLogger(__name__)


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
        config file
    """
    local = True if config.STORAGE_TYPE == 'localfs' else False
    datacenters.build_setup(
        config=config.PARAMETERS,
        storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE,
        basename=config.TESTNAME,
        local=local)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    datacenters.clean_datacenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD
    )


@attr(tier=3)
class TestCase4742(TestCase):
    """
    storage sanity test, disconnect SPM from storage
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_2_Storage_Host%20Failure
    """
    __test__ = True
    polarion_test_case = '4742'
    master_domain_ip = None
    spm = None
    bz = {'1017207': {'engine': None, 'version': None}}

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

    @polarion("RHEVM3-4742")
    def test_disconnect_SPM_from_storage(self):
        """ test checks if disconnecting SPM from storage domain
            works properly
        """

        logger.info("Blocking connectivity from SPM : %s to master domain : "
                    "%s", self.spm, self.master_domain_ip)
        found = st_api.blockOutgoingConnection(self.spm, config.HOSTS_USER,
                                               config.HOSTS_PW,
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
        st_api.unblockOutgoingConnection(cls.spm, config.HOSTS_USER,
                                         config.HOSTS_PW,
                                         cls.master_domain_ip)
