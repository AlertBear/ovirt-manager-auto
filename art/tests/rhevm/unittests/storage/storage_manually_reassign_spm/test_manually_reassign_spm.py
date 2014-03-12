import logging
from time import sleep
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.storagedomains import \
    findMasterStorageDomain, findNonMasterStorageDomains, cleanDataCenter, \
    getDomainAddress, deactivateStorageDomain, activateStorageDomain
import config
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level.hosts import select_host_as_spm, \
    getSPMHost, checkSPMPriority, deactivateHosts, setSPMPriority, \
    waitForSPM, checkHostSpmStatus, activateHosts, isHostUp
from art.rhevm_api.utils.storage_api import blockOutgoingConnection, \
    unblockOutgoingConnection
from art.test_handler.tools import tcms, bz

logger = logging.getLogger(__name__)

TCMS_TEST_PLAN = '9953'


def setup_module():
    """
    Build datacenter
    """
    build_setup(config=config.PARAMETERS, storage=config.PARAMETERS,
                storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)

    assert deactivateHosts(True, config.HOSTS)


def teardown_module():
    """
    Clean datacenter
    """
    assert activateHosts(True, config.HOSTS)
    cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class DCUp(TestCase):
    """
    Base class that ensures DC, all domains and hosts are up, spm is elected
    and spm priorities are set to default for all hosts
    """

    __test__ = False

    spm_priorities = []

    spm_host = None
    hsm_hosts = []
    master_domain = None
    master_address = None
    nonmaster_domain = None
    nonmaster_address = None

    @classmethod
    def setup_class(cls):
        """
        * Set hosts' spm priorities according to spm_priorities list
        * SPM should be elected
        * Check that all entities for DC are up (hosts, SDs)
        """
        if not cls.spm_priorities:
            cls.spm_priorities = [config.DEFAULT_SPM_PRIORITY] * \
                len(config.HOSTS)

        logger.info('Setting spm priorities for hosts: %s', cls.spm_priorities)
        for host, priority in zip(config.HOSTS, cls.spm_priorities):
            assert setSPMPriority(True, host, priority)

        hosts_to_activate = [host for host in config.HOSTS if not
                             isHostUp(True, host)]
        logger.info('Reactivating hosts: %s', hosts_to_activate)
        assert activateHosts(True, hosts_to_activate)

        logger.info('Waiting for spm to be elected')
        assert waitForSPM(config.DATA_CENTER_NAME, 120, 60)

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
        cls.nonmaster_domain = nonmaster_dom['nonMasterDomains'][0]

        logger.info('Found master domain: %s, nonmaster domain: %s',
                    cls.master_domain, cls.nonmaster_domain)

        rc, master_address = getDomainAddress(True, cls.master_domain)

        assert rc

        rc, nonmaster_address = getDomainAddress(True, cls.nonmaster_domain)

        assert rc

        cls.master_address = master_address['address']
        cls.nonmaster_address = nonmaster_address['address']

        logger.info('Found master domain address: %s, nonmaster domain '
                    'address: %s', cls.master_address, cls.nonmaster_address)

        logger.info('Ensuring spm priority is for all hosts')
        for host, priority in zip(config.HOSTS, cls.spm_priorities):
            assert checkSPMPriority(True, host, priority)

    @classmethod
    def teardown_class(cls):
        """
        * Reset spm priorities for all hosts to default (Normal)
        * Reactivate all domains, and hosts
        """
        logger.info('Setting all hosts to maintenance')
        assert deactivateHosts(True, config.HOSTS)

        logger.info('Resetting spm priority to %s for all hosts',
                    cls.spm_priorities)
        for host, priority in zip(config.HOSTS, cls.spm_priorities):
            assert setSPMPriority(True, host, priority)


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


class SelectNewSPMDuringSPMElection(DCUp):
    """
    Class that Begins spm selection, then selects a second host as spm during
    the original spm selection expecting the second action to succeed
    """

    __test__ = False
    first_spm = None
    second_spm = None

    def select_new_spm_during_selection(self):
        """
        First select first_spm then second_spm
        """
        logger.info('Selecting %s as spm', self.first_spm)
        self.assertTrue(select_host_as_spm(True, self.first_spm,
                                           config.DATA_CENTER_NAME,
                                           wait=False))

        logger.info('Attempting to select %s as spm', self.second_spm)
        self.assertTrue(select_host_as_spm(True, self.second_spm,
                                           config.DATA_CENTER_NAME,
                                           wait=False))

        logger.info('Waiting for spm selection to complete')
        self.assertTrue(waitForSPM(config.DATA_CENTER_NAME, 120, 10))

        self.assertTrue(checkHostSpmStatus(True, self.second_spm))
        logger.info('SPM selected successfully')


class TestCase288463(SelectNewSPMDuringSPMElection):
    """
    TCMS Test Case 288463 - Set new host as spm during spm election
    """
    # Case disabled due to failing on race condition sometimes - fails
    # to select second host as spm with CanDoAction on engine. Unable to
    # reproduce consistently, should be solved later.
    __test__ = False
    tcms_test_case = '288463'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_select_new_host_as_spm(self):
        """
        * Start spm election
        * Select new host as spm during election
        """
        self.first_spm = self.hsm_hosts[0]
        self.second_spm = self.hsm_hosts[1]
        self.select_new_spm_during_selection()


