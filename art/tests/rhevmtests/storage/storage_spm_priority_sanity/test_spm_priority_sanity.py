"""
Storage SPM priority sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_2_Storage_SPM_Priority
"""
import logging
import pytest
import config
import helpers
from art.core_api import apis_exceptions
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
import art.rhevm_api.utils.storage_api as st_api
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, StorageTest as BaseTestCase, testflow
from rhevmtests.storage.fixtures import (
    set_spm_priorities,
)
from rhevmtests.storage.storage_spm_priority_sanity.fixtures import (
    wait_for_spm, remove_host, deactivate_hsm_hosts, initialize_hosts_params,
    activate_old_master_domain, set_different_host_priorities
)
from utilities import utils


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
WAIT_FOR_SPM_TIMEOUT = 100
RETRY_INTERVAL = 10


@pytest.mark.usefixtures(
    wait_for_spm.__name__,
    set_spm_priorities.__name__
)
class BasicEnvironment(BaseTestCase):
    """
    Base class that ensures SPM is elected and SPM priorities
    are set to default for all hosts
    """
    storages = config.NOT_APPLICABLE

    def wait_for_spm_host_and_verify_identity(self, host_name):
        """
        Waits for an SPM host to be selected, check whether the SPM host
        matches the expected host_name

        :param host_name: Name of the host that should be the SPM host
        :type host_name: str
        :return: True if the SPM host matches the input host_name,
        False otherwise
        """
        logger.info("Waiting for SPM to be elected")
        if not ll_hosts.waitForSPM(
            config.DATA_CENTER_NAME, WAIT_FOR_SPM_TIMEOUT, RETRY_INTERVAL
        ):
            logger.error(
                "SPM host was not elected in %s", config.DATA_CENTER_NAME
            )
            return False

        self.spm_host = ll_hosts.getSPMHost(config.HOSTS)
        testflow.step("Verify SPM host is '%s'", host_name)
        if self.spm_host is not host_name:
            logger.info(
                "SPM host %s does not match the expected host %s",
                self.spm_host, host_name
            )
            return False

        return True

    def activate_and_verify_hosts(self, hosts=config.HOSTS):
        """
        Activate given hosts and verify they are in state 'up'

        :param hosts: List of hosts to activate
        :type hosts: list
        :raise: HostException
        """
        hosts_sorted_by_spm_priority = ll_hosts._sort_hosts_by_priority(hosts)

        for host in hosts_sorted_by_spm_priority:
            testflow.step("Activate host '%s'", host)
            assert ll_hosts.activate_host(True, host), (
                "Unable to activate host: %s " % host
            )
        assert ll_hosts.waitForHostsStates(True, hosts, config.HOST_UP), (
            "Hosts failed to activate"
        )

    def set_priorities(
        self, positive=True, priorities=None, hosts=config.HOSTS
    ):
        """
        Sets the SPM priorities on the input hosts

        :param positive: True if operation should succeded, False otherwise
        :param priorities: List of hosts for which SPM priorities should
        be configured
        :type priorities: list
        :param hosts: List of hosts for Setting new SPM priorities on
        :type hosts: list
        :raise: HostException
        """
        testflow.step(
            "Setting SPM priorities %s for hosts: %s", priorities, hosts
        )
        for host, priority in zip(hosts, priorities):
            assert ll_hosts.setSPMPriority(positive, host, priority), (
                "Unable to set host %s priority" % host
            )

        testflow.step(
            "Ensure that the SPM priority was configured on input hosts"
        )
        for host, priority in zip(hosts, priorities):
            assert ll_hosts.checkSPMPriority(positive, host, str(priority)), (
                "Unable to check host %s priority" % host
            )


