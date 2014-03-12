"""
Storage SPM priority sanity test - 5299
https://tcms.engineering.redhat.com/plan/5299/
"""

import logging
import time
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.tests_lib.high_level import hosts as hosts
from art.rhevm_api.tests_lib.low_level import datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.rhevm_api.utils.test_utils import get_api, toggleServiceOnHost,\
    raise_if_false

from art.test_handler.settings import opts
from art.test_handler.tools import tcms, bz
from art.test_handler import exceptions
from art.test_handler.handler_lib.utils import no_datatype_validation
from art.unittest_lib.common import is_bz_state
from art.rhevm_api.utils.storage_api import blockOutgoingConnection, \
    unblockOutgoingConnection

import config


LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']
HOST_API = get_api('host', 'hosts')

BZ986961_NOT_FIXED = not is_bz_state('986961')

TCMS_PLAN_ID = '5299'
TMP_CLUSTER = "Default"
SPM_TIMEOUT = 300
POLLING_INTERVAL = 10
DEFAULT_SPM_PRIORITY = '5'
SLEEP_AMOUNT = 600


def set_spm_priority_in_db(positive, host, priority):
    """
    Changes spm priority value in DB for the host
    """

    assert ll_hosts.setSPMPriorityInDB(
        positive, hostName=host, spm_priority=priority,
        ip=config.DB_HOST, user=config.DB_HOST_USER,
        password=config.DB_HOST_PASSWORD, db_user=config.DB_USER)


def restart_vdsm(host_index):
    """
    Restarts vdsm on the host given by index
    """
    assert toggleServiceOnHost(
        True, host=config.HOSTS[host_index], user='root',
        password=config.HOSTS_PWD[host_index], service='vdsmd',
        action='restart')


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_plan_id = TCMS_PLAN_ID
    tcms_test_case = "-1"
    STRING_HOSTS = ",".join(config.HOSTS)

    @classmethod
    def _set_priorities(cls):
        """
        Sets priorities to hosts
        """
        priorities = config.PARAMETERS.as_list('spms_%s' % cls.tcms_test_case)
        res = list()
        for pri, host in zip(priorities, config.HOSTS):
            LOGGER.debug("Setting SPM priority of host %s to %s", host, pri)
            res.append(ll_hosts.setSPMPriority(True, host, pri))
        raise_if_false(
            res, config.HOSTS, "Setting SPM priority failed on hosts %s",
            exceptions.HostException)

    def _check_host_for_spm(self, host):
        """
        Tests that host is spm
        """
        ll_hosts.waitForSPM(config.DC_NAME, SPM_TIMEOUT, POLLING_INTERVAL)
        LOGGER.info("Ensuring host %s is SPM", host)
        if not ll_hosts.checkHostSpmStatus(True, host):
            raise exceptions.HostException("Host %s is not an "
                                           "SPM but should be" % host)

    def _maintenance_and_wait_for_dc(self, host):
        """
        Maintenance given host and waits until DC is up
        """
        LOGGER.info("Deactivating host %s", host)
        assert hosts.deactivate_host_if_up(host)
        LOGGER.debug("Waiting until DC is up")
        assert datacenters.waitForDataCenterState(config.DC_NAME) or \
            BZ986961_NOT_FIXED
        # WA BZ#986961
        if BZ986961_NOT_FIXED:
            LOGGER.info("Due to BZ#986961 waiting until one of hosts is "
                        "selected as SPM")
            assert ll_hosts.waitForSPM(config.DC_NAME, 600, POLLING_INTERVAL)

    def _maintenance_and_activate_all_hosts(self):
        # Deactivate all hosts
        LOGGER.debug("Deactivating all hosts")
        assert hosts.deactivate_hosts_if_up(config.HOSTS)

        # Activate all hosts
        LOGGER.debug("Activating all hosts")
        assert ll_hosts.activateHosts(True, config.HOSTS)

        # Wait for a spm to be chosen
        assert datacenters.waitForDataCenterState(config.DC_NAME) or \
            BZ986961_NOT_FIXED

    def _get_new_spm(self, spm, expected):
        """
        Puts current spm to maintenance and checks whether expected is new SPM
        Then moves former spm back to up status
        """
        self._maintenance_and_wait_for_dc(spm)
        self._check_host_for_spm(expected)
        assert ll_hosts.activateHost(True, spm)

    @classmethod
    def setup_class(cls):
        """
        Sets priorities, prepares dc with one host activated
        """
        cls._set_priorities()
        LOGGER.debug("Waiting for SPM")
        assert ll_hosts.waitForSPM(config.DC_NAME,
                                   SPM_TIMEOUT,
                                   POLLING_INTERVAL)

        spm_host = ll_hosts.getSPMHost(config.HOSTS)
        LOGGER.debug("SPM is %s", spm_host)
        LOGGER.debug("Deactivating hosts %s", config.HOSTS)
        assert hosts.deactivate_hosts_if_up(cls.STRING_HOSTS)


