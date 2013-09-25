import logging
import unittest
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.storagedomains import \
    findMasterStorageDomain, findNonMasterStorageDomains, cleanDataCenter
import config
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level.hosts import select_host_as_spm, \
    getSPMHost, checkSPMPriority, deactivateHosts, setSPMPriority
from art.rhevm_api.utils.storage_api import blockOutgoingConnection
from art.test_handler.tools import tcms

logger = logging.getLogger(__name__)

TCMS_TEST_PLAN = '9953'


def setup_module():
    """
    Build datacenter
    """
    build_setup(config=config.PARAMETERS, storage=config.PARAMETERS,
                storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)


def teardown_module():
    """
    Clean datacenter
    """
    cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)

class DCUp(unittest.TestCase):
    """
    Base class that ensures DC, all domains and hosts are up, spm is elected
    and spm priorities are set to default for all hosts
    """

    __test__ = False

    spm_host = None
    hsm_hosts = []
    master_domain = None
    master_address = None
    nonmaster_domain = None
    nonmaster_address = None

    @classmethod
    def setup_class(cls):
        """
        * Check that all entities for DC are up (hosts, SDs)
        * All hosts SPM priorities should be default (Normal)
        * SPM should be elected

        #TODO: If conditions do not hold remove everything and rebuild
        """
        logger.info('Getting spm host')
        cls.spm_host = getSPMHost(config.HOSTS)
        cls.hsm_hosts = [host for host in config.HOSTS if host != cls.spm_host]

        assert cls.spm_host
        assert len(cls.hsm_hosts) == 2

        logger.info('Found spm host: %s, hsm hosts: %s', cls.spm_host,
                    cls.hsm_hosts)

        rc, master_dom = findMasterStorageDomain(True, config.DATA_CENTER_NAME)
        assert rc

        rc, nonmaster_dom = findNonMasterStorageDomains(True,
                                                        config.DATA_CENTER_NAME)
        assert rc

        cls.master_domain = master_dom['masterDomain']
        cls.nonmaster_domain = nonmaster_dom['nonMasterDomains']

        assert cls.master_domain and cls.nonmaster_domain

        logger.info('Found master domain: %s, nonmaster domain: %s',
                    cls.master_domain, cls.nonmaster_domain)

        logger.info('Ensuring spm priority is default (%s) for all hosts')
        for host in config.HOSTS:
            assert checkSPMPriority(True, host, config.DEFAULT_SPM_PRIORITY)


    @classmethod
    def teardown_class(cls):
        """
        * Reset spm priorities for all hosts to default (Normal)
        * Reactivate all domains, and hosts
        """
        logger.info('Setting all hosts to maintenance')
        assert deactivateHosts(True, config.HOSTS)

        logger.info('Setting spm priority to %s for all hosts')
        for host in config.HOSTS:
            assert setSPMPriority(True, host, config.DEFAULT_SPM_PRIORITY)


class TestCase288461(DCUp):
    """
    TCMS Test Case 288461 - Manually Resign SPM
    """

    __test__ = True
    tcms_test_case = '288461'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_resign_spm(self):
        """
        Assign hsm host to be spm while another host is spm of DC
        """
        self.assertTrue(select_host_as_spm(True, self.hsm_hosts[0],
                                           config.DATA_CENTER_NAME),
                        'Unable to set host %s as spm' % self.hsm_hosts[0])