class SPMHostsMinusOnePriorityFlow(BasicEnvironment):
    """
    Base class for minus one SPM hosts priority flow
    """
    __test__ = False

    def basic_flow(self, priorities, hosts=config.HOSTS):
        """
        Basic flow for minus one SPM hosts priority
        """
        self.set_priorities(priorities=priorities, hosts=hosts)
        helpers.deactivate_and_verify_hosts(hosts=hosts)
        self.activate_and_verify_hosts(hosts=hosts)

        testflow.step("Waiting for SPM to be elected")
        with pytest.raises(apis_exceptions.APITimeout):
            ll_hosts.waitForSPM(
                datacenter=config.DATA_CENTER_NAME,
                timeout=WAIT_FOR_SPM_TIMEOUT, sleep=RETRY_INTERVAL
            )


@pytest.mark.usefixtures(
    remove_host.__name__
)
class TestCase6220(BasicEnvironment):
    """
    RHEVM3-6220 - Default SPM priority value
    """
    __test__ = True
    polarion_test_case = '6220'

    @polarion("RHEVM3-6220")
    @attr(tier=2)
    def test_default_spm_priority(self):
        """
        * Remove host from the environment
        * Add the remove host back and check the default spm value
        Expected result: default value shuld be '5'
        """
        testflow.step("Add host %s back to the environment", self.removed_host)
        assert ll_hosts.add_host(
            name=self.removed_host, address=self.host_object.fqdn,
            wait=True, cluster=config.CLUSTER_NAME,
            root_password=config.HOSTS_PW
        ), "Failed to add host %s back to %s" % (
            self.removed_host, config.DATA_CENTER_NAME
        )

        testflow.step(
            "verify SPM priority of %s is equal to %s", self.removed_host,
            config.DEFAULT_SPM_PRIORITY
        )
        assert ll_hosts.getSPMPriority(self.removed_host) == (
            config.DEFAULT_SPM_PRIORITY
        ), "SPM priority of %s is not equal to %s" % (
            self.removed_host, config.DEFAULT_SPM_PRIORITY
        )


class TestCase6212(BasicEnvironment):
    """
    RHEVM3-6212 - Legal values range validation
    RHEVM3-6213 - Illegal values range validation
    RHEVM3-6209 - Illegal SPM Priority values
    """
    __test__ = True

    @polarion("RHEVM3-6212")
    @attr(tier=2)
    def test_legal_value_range_validation(self):
        """
        * Change and validate SPM priority to '-1, 10'
        Expected result: All changes should occur
        """
        valid_priorities = [
            config.MIN_SPM_PRIORITY, config.MAX_SPM_PRIORITY
        ]
        self.set_priorities(
            priorities=valid_priorities, hosts=self.hsm_hosts[:2]
        )

    @polarion("RHEVM3-6213")
    @attr(tier=2)
    def test_illegal_value_range_validation(self):
        """
        * Change and validate SPM priority to '-2, 11'
        Expected result: Illegal values changes shouldn't occur, SPM priority
        should stay as it was (5)
        """
        testflow.step(
            "Set host: '%s' SPM priority to '%s'", self.hsm_hosts[0],
            config.BELOW_MIN_SPM_PRIORITY
        )
        assert ll_hosts.setSPMPriority(
            False, self.hsm_hosts[0], config.BELOW_MIN_SPM_PRIORITY
        ), "Set SPM priority to illegal value succeded"
        assert ll_hosts.checkSPMPriority(
            True, self.hsm_hosts[0], str(config.DEFAULT_SPM_PRIORITY)
        ), "Host %s SPM priority isn't %s" % (
            (self.hsm_hosts[0], config.DEFAULT_SPM_PRIORITY)
        )
        testflow.step(
            "Set host: '%s' SPM priority to '%s'", self.hsm_hosts[0],
            config.LARGER_THAN_MAX_SPM_PRIORITY
        )
        assert ll_hosts.setSPMPriority(
            False, self.hsm_hosts[0], config.LARGER_THAN_MAX_SPM_PRIORITY
        ), "Set SPM priority to illegal value succeded"
        assert ll_hosts.checkSPMPriority(
            True, self.hsm_hosts[0], str(config.DEFAULT_SPM_PRIORITY)
        ), "Host %s SPM priority isn't %s" % (
            self.hsm_hosts[0], config.DEFAULT_SPM_PRIORITY
        )

    @polarion("RHEVM3-6209")
    @attr(tier=2)
    def test_illegal_spm_priority_value(self):
        """
        * Change and validate SPM priority to '#'
        Expected result: Illegal values changes shouldn't occur
        """
        testflow.step(
            "Set host: '%s' SPM priority to '%s'", self.hsm_hosts[0],
            config.ILLEGAL_SPM_PRIORITY
        )
        assert ll_hosts.setSPMPriority(
            False, self.hsm_hosts[0], config.ILLEGAL_SPM_PRIORITY
        ), "Set SPM priority to illegal value succeded"