class AllHostsUp(BaseTestCase):
    """
    Gets all hosts to up status
    """

    @classmethod
    def setup_class(cls):
        """
        Move all hosts to up status
        """
        super(AllHostsUp, cls).setup_class()
        cls._move_all_hosts_up_from_maintenance()

    @classmethod
    def teardown_class(cls):
        """
        Moves all maintenanced hosts to up status
        """
        cls._move_all_hosts_up_from_maintenance()

    def _check_no_spm(self):
        """
        Checks there was no SPM selected
        """
        LOGGER.info("Sleeping for %d seconds in order to make sure no SPM was"
                    " selected", SLEEP_AMOUNT)
        time.sleep(SLEEP_AMOUNT)
        self.assertTrue(ll_hosts.checkSPMPresence(False, self.STRING_HOSTS))
        LOGGER.info("No SPM was selected, that's correct")

    @classmethod
    def _move_all_hosts_up_from_maintenance(cls):
        """
        Moves all maintenannced hosts to up status
        """
        for host_name in config.HOSTS:
            host_obj = HOST_API.find(host_name)
            if host_obj.get_status().get_state() == \
                    ENUMS['host_state_maintenance']:
                if not ll_hosts.activateHost(True, host_name):
                    raise exceptions.HostException("Failed to activate "
                                                   "host %s" % host_name)


class DCUp(AllHostsUp):
    """
    All hosts and DC are up
    """

    @classmethod
    def setup_class(cls):
        super(DCUp, cls).setup_class()
        assert ll_hosts.waitForSPM(config.DC_NAME,
                                   SPM_TIMEOUT,
                                   POLLING_INTERVAL)


class TwoHostsAndOneWithHigherPriority(AllHostsUp):
    """
    Setup with 3 hosts -
    Two hosts with same spm priority and one host is higher

    https://tcms.engineering.redhat.com/case/136167

    In this the behaviour must be as in the test when all hosts have different
    SPM value.
    The host with the highest value always chosen to be SPM host.
    """
    __test__ = True
    tcms_test_case = '136167'
    number_of_iterations = 3

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Ensure that host with highest priority is always chosen as SPM
        """
        for _ in range(self.number_of_iterations):
            self._maintenance_and_activate_all_hosts()
            self._check_host_for_spm(config.HOSTS[2])


class SPMPriorityMinusOne(AllHostsUp):
    """
    All hosts with '-1' priority - no SPM should be elected

    https://tcms.engineering.redhat.com/case/136169/
    """
    __test__ = True
    tcms_test_case = '136169'

    @classmethod
    def setup_class(cls):
        """
        overriding the AllHostsUp setup_class because there is a call to
        super(AllHostsUp, cls).setup_class() which call to hosts.waitForSPM.
        this method will cause a TimeOut
        """
        cls._set_priorities()
        LOGGER.debug("Deactivating hosts %s", config.HOSTS)
        assert hosts.deactivate_hosts_if_up(cls.STRING_HOSTS)
        if not ll_hosts.activateHosts(True, config.HOSTS):
            raise exceptions.HostException("Failed to activate hosts")

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Ensure that hosts with -1 value as spm priority won't be selected as
        SPM
        """
        self._check_no_spm()

    @classmethod
    def teardown_class(cls):
        """
        Set some SPM in order to clean up
        """
        assert ll_hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        assert datacenters.waitForDataCenterState(config.DC_NAME)
        super(SPMPriorityMinusOne, cls).teardown_class()


