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
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier4,
    storages,
)
from art.unittest_lib import StorageTest as BaseTestCase, testflow
from rhevmtests.storage.fixtures import (
    set_spm_priorities, unblock_connectivity_storage_domain_teardown,
)
from rhevmtests.storage.storage_spm_priority_sanity.fixtures import (
    wait_for_spm, remove_host, deactivate_hsm_hosts, initialize_hosts_params,
    activate_old_master_domain, set_different_host_priorities,
    check_hosts_status, init_host_and_sd_params, init_params_for_unblock,
)
from utilities import utils


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
WAIT_FOR_SPM_TIMEOUT = 100
RETRY_INTERVAL = 10


@storages((config.NOT_APPLICABLE,))
@pytest.mark.usefixtures(
    wait_for_spm.__name__,
    set_spm_priorities.__name__
)
class BasicEnvironment(BaseTestCase):
    """
    Base class that ensures SPM is elected and SPM priorities
    are set to default for all hosts
    """

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
        if not ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, WAIT_FOR_SPM_TIMEOUT, RETRY_INTERVAL
        ):
            logger.error(
                "SPM host was not elected in %s", config.DATA_CENTER_NAME
            )
            return False

        self.spm_host = ll_hosts.get_spm_host(config.HOSTS)
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
        hosts_sorted_by_spm_priority = ll_hosts.sort_hosts_by_priority(hosts)

        for host in hosts_sorted_by_spm_priority:
            testflow.step("Activate host '%s'", host)
            assert ll_hosts.activate_host(True, host), (
                "Unable to activate host: %s " % host
            )
        assert ll_hosts.wait_for_hosts_states(True, hosts, config.HOST_UP), (
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
            assert ll_hosts.set_spm_priority(positive, host, priority), (
                "Unable to set host %s priority" % host
            )

        testflow.step(
            "Ensure that the SPM priority was configured on input hosts"
        )
        for host, priority in zip(hosts, priorities):
            assert ll_hosts.check_spm_priority(
                positive, host, str(priority)), (
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
            ll_hosts.wait_for_spm(
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
    @tier2
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
        assert ll_hosts.get_spm_priority(self.removed_host) == (
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
    @tier2
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
    @tier2
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
        assert ll_hosts.set_spm_priority(
            False, self.hsm_hosts[0], config.BELOW_MIN_SPM_PRIORITY
        ), "Set SPM priority to illegal value succeded"
        assert ll_hosts.check_spm_priority(
            True, self.hsm_hosts[0], str(config.DEFAULT_SPM_PRIORITY)
        ), "Host %s SPM priority isn't %s" % (
            (self.hsm_hosts[0], config.DEFAULT_SPM_PRIORITY)
        )
        testflow.step(
            "Set host: '%s' SPM priority to '%s'", self.hsm_hosts[0],
            config.LARGER_THAN_MAX_SPM_PRIORITY
        )
        assert ll_hosts.set_spm_priority(
            False, self.hsm_hosts[0], config.LARGER_THAN_MAX_SPM_PRIORITY
        ), "Set SPM priority to illegal value succeded"
        assert ll_hosts.check_spm_priority(
            True, self.hsm_hosts[0], str(config.DEFAULT_SPM_PRIORITY)
        ), "Host %s SPM priority isn't %s" % (
            self.hsm_hosts[0], config.DEFAULT_SPM_PRIORITY
        )

    @polarion("RHEVM3-6209")
    @tier2
    def test_illegal_spm_priority_value(self):
        """
        * Change and validate SPM priority to '#'
        Expected result: Illegal values changes shouldn't occur
        """
        testflow.step(
            "Set host: '%s' SPM priority to '%s'", self.hsm_hosts[0],
            config.ILLEGAL_SPM_PRIORITY
        )
        assert ll_hosts.set_spm_priority(
            False, self.hsm_hosts[0], config.ILLEGAL_SPM_PRIORITY
        ), "Set SPM priority to illegal value succeded"


@pytest.mark.usefixtures(
    check_hosts_status.__name__
)
class TestCase6217(SPMHostsMinusOnePriorityFlow):
    """
    RHEVM3-6217 - All hosts with '-1' priority
    """
    __test__ = True
    polarion_test_case = '6217'

    @polarion("RHEVM3-6217")
    @tier2
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
    @tier2
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
        spm_host_ip = ll_hosts.get_host_ip(self.spm_host)
        test_utils.restartVdsmd(spm_host_ip, config.HOSTS_PW)
        assert ll_hosts.wait_for_hosts_states(
            True, self.spm_host, config.HOST_UP
        ), "Host %s failed to reach 'UP' state" % self.spm_host

        testflow.step("Waiting for SPM to be elected")
        with pytest.raises(apis_exceptions.APITimeout):
            ll_hosts.wait_for_spm(
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
    @tier2
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
        host_ip = ll_hosts.get_host_ip(host_name)
        test_utils.restartVdsmd(host_ip, config.HOSTS_PW)
        self.activate_and_verify_hosts(hosts=[host_name])

    @polarion("RHEVM3-6224")
    @tier2
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
            ll_hosts.wait_for_spm(
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
    @tier2
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
    @tier2
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
        status = False
        try:
            ll_hosts.set_spm_priority_in_db(
                host_name=self.spm_host,
                spm_priority=config.LARGER_THAN_MAX_SPM_PRIORITY,
                engine=config.ENGINE
            ), "SPM priority on the DB for host '%s' changed to '%s'" % (
                self.spm_host, config.LARGER_THAN_MAX_SPM_PRIORITY
            )
        # Exception is raised from engine.db.psql in rrmngmt
        except Exception:
            status = True
        assert status, (
            "SPM priority on the DB for host '%s' changed to '%s'" % (
                self.spm_host, config.MIN_SPM_PRIORITY + 1
            )
        )
        testflow.step(
            "Change SPM priority to %s in the DB to %s", self.spm_host,
            config.BELOW_MIN_SPM_PRIORITY
        )
        status = False
        try:
            ll_hosts.set_spm_priority_in_db(
                host_name=self.spm_host,
                spm_priority=config.BELOW_MIN_SPM_PRIORITY,
                engine=config.ENGINE
            )
        except Exception:
            status = True
        assert status, (
            "SPM priority on the DB for host '%s' changed to '%s'" % (
                self.spm_host, config.BELOW_MIN_SPM_PRIORITY
            )
        )


@pytest.mark.usefixtures(
    initialize_hosts_params.__name__,
    init_params_for_unblock.__name__,
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

    @polarion("RHEVM3-6215")
    @tier4
    def test_highest_spm_priority_host_non_responsive(self):
        """
        * Set different SPM priority to each host
        * Deactivate SPM host
        * Block connection between engine to the highest priority host
        Expected result: HSM with the next highest SPM priority is selected
        as SPM
        """
        self.engine_ip = utils.getIpAddressByHostName(config.VDC)
        new_priority = range(1, len(self.hsm_hosts) + 1)
        self.set_priorities(priorities=new_priority, hosts=self.hsm_hosts)
        helpers.deactivate_and_verify_hosts(hosts=[self.spm_host])
        logger.info(
            "Blocking connection between %s and %s", self.engine_ip,
            self.high_spm_priority_host
        )
        self.former_spm = self.spm_host
        assert storage_helpers.blockOutgoingConnection(
            self.high_spm_priority_host, config.HOSTS_USER,
            config.HOSTS_PW, self.engine_ip
        ), "Unable to block connection between %s and %s" % (
            self.high_spm_priority_host, self.engine_ip
        )
        self.wait_for_spm_host_and_verify_identity(
            self.low_spm_priority_host
        )


@pytest.mark.usefixtures(
    init_host_and_sd_params.__name__,
    check_hosts_status.__name__,
    unblock_connectivity_storage_domain_teardown.__name__,
)
class TestCase6219(BasicEnvironment):
    """
    RHEVM3-6219 - Storage disconnection and SPM re-election
    """
    __test__ = True
    polarion_test_case = '6219'
    former_spm = None
    spm_priority = config.MAX_SPM_PRIORITY
    block_spm_host = True

    @polarion("RHEVM3-6219")
    @tier4
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
            self.storage_domain_ip
        )
        self.former_spm = self.spm_host
        assert storage_helpers.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        ), "Unable to block connection between %s and %s" % (
            self.spm_host, self.non_master
        )
        assert ll_hosts.wait_for_hosts_states(
            True, self.spm_host, states=config.HOST_NONOPERATIONAL
        ), "Host %s failed to reach non-operational state" % self.spm_host
        self.set_priorities(
            priorities=[config.DEFAULT_SPM_PRIORITY], hosts=[self.hsm_hosts[0]]
        )
        self.wait_for_spm_host_and_verify_identity(self.hsm_hosts[0])