class TestCase6217(SPMHostsMinusOnePriorityFlow):
    """
    RHEVM3-6217 - All hosts with '-1' priority
    """
    __test__ = True
    polarion_test_case = '6217'

    @polarion("RHEVM3-6217")
    @attr(tier=2)
    def test_all_hosts_with_minus_one_spm_priority(self):
        """
        * Set all host's SPM priority to '-1'
        * Switch all hosts to maintenance
        * Activate all hosts
        Expected result: No host was selected as SPM
        """
        min_priorities = ([config.MIN_SPM_PRIORITY] * len(config.HOSTS))
        self.basic_flow(priorities=min_priorities)


@pytest.mark.usefixtures(
    deactivate_hsm_hosts.__name__
)
class TestCase6205(SPMHostsMinusOnePriorityFlow):
    """
    RHEVM3-6205 - Host that has priority -1 is not chosen,
    even if it is the only host
    """
    __test__ = True
    polarion_test_case = '6205'

    @polarion("RHEVM3-6205")
    @attr(tier=2)
    def test_all_hosts_with_minus_one_spm_priority(self):
        """
        * Switch all host except the SPM host to maintenance
        * Set SPM host SPM priority to '-1'
        * Switch SPM host to maintenance
        * Activate SPM host
        * Restart SPM vdsm daemon
        Expected result: No host was selected as SPM
        """
        min_priorities = [config.MIN_SPM_PRIORITY]
        self.basic_flow(priorities=min_priorities, hosts=[self.spm_host])

        testflow.step("Restarting vdsmd on %s", self.spm_host)
        spm_host_ip = ll_hosts.getHostIP(self.spm_host)
        test_utils.restartVdsmd(spm_host_ip, config.HOSTS_PW)
        assert ll_hosts.waitForHostsStates(
            True, self.spm_host, config.HOST_UP
        ), "Host %s failed to reach 'UP' state" % self.spm_host

        testflow.step("Waiting for SPM to be elected")
        with pytest.raises(apis_exceptions.APITimeout):
            ll_hosts.waitForSPM(
                datacenter=config.DATA_CENTER_NAME,
                timeout=WAIT_FOR_SPM_TIMEOUT, sleep=RETRY_INTERVAL
            )


@pytest.mark.usefixtures(
    initialize_hosts_params.__name__
)
class TestCase6206(BasicEnvironment):
    """
    RHEVM3-6206 - Two hosts swap their priorities, the SPM changes accordingly
    """
    __test__ = True
    polarion_test_case = '6206'

    def basic_flow(self):
        """
        Deactivate Hosts, set new priorities, activate hosts and wait for SPM
        """
        helpers.deactivate_and_verify_hosts()
        self.set_priorities(priorities=self.priorities, hosts=self.hosts)
        self.activate_and_verify_hosts(hosts=self.hosts)
        assert self.wait_for_spm_host_and_verify_identity(
            self.high_spm_priority_host
        ), "%s selected as SPM and not %s" % (
            self.spm_host, self.high_spm_priority_host
        )

    @polarion("RHEVM3-6206")
    @attr(tier=2)
    def test_two_hosts_swap_priorities(self):
        """
        * Set all hosts to maintenance
        * Set one host priority to 5 and other to 4
        * Activate the two hosts and verify that the higher SPM priority host
        is selected as SPM
        * Switch the SPM priority of the two hosts
        * Put the two hosts on maintenance
        * Activate the two hosts and verify that the higher SPM priority host
        is selected as SPM
        Expected result: The host with the higher SPM priority is
        selected each time
        """
        self.basic_flow()
        testflow.step(
            "Swapping SPM priorities between host %s and %s",
            self.high_spm_priority_host, self.low_spm_priority_host
        )
        self.high_spm_priority_host, self.low_spm_priority_host = (
            self.low_spm_priority_host, self.high_spm_priority_host
        )
        self.hosts = [self.high_spm_priority_host, self.low_spm_priority_host]
        self.basic_flow()