class SeveralHosts(DCUp):
    """
    Several hosts with different SPM priority

    https://tcms.engineering.redhat.com/case/136171/
    """
    __test__ = True
    tcms_test_case = '136171'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        SPM host is always the host with the highest SPM Priority value.
        """
        self._get_new_spm(config.HOSTS[0], config.HOSTS[2])
        self._get_new_spm(config.HOSTS[2], config.HOSTS[1])
        self._get_new_spm(config.HOSTS[1], config.HOSTS[2])


class PriorityOutOfRange(SPMPriorityMinusOne):
    """
    Change the SPM priority value in the DataBase (negative test)

    https://tcms.engineering.redhat.com/case/136454
    """
    __test__ = True
    tcms_test_case = '136454'
    host = config.HOSTS[0]

    @classmethod
    def setup_class(cls):
        """
        Do nothing
        """
        pass

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Test edge values
        """
        for value in (
                config.MAX_VALUE, config.MAX_VALUE - 1, config.MIN_VALUE,
                config.MIN_VALUE + 1):
            set_spm_priority_in_db(True, self.host, value)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority_greater_than_range(self):
        """
        Test that greater value than defined maximum cannot be set even in
        database
        """
        set_spm_priority_in_db(False, self.host, config.MAX_VALUE + 1)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority_lesser_than_range(self):
        """
        Test that lesser value than defined minimum cannot be set even in
        database
        """
        set_spm_priority_in_db(False, self.host, config.MIN_VALUE - 1)


class ADefaultSPMPriority(BaseTestCase):
    """
    Default SPM priority value

    https://tcms.engineering.redhat.com/case/136449/
    """
    __test__ = True
    tcms_test_case = '136449'

    @classmethod
    def setup_class(cls):
        """
        Don't do anything
        """
        pass

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Check that all hosts have default priority 5
        """
        priorities = list()
        for host in config.HOSTS:
            priorities.append(ll_hosts.checkSPMPriority(True, host, '5'))
        raise_if_false(
            priorities, config.HOSTS, "Hosts %s doesn't have default priority",
            exceptions.HostException)


class RandomSelection(DCUp):
    """
    Random SPM selection when all hosts have the same priority

    https://tcms.engineering.redhat.com/case/136466/
    """
    __test__ = True
    tcms_test_case = '136466'
    iteration_number = 5

    def _select_new_spm(self):
        """
        Moves old SPM to maintenance, waits for new SPM and checks that
        new SPM is the same as before. All hosts should have the same SPM
        priority
        """
        former_spm = ll_hosts._getSPMHostname(config.HOSTS)
        self._maintenance_and_wait_for_dc(former_spm)
        assert ll_hosts.activateHost(True, former_spm)
        assert ll_hosts.waitForSPM(config.DC_NAME,
                                   SPM_TIMEOUT,
                                   POLLING_INTERVAL)
        new_spm = ll_hosts._getSPMHostname(config.HOSTS)
        self.assertTrue(
            former_spm != new_spm,
            "Selected the same SPM - former spm: %s, current spm: %s" %
            (former_spm, new_spm))

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Test several times that new SPM is selected each time former SPM is
        moved to maintenance
        """
        for _ in range(self.iteration_number):
            self._select_new_spm()


class RestartVdsm(DCUp):
    """
    Restart/Stop VDSM

    https://tcms.engineering.redhat.com/case/136468/
    """
    __test__ = True
    tcms_test_case = '136468'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_restart_vdsm(self):
        """
        Ensure that after vdsm is restarted, priority change is not ignored
        """
        assert ll_hosts.checkHostSpmStatus(True, config.HOSTS[2])
        assert hosts.deactivate_host_if_up(config.HOSTS[2])
        set_spm_priority_in_db(True, config.HOSTS[2], '-1')
        restart_vdsm(2)
        assert ll_hosts.activateHost(True, config.HOSTS[2])
        self._check_no_spm()
        set_spm_priority_in_db(True, config.HOSTS[0], '2')
        restart_vdsm(0)
        self._check_host_for_spm(config.HOSTS[0])


class SingleHost(AllHostsUp):
    """
    Host that has priority -1 is not chosen, even if it is the only host

    https://tcms.engineering.redhat.com/case/138270/
    """
    __test__ = True
    tcms_test_case = '138270'
    iteration_number = 5

    @classmethod
    def setup_class(cls):
        """
        Puts two hosts into default cluster
        """
        hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '-1')

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert ll_hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHost, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host(self):
        """
        Maintenace host several times and make sure it was not selected as SPM
        """
        for _ in range(self.iteration_number):
            assert hosts.deactivate_host_if_up(config.HOSTS[0])
            assert ll_hosts.activateHost(True, config.HOSTS[0])
            self._check_no_spm()