class TestCase293727(SelectNewSPMDuringSPMElection):
    """
    TCMS Test Case 288463 - Set previous spm host as spm during new spm
    election
    """
    # Case disabled due to failing on race condition sometimes - fails
    # to select second host as spm with CanDoAction on engine. Unable to
    # reproduce consistently, should be solved later.
    __test__ = False
    tcms_test_case = '293727'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_select_new_host_as_spm(self):
        """
        * Start spm election
        * Select host that was spm before as spm during election
        """
        self.first_spm = self.hsm_hosts[0]
        self.second_spm = self.spm_host
        self.select_new_spm_during_selection()


class ReassignSPMWithStorageBlocked(DCUp):
    """
    Block connection between specified hosts and specified domain and try to
    reassign spm
    """

    __test__ = False
    domain_blocked = []
    domain_to_block = None
    hosts_to_block = []
    wait_for_dc_status = None

    def block_connection_and_reassign_spm(self):
        self.domain_blocked = []
        for host in self.hosts_to_block:
            logger.info('Blocking connection between %s and %s', host,
                        self.domain_to_block)
            self.assertTrue(blockOutgoingConnection(host,
                                                    config.HOST_USER,
                                                    config.HOST_PASSWORD[0],
                                                    self.domain_to_block),
                            'Unable to block connection between %s and %s'
                            % (self.spm_host, self.domain_to_block))
            self.domain_blocked.append(host)

        if self.wait_for_dc_status:
            logger.info('Waiting for status %s on datacenter %s',
                        self.wait_for_dc_status, config.DATA_CENTER_NAME)
            self.assertTrue(waitForDataCenterState(config.DATA_CENTER_NAME,
                                                   self.wait_for_dc_status,
                                                   timeout=360))

        logger.info('Setting host %s to be new spm', self.hsm_hosts[0])
        self.assertTrue(select_host_as_spm(True, self.hsm_hosts[0],
                                           config.DATA_CENTER_NAME),
                        'Unable to set host %s as spm' % self.hsm_hosts[0])

        logger.info('Ensuring new host (%s) is spm', self.hsm_hosts[0])
        self.assertTrue(checkHostSpmStatus(True, self.hsm_hosts[0]))

    def tearDown(self):
        """
        Remove iptables block from original spm host and non-master storage
        """
        logger.info('Domain %s is blocked: %s', self.domain_to_block,
                    self.domain_blocked)
        for host in self.domain_blocked:
            logger.info('Unblocking connection between %s and %s',
                        host,
                        self.domain_to_block)
            assert unblockOutgoingConnection(host,
                                             config.HOST_USER,
                                             config.HOST_PASSWORD[0],
                                             self.domain_to_block)


class TestCase289887(ReassignSPMWithStorageBlocked):
    """
    TCMS Test Case 289887 - Resign SPM when host cannot see non-master domain
    """
    __test__ = True
    tcms_test_case = '289887'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_set_spm_with_blocked_nonmaster_domain(self):
        """
        * Block connection between spm and non-master domain
        * Set HSM host as SPM
        """
        self.domain_to_block = self.nonmaster_address
        self.hosts_to_block.append(self.spm_host)
        self.block_connection_and_reassign_spm()


class TestCase289888(ReassignSPMWithStorageBlocked):
    """
    TCMS Test Case 289888 - Resign SPM when host cannot see master domain
    """
    __test__ = True
    tcms_test_case = '289888'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    @bz('999493')
    def test_set_spm_with_blocked_nonmaster_domain(self):
        """
        * Block connection between spm and non-master domain
        * Set HSM host as SPM
        """
        self.domain_to_block = self.master_address
        self.hosts_to_block = config.HOSTS
        self.wait_for_dc_status = config.DATA_CENTER_PROBLEMATIC
        self.block_connection_and_reassign_spm()


class TestCase289890(DCUp):
    """
    TCMS Test Case 289890 - Reassign spm during storage domain deactivation
    """

    __test__ = True
    tcms_test_case = '289890'

    @classmethod
    def setup_class(cls):
        """
        deactivate non master domain
        """
        super(TestCase289890, cls).setup_class()
        logger.info('deactivating non-master domain %s', cls.nonmaster_domain)
        assert deactivateStorageDomain(True, config.DATA_CENTER_NAME,
                                       cls.nonmaster_domain)

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_reassign_spm_during_deactivate_domain(self):
        """
        Deactivate domain and select new spm during deactivate process
        """
        logger.info('Deactivating storage domain %s', self.master_domain)

        self.assertTrue(deactivateStorageDomain(True,
                                                config.DATA_CENTER_NAME,
                                                self.master_domain))

        logger.info('Trying to select host %s as new spm', self.hsm_hosts[0])
        self.assertTrue(select_host_as_spm(False, self.hsm_hosts[0],
                                           config.DATA_CENTER_NAME))

    @classmethod
    def teardown_class(cls):
        """
        Reactivate storage domain
        """
        for domain in (cls.master_domain, cls.nonmaster_domain):
            logger.info('Reactivating domain %s', domain)
            assert activateStorageDomain(True, config.DATA_CENTER_NAME,
                                         domain)
        super(TestCase289890, cls).teardown_class()