@pytest.mark.usefixtures(
    set_different_host_priorities.__name__
)
class TestCase6224(BasicEnvironment):
    """
    RHEVM3-6224 - Restart/Stop VDSM
    """
    __test__ = True
    polarion_test_case = '6224'

    def basic_flow(self, host_name, priority):
        """
        Change SPM priority in the DB and restart VDSM

        :param host_name: Host to change his SPM priority on the DB
        :type host_name: str
        :param priority: New SPM priority
        :type priority: int
        :raise: HostException
        """
        helpers.deactivate_and_verify_hosts(hosts=[host_name])
        testflow.step(
            "Change SPM priority to %s in the DB to %s", host_name, priority
        )
        assert ll_hosts.set_spm_priority_in_db(
            host_name=host_name, spm_priority=priority,
            engine=config.ENGINE
        ), "Failed to change SPM priority on the DB for host '%s'" % (
            self.spm_host
        )
        testflow.step("Restarting vdsmd on %s", host_name)
        host_ip = ll_hosts.getHostIP(host_name)
        test_utils.restartVdsmd(host_ip, config.HOSTS_PW)
        self.activate_and_verify_hosts(hosts=[host_name])

    @polarion("RHEVM3-6224")
    @attr(tier=2)
    def test_restart_stop_vdsm(self):
        """
        * Set HSM hosts with '-1' SPM priority, and the SPM host with '2'
        * Update DB so current SPM host SPM priority is set with '-1'
        * Restart SPM VDSM
        * Update the DB and change the value of HSM host to 2
        * Restart HSM VDSM
        Expected result: After first VDSM restart, policy is NOT ignored and
        NO SPM was elected.
        After restarting VDSM for the second time the host with higher value
        is elected as SPM
        """
        self.basic_flow(
            host_name=self.spm_host, priority=config.MIN_SPM_PRIORITY
        )
        testflow.step("Waiting for SPM to be elected")
        with pytest.raises(apis_exceptions.APITimeout):
            ll_hosts.waitForSPM(
                datacenter=config.DATA_CENTER_NAME,
                timeout=WAIT_FOR_SPM_TIMEOUT, sleep=RETRY_INTERVAL
            )
        self.basic_flow(host_name=self.hsm_hosts[0], priority=2)
        assert self.wait_for_spm_host_and_verify_identity(self.hsm_hosts[0]), (
            "%s selected as SPM and not %s" %
            (self.spm_host, self.hsm_hosts[0])
        )


@pytest.mark.usefixtures(
    activate_old_master_domain.__name__
)
class TestCase6222(BasicEnvironment):
    """
    RHEVM3-6222 - Migrate Master Storage Domain (negative test)
    """
    __test__ = True
    polarion_test_case = '6222'

    @polarion("RHEVM3-6222")
    @attr(tier=2)
    def test_migrate_master_storage_domain(self):
        """
        * Switch Master domain to maintenance
        Expected result: SPM host doesn't change
        """
        former_spm = self.spm_host
        testflow.step("Deactivate master storage domain")
        assert ll_sd.deactivate_master_storage_domain(
            True, config.DATA_CENTER_NAME
        ), "Failed to deactivate master storage domain"
        status, master_domain_obj = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        assert status, "Master storage domain was not found"
        status = self.wait_for_spm_host_and_verify_identity(
            former_spm
        )
        assert status, "%s selected as SPM and not %s" % (
            self.spm_host, self.hsm_hosts[0]
        )