class SPMPriorityOneHostMinusOne(DCUp):
    """
    Host with -1 priority never chosen to be spm

    https://tcms.engineering.redhat.com/case/136168/
    """
    __test__ = True
    tcms_test_case = '136168'
    iteration_number = 5

    def _select_new_spm(self):
        """
        Moves old SPM to maintenance, waits for new SPM
        and checks that new SPM is the same as before. All hosts should have
        the same SPM priority
        """
        former_spm = ll_hosts.returnSPMHost(config.HOSTS)
        LOGGER.info("former SPM - %s", former_spm)
        self._maintenance_and_wait_for_dc(former_spm)
        assert ll_hosts.activateHost(True, former_spm)
        new_spm = ll_hosts.returnSPMHost(config.HOSTS)
        self.assertNotEqual(
            former_spm, new_spm,
            "Selected the same SPM - former spm: %s, current spm: %s" %
            (former_spm, new_spm))

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Test several times that new SPM is selected each time former SPM is
        moved to maintenance
        """
        for _ in range(self.iteration_number):
            self._maintenance_and_activate_all_hosts()
            _, current_spm = ll_hosts.returnSPMHost(config.HOSTS)
            # Make sure that the host with -1 priority is not chosen to spm
            self.assertNotEqual(
                current_spm, config.HOSTS[2],
                "Selected host with -1 priority to be SPM - current spm: %s"
                % current_spm)


class TwoHost(AllHostsUp):
    """
    Host with higher priority is always chosen, after swiping priorities

    https://tcms.engineering.redhat.com/case/138271/
    """
    __test__ = True
    tcms_test_case = '138271'

    @classmethod
    def setup_class(cls):
        """
        Puts the SPM in maintenance, so we'll have only 2 active hosts and
        new election
        """
        if not ll_hosts.isHostUp(True, config.HOSTS[2]):
            ll_hosts.activateHost(True, config.HOSTS[2])
        ll_hosts.select_host_as_spm(True, config.HOSTS[2], config.DC_NAME)
        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '4')
        assert ll_hosts.setSPMPriority(True, config.HOSTS[1], '5')
        if ll_hosts.waitForHostsStates(True, config.HOSTS[2], timeout=10):
            assert hosts.deactivate_host_if_up(config.HOSTS[2])

    @classmethod
    def teardown_class(cls):
        """
        Activate the host we deactivate in setup_class
        """
        ll_hosts.activateHost(True, config.HOSTS[2])
        super(TwoHost, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_two_host(self):
        """
        Switch priorities between 2 hosts
        """
        # Make sure that the host with the highest priority is the spm
        self._check_host_for_spm(config.HOSTS[1])

        # Deactivate all hosts
        assert hosts.deactivate_host_if_up(config.HOSTS[0])
        assert hosts.deactivate_host_if_up(config.HOSTS[1])

        # Swap host priorities
        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '5')
        assert ll_hosts.setSPMPriority(True, config.HOSTS[1], '4')

        # Activate both hosts, the host with highest priority should be spm
        assert ll_hosts.activateHost(True, config.HOSTS[0])
        assert ll_hosts.activateHost(True, config.HOSTS[1])
        self._check_host_for_spm(config.HOSTS[0])


class SingleHostChangePriority(DCUp):
    """
    Make sure that spm priority changes correctly

    https://tcms.engineering.redhat.com/case/174269/
    """
    __test__ = True
    tcms_test_case = '174269'

    @classmethod
    def setup_class(cls):
        """
        Puts two hosts into default cluster
        """
        hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '-1')

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert ll_hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHostChangePriority, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host_change_priority(self):
        """
        Change priorities a few times and make sure that they actually changed
        """
        assert ll_hosts.setSPMPriority(True,
                                       config.HOSTS[0],
                                       DEFAULT_SPM_PRIORITY)

        ll_hosts.checkSPMPriority(True,  config.HOSTS[0], '5')

        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '-1')
        ll_hosts.checkSPMPriority(True,  config.HOSTS[0], '-1')

        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '10')
        ll_hosts.checkSPMPriority(True,  config.HOSTS[0], '10')


class SingleHostChangePriorityIllegal(DCUp):
    """
    Make sure that spm priority changes correctly or doesn't change at all
    if there is an illegal priority

    https://tcms.engineering.redhat.com/case/174272/
    """
    __test__ = True
    tcms_test_case = '174272'

    @classmethod
    def setup_class(cls):
        """
        Puts two hosts into default cluster
        """
        hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert ll_hosts.setSPMPriority(True, config.HOSTS[0], '-1')

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert ll_hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHostChangePriorityIllegal, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host_change_priority_illegal(self):
        """
        Change priorities a few times and make sure that they actually changed
        """
        assert ll_hosts.setSPMPriority(True,
                                       config.HOSTS[0],
                                       DEFAULT_SPM_PRIORITY)

        ll_hosts.checkSPMPriority(True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)

        self.assertFalse(ll_hosts.setSPMPriority(True, config.HOSTS[0], '-2'),
                         "Succeeded to set SPM priority to -2 - must be "
                         "greater than or equal to -1")
        ll_hosts.checkSPMPriority(True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)

        self.assertFalse(ll_hosts.setSPMPriority(True, config.HOSTS[0], '11'),
                         "Succeeded to set SPM priority to 11 - must be less "
                         "than or equal to 10")
        ll_hosts.checkSPMPriority(True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)


class SingleHostChangePriorityIllegalValue(DCUp):
    """
    Make sure that spm priority doesn't change if there is an illegal
    character

    https://tcms.engineering.redhat.com/case/144500/

    the class StorageManagerHack(StorageManager) located in /low_level/hosts.py
    that should allow passing value that is not int (e.g. '#') is not useful
    because, in the StorageManager class located in data_structures.py
    there is a check also there that the priority is int :
    " 'priority': MemberSpec_('priority', 'xs:int', 0) "

    """
    __test__ = True
    tcms_test_case = '144500'

    @classmethod
    def setup_class(cls):
        """
        Puts two hosts into default cluster
        """
        hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert ll_hosts.setSPMPriority(True,
                                       config.HOSTS[0],
                                       DEFAULT_SPM_PRIORITY)

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert ll_hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHostChangePriorityIllegalValue, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    @no_datatype_validation
    def test_single_host_change_priority_illegal(self):
        """
        Change priority to an illegal value - '#'
        """
        self.assertFalse(ll_hosts.setSPMPriority(True, config.HOSTS[0], '#'),
                         "Failed to set SPM priority to # - illegal value")
        ll_hosts.checkSPMPriority(True,  config.HOSTS[0], DEFAULT_SPM_PRIORITY)


class StorageDisconnect(DCUp):
    """
    Disconnect spm from storage, make sure that backend send spmStop and
    reconstruct master on SPM, and doesn't try to use other hosts
    (expected behavior)

    https://tcms.engineering.redhat.com/case/136447
    """
    __test__ = True
    tcms_test_case = '136447'

    @classmethod
    def teardown_class(cls):
        """
        Unblock outgoing connection
        """
        if not unblockOutgoingConnection(config.HOSTS[2], config.VDS_ROOT,
                                         config.VDS_PASSWORDS[-1],
                                         config.STORAGE_SERVERS[-1]):
            logging.debug("Failed to unblock outgoing connection")

    @bz('1017207')
    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_disconnect_storage(self):
        """
        Test that after disconnecting spm from the storage,
        backend send spmStop and
        reconstruct master on SPM, and doesn't try to use other hosts
        """
        # Make sure the the new spm is the host with the highest priority

        self._check_host_for_spm(config.HOSTS[2])
        self.assertTrue(blockOutgoingConnection(
            config.HOSTS[2], config.VDS_ROOT, config.VDS_PASSWORDS[-1],
            config.STORAGE_SERVERS[-1]))
        self._check_no_spm()

        self.assertTrue(ll_hosts.setSPMPriority(True,
                        config.HOSTS[1],
                        DEFAULT_SPM_PRIORITY),
                        "Failed to change SPM priority for host %s to "
                        "default - %s" %
                        (config.HOSTS[1], DEFAULT_SPM_PRIORITY))

        ll_hosts.getSPMPriority(config.HOSTS[1])
        self._check_host_for_spm(config.HOSTS[1])