class TestCase6221(BasicEnvironment):
    """
    RHEVM3-6221 - Change the SPM priority value in the DB (negative test)
    """
    __test__ = True
    polarion_test_case = '6221'

    @polarion("RHEVM3-6221")
    @attr(tier=2)
    def test_db_illegal_spm_priority_value(self):
        """
        * Set illegal SPM priority on the DB (-2, 11)
        Expected result: DB blocks values higher than 10
        and lower than -1
        """
        testflow.step(
            "Change SPM priority to %s in the DB to %s", self.spm_host,
            config.LARGER_THAN_MAX_SPM_PRIORITY
        )
        assert not ll_hosts.set_spm_priority_in_db(
            host_name=self.spm_host,
            spm_priority=config.LARGER_THAN_MAX_SPM_PRIORITY,
            engine=config.ENGINE
        ), "SPM priority on the DB for host '%s' changed to '%s'" % (
            self.spm_host, config.MIN_SPM_PRIORITY + 1
        )
        testflow.step(
            "Change SPM priority to %s in the DB to %s", self.spm_host,
            config.BELOW_MIN_SPM_PRIORITY
        )
        assert not ll_hosts.set_spm_priority_in_db(
            host_name=self.spm_host,
            spm_priority=config.BELOW_MIN_SPM_PRIORITY,
            engine=config.ENGINE
        ), "SPM priority on the DB for host '%s' changed to '%s'" % (
            self.spm_host, config.MIN_SPM_PRIORITY + 1
        )


class TestCase6215(BasicEnvironment):
    """
    RHEVM3-6215 - Host with higher SPM Priority not responding
    """
    # TODO: Cannot block the connection between the engine and host due to
    # the fact that art code runs on the engine (when using GE)

    __test__ = False
    former_spm = None
    polarion_test_case = '6215'

    def setUp(self):
        """
        Set different SPM priorities to each host
        """
        super(TestCase6215, self).setUp()
        new_priority = range(1, len(self.hsm_hosts) + 1)
        self.set_priorities(priorities=new_priority, hosts=self.hsm_hosts)

        self.second_spm_priority_host = self.hsm_hosts[1]
        self.max_spm_priority_host = self.hsm_hosts[2]
        self.max_spm_priority_host_ip = ll_hosts.getHostIP(
            self.max_spm_priority_host
        )
        self.engine_ip = utils.getIpAddressByHostName(config.VDC)
        logger.info(
            "Host '%s' has the highest SPM priority and next is %s",
            self.max_spm_priority_host, self.second_spm_priority_host
        )

    @polarion("RHEVM3-6215")
    @attr(tier=4)
    def test_highest_spm_priority_host_non_responsive(self):
        """
        * Set different SPM priority to each host
        * Deactivate SPM host
        * Block connection between engine to the highest priority host
        Expected result: HSM with the next highest SPM priority is selected
        as SPM
        """
        helpers.deactivate_and_verify_hosts(hosts=[self.spm_host])
        logger.info(
            "Blocking connection between %s and %s", self.engine_ip,
            self.max_spm_priority_host
        )
        self.former_spm = self.spm_host
        assert st_api.blockOutgoingConnection(
            self.max_spm_priority_host_ip, config.HOSTS_USER,
            config.HOSTS_PW, self.engine_ip
        ), "Unable to block connection between %s and %s" % (
            self.max_spm_priority_host_ip, self.engine_ip
        )
        self.wait_for_spm_host_and_verify_identity(
            self.second_spm_priority_host
        )

    def tearDown(self):
        """
        Unblock connection between the engine and the host and
        activate the former SPM host
        """
        logger.info(
            "Unblock connection between %s and %s", self.max_spm_priority_host,
            self.engine_ip
        )
        if not st_api.unblockOutgoingConnection(
            self.max_spm_priority_host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.engine_ip
        ):
            logger.error(
                "Failed to unblock connection between %s and %s",
                self.max_spm_priority_host, self.engine_ip
            )
            BaseTestCase.test_failed = True
        if not ll_hosts.waitForHostsStates(True, self.max_spm_priority_host):
            logger.error(
                "Host failed to reach 'UP' state %s",
                self.max_spm_priority_host
            )
            BaseTestCase.test_failed = True
        if not ll_hosts.activate_host(True, self.former_spm):
            logger.error(
                "Failed to activate host '%s'", self.former_spm
            )
            BaseTestCase.test_failed = True
        if not ll_hosts.waitForHostsStates(True, self.former_spm):
            logger.error(
                "Host failed to reach 'UP' state %s", self.former_spm
            )
            BaseTestCase.test_failed = True
        super(TestCase6215, self).tearDown()


class TestCase6219(BasicEnvironment):
    """
    RHEVM3-6219 - Storage disconnection and SPM re-election
    """
    __test__ = True
    polarion_test_case = '6219'
    former_spm = None

    def setUp(self):
        """
        Set HSM hosts SPM priority to '-1' and SPM host SPM priority to '10'
        """
        super(TestCase6219, self).setUp()
        minus_one_priorities = (
            [config.MIN_SPM_PRIORITY] * len(self.hsm_hosts)
        )
        self.set_priorities(
            priorities=minus_one_priorities, hosts=self.hsm_hosts
        )
        self.set_priorities(
            priorities=[config.MAX_SPM_PRIORITY], hosts=[self.spm_host]
        )
        self.spm_host_ip = ll_hosts.getHostIP(
            self.spm_host
        )

        logger.info(
            "Search non-master storage domain to block on the SPM host"
        )
        found, non_master_obj = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME,
        )
        assert found, "Failed to find non-master storage domain"
        non_master = non_master_obj['nonMasterDomains'][0]
        rc, non_master_domain = ll_sd.getDomainAddress(
            True, non_master
        )
        assert rc, "Could not get the address of '%s'" % non_master
        self.non_master_storage_domain_ip = non_master_domain['address']

    @polarion("RHEVM3-6219")
    @attr(tier=4)
    def test_storage_disconnection_and_spm_reelection(self):
        """
        * Set HSM hosts SPM priorities to '-1' and SPM host
        SPM priority to '10'
        * Kill connection to storage domain on SPM host
        * Set HSM host with valid SPM priority
        Expected result: HSM host with valid SPM priority should become SPM
        """
        logger.info(
            "Blocking connection between %s and %s", self.spm_host,
            self.non_master_storage_domain_ip
        )
        self.former_spm = self.spm_host
        assert st_api.blockOutgoingConnection(
            self.spm_host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.non_master_storage_domain_ip
        ), "Unable to block connection between %s and %s" % (
            self.spm_host, self.non_master_storage_domain_ip
        )
        assert ll_hosts.waitForHostsStates(
            True, self.spm_host, states=config.HOST_NONOPERATIONAL
        ), "Host %s failed to reach non-operational state" % self.spm_host
        self.set_priorities(
            priorities=[config.DEFAULT_SPM_PRIORITY], hosts=[self.hsm_hosts[0]]
        )
        self.wait_for_spm_host_and_verify_identity(self.hsm_hosts[0])

    def tearDown(self):
        """
        Unblock connection between the former SPM and the storage domain
        """
        logger.info(
            "Unblock connection between %s and %s", self.former_spm,
            self.non_master_storage_domain_ip
        )
        if not st_api.unblockOutgoingConnection(
            self.spm_host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.non_master_storage_domain_ip
        ):
            logger.error(
                "Failed to unblock connection between %s and %s",
                self.former_spm, self.non_master_storage_domain_ip
            )
            BaseTestCase.test_failed = True
        if not ll_hosts.waitForHostsStates(True, self.former_spm):
            logger.error(
                "Host failed to reach 'UP' state %s", self.former_spm
            )
            BaseTestCase.test_failed = True
        super(TestCase6219, self).tearDown()
