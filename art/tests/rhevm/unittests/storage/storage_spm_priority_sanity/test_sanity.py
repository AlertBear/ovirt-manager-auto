"""
Storage SPM priority sanity test - 5299
https://tcms.engineering.redhat.com/plan/5299/
"""

import logging
import time
from unittest import TestCase

import art.rhevm_api.tests_lib.high_level.hosts as hi_hosts
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.utils.test_utils import get_api, toggleServiceOnHost
from art.test_handler.settings import opts
from art.test_handler import exceptions
from art.test_handler.tools import tcms
from art.unittest_lib.common import is_bz_state
import config
from art.rhevm_api.utils.storage_api import blockOutgoingConnection, \
    unblockOutgoingConnection


LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']
HOST_API = get_api('host', 'hosts')

BZ986961_NOT_FIXED = not is_bz_state('986961')

TCMS_PLAN_ID = '5299'
TMP_CLUSTER = "Default"
SPM_TIMEOUT = 300
POLLING_INTERVAL = 10
DEFAULT_SPM_PRIORITY = '5'


def raise_if_false(results, collection, message, exc):
    """
    Raises exception if False occurs in results. Message must contain one
    placeholder for string which will be items from collection on which place
    False is
    """
    if False in results:
        failed = [collection[i] for i, result in enumerate(results)
                  if not result]
        raise exc(message % failed)


def set_spm_priority_in_db(positive, host, priority):
    """
    Changes spm priority value in DB for the host
    """
    assert hosts.setSPMPriorityInDB(
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
            res.append(hosts.setSPMPriority(True, host, pri))
        raise_if_false(
            res, config.HOSTS, "Setting SPM priority failed on hosts %s",
            exceptions.HostException)

    def _check_host_for_spm(self, host):
        """
        Tests that host is spm
        """
        LOGGER.info("Ensuring host %s is SPM", host)
        self.assertTrue(
            hosts.checkHostSpmStatus(True, host),
            "Host %s is not an SPM but should be" % host)

    def _maintenance_and_wait_for_dc(self, host):
        """
        Maintenance given host and waits until DC is up
        """
        LOGGER.info("Deactivating host %s", host)
        assert hosts.deactivateHost(True, host)
        LOGGER.debug("Waiting until DC is up")
        assert datacenters.waitForDataCenterState(config.DC_NAME) or \
            BZ986961_NOT_FIXED
        # WA BZ#986961
        if BZ986961_NOT_FIXED:
            LOGGER.info("Due to BZ#986961 waiting until one of hosts is "
                        "selected as SPM")
            assert hosts.waitForSPM(config.DC_NAME, 600, POLLING_INTERVAL)

    def _maintenance_and_activate_all_hosts(self):
        # Deactivate all hosts
        assert hosts.deactivateHosts(True, config.HOSTS)

        # Activate all hosts
        assert hosts.activateHosts(True, config.HOSTS)

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
        assert hosts.activateHost(True, spm)

    @classmethod
    def setup_class(cls):
        """
        Sets priorities, prepares dc with one host activated
        """
        cls._set_priorities()
        LOGGER.debug("Waiting for SPM")
        assert hosts.waitForSPM(config.DC_NAME, SPM_TIMEOUT, POLLING_INTERVAL)
        spm_host = hosts.getSPMHost(config.HOSTS)
        LOGGER.debug("SPM is %s", spm_host)
        LOGGER.debug("Deactivating hosts %s", config.HOSTS)
        assert hosts.deactivateHosts(True, cls.STRING_HOSTS)


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
        for host_name in config.HOSTS:
            assert hosts.activateHost(True, host_name)

    @classmethod
    def teardown_class(cls):
        """
        Moves all maintenanced hosts to up status
        """
        for host_name in config.HOSTS:
            host_obj = HOST_API.find(host_name)
            if host_obj.status.state == ENUMS['host_state_maintenance']:
                assert hosts.activateHost(True, host_name)

    def _check_no_spm(self):
        """
        Checks there was no SPM selected
        """
        LOGGER.info("Sleeping for %d seconds in order to make sure no SPM was"
                    " selected", config.SLEEP_AMOUNT)
        time.sleep(config.SLEEP_AMOUNT)
        self.assertTrue(hosts.checkSPMPresence(False, self.STRING_HOSTS))
        LOGGER.info("No SPM was selected, that's correct")


class DCUp(AllHostsUp):
    """
    All hosts and DC are up
    """

    @classmethod
    def setup_class(cls):
        super(DCUp, cls).setup_class()
        assert hosts.waitForSPM(config.DC_NAME, SPM_TIMEOUT, POLLING_INTERVAL)



class TwoHostsAndOneWithHigherPriority(BaseTestCase):
    """
    Two hosts with same spm priority id and one host is higher

    https://tcms.engineering.redhat.com/case/136167

    In this the behaviour must be as in the test when all hosts have different
    SPM value.
    The host with the highest value always chosen to be SPM host.
    """
    __test__ = True
    tcms_test_case = '136167'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_priority(self):
        """
        Ensure that host with highest priority is always chosen as SPM
        """
        LOGGER.debug("Activating host %s", config.HOSTS[0])
        assert hosts.activateHost(True, config.HOSTS[0])
        LOGGER.debug("Waiting until DC is up")
        assert datacenters.waitForDataCenterState(config.DC_NAME)
        self._check_host_for_spm(config.HOSTS[0])
        LOGGER.info("Activating host %s", config.HOSTS[1])
        assert hosts.activateHost(True, config.HOSTS[1])
        LOGGER.info("Activating host %s", config.HOSTS[2])
        assert hosts.activateHost(True, config.HOSTS[2])
        self._maintenance_and_wait_for_dc(config.HOSTS[0])
        self._check_host_for_spm(config.HOSTS[2])
        self._maintenance_and_wait_for_dc(config.HOSTS[2])
        assert hosts.activateHost(True, config.HOSTS[0])
        assert hosts.activateHost(True, config.HOSTS[2])
        self._maintenance_and_wait_for_dc(config.HOSTS[1])
        self._check_host_for_spm(config.HOSTS[2])


class SPMPriorityMinusOne(AllHostsUp):
    """
    All hosts with '-1' priority

    https://tcms.engineering.redhat.com/case/136169/
    """
    __test__ = True
    tcms_test_case = '136169'

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
        assert hosts.setSPMPriority(
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
            priorities.append(hosts.checkSPMPriority(True, host, '5'))
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
        Moves old SPM to maintenance, waits for new SPM and checks that new SPM
        is the same as before. All hosts should have the same SPM priority
        """
        former_spm = hosts._getSPMHostname(config.HOSTS)
        self._maintenance_and_wait_for_dc(former_spm)
        assert hosts.activateHost(True, former_spm)
        new_spm = hosts._getSPMHostname(config.HOSTS)
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
        assert hosts.checkHostSpmStatus(True, config.HOSTS[2])
        assert hosts.deactivateHost(True, config.HOSTS[2])
        set_spm_priority_in_db(True, config.HOSTS[2], '-1')
        restart_vdsm(2)
        assert hosts.activateHost(True, config.HOSTS[2])
        self._check_no_spm()
        set_spm_priority_in_db(True, config.HOSTS[0], '2')
        restart_vdsm(0)
        assert hosts.waitForSPM(config.DC_NAME, SPM_TIMEOUT, POLLING_INTERVAL)
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
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert hosts.setSPMPriority(True, config.HOSTS[0], '-1')

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHost, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host(self):
        """
        Maintenace host several times and make sure it was not selected as SPM
        """
        for _ in range(self.iteration_number):
            assert hosts.deactivateHost(True, config.HOSTS[0])
            assert hosts.activateHost(True, config.HOSTS[0])
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
        Moves old SPM to maintenance, waits for new SPM and checks that new SPM
        is the same as before. All hosts should have the same SPM priority
        """
        former_spm = hosts.returnSPMHost(config.HOSTS)
        self._maintenance_and_wait_for_dc(former_spm)
        assert hosts.activateHost(True, former_spm)
        new_spm = hosts.returnSPMHost(config.HOSTS)
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
            current_spm = hosts.returnSPMHost(config.HOSTS)
            # Make sure that the host with -1 priority is not chosen to spm
            self.assertNotEqual(
                current_spm, config.HOSTS[2],
                "Selected the -1 host to be SPM - current spm: %s" %
                (current_spm))


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
        Puts one hosts into default cluster, so we'll have only 2 hosts
        """
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert hosts.setSPMPriority(True, config.HOSTS[0], '4')
        assert hosts.setSPMPriority(True, config.HOSTS[1], '5')


    @classmethod
    def teardown_class(cls):
        """
        Moves one hosts back from default cluster
        """
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(TwoHost, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_two_host(self):
        """
        Switch priorities between 2 hosts
        """
        # Make sure that the host with the highest priority is the spm
        self._check_host_for_spm(config.HOSTS[1])

        # Deactivate all hosts
        assert hosts.deactivateHost(True, config.HOSTS[0])
        assert hosts.deactivateHost(True, config.HOSTS[1])

        # Swap host priorities
        set_spm_priority_in_db(config.HOSTS[0], 5)
        set_spm_priority_in_db(config.HOSTS[1], 4)

        # Activate both hosts, the host with highest priority should be spm
        assert hosts.activateHost(True, config.HOSTS[0])
        assert hosts.activateHost(True, config.HOSTS[1])
        self._check_host_for_spm(config.HOSTS[0])


class FenceSPM(DCUp):
    """
    Reboot the spm and make sure that the new spm is the host with the
    highest priority

    https://tcms.engineering.redhat.com/case/144502/
    """
    __test__ = True
    tcms_test_case = '144502'
    iteration_number = 5

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_fence_spm(self):
        """
        Reboot spm
        """
        for _ in range(self.iteration_number):
            self._maintenance_and_activate_all_hosts()

            # Make sure that the host with the highest priority is the spm
            self._check_host_for_spm(config.HOSTS[2])

            # Fence spm host (reboot)
            hosts.fenceHost(True, config.HOSTS[2], 'restart')

            # Make sure the the new spm is the host with the highest priority
            self._check_host_for_spm(config.HOSTS[1])


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
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert hosts.setSPMPriority(True, config.HOSTS[0], '-1')

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHostChangePriority, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host_change_priority(self):
        """
        Change priorities a few times and make sure that they actually changed
        """
        assert hosts.setSPMPriority(True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hosts.checkSPMPriority(True,  config.HOSTS[0], '5')

        assert hosts.setSPMPriority(True, config.HOSTS[0], '-1')
        hosts.checkSPMPriority(True,  config.HOSTS[0], '-1')

        assert hosts.setSPMPriority(True, config.HOSTS[0], '10')
        hosts.checkSPMPriority(True,  config.HOSTS[0], '10')


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
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert hosts.setSPMPriority(True, config.HOSTS[0], '-1')

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHostChangePriorityIllegal, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host_change_priority_illegal(self):
        """
        Change priorities a few times and make sure that they actually changed
        """
        assert hosts.setSPMPriority(True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hosts.checkSPMPriority(True,  config.HOSTS[0], DEFAULT_SPM_PRIORITY)

        assert hosts.setSPMPriority(False, config.HOSTS[0], '-2')
        hosts.checkSPMPriority(True,  config.HOSTS[0], DEFAULT_SPM_PRIORITY)

        assert hosts.setSPMPriority(True, config.HOSTS[0], '11')
        hosts.checkSPMPriority(True,  config.HOSTS[0], DEFAULT_SPM_PRIORITY)


class SingleHostChangePriorityIllegalValue(DCUp):
    """
    Make sure that spm priority doesn't change if there is an illegal
    character

    https://tcms.engineering.redhat.com/case/144500/
    """
    __test__ = True
    tcms_test_case = '144500'

    @classmethod
    def setup_class(cls):
        """
        Puts two hosts into default cluster
        """
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], TMP_CLUSTER)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], TMP_CLUSTER)
        assert hosts.setSPMPriority(True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)

    @classmethod
    def teardown_class(cls):
        """
        Moves two hosts back from default cluster
        """
        assert hosts.setSPMPriority(
            True, config.HOSTS[0], DEFAULT_SPM_PRIORITY)
        hi_hosts.switch_host_to_cluster(config.HOSTS[1], config.CLUSTER_NAME)
        hi_hosts.switch_host_to_cluster(config.HOSTS[2], config.CLUSTER_NAME)
        super(SingleHostChangePriorityIllegalValue, cls).teardown_class()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_single_host_change_priority_illegal(self):
        """
        Change priority to an illegal value - '#'
        """
        assert hosts.setSPMPriority(False, config.HOSTS[0], '#')
        hosts.checkSPMPriority(True,  config.HOSTS[0], DEFAULT_SPM_PRIORITY)


class StorageDisconnect(DCUp):
    """
    Disconnect storage from spm, make sure that backend send spmStop and
    reconstruct master on SPM, and doesn't try to use other hosts
    (expected behavior)

    https://tcms.engineering.redhat.com/case/136447
    """
    __test__ = True
    tcms_test_case = '136447'

    @classmethod
    def setup_class(cls):
        """
        Do nothing
        """
        pass


    @classmethod
    def teardown_class(cls):
        """
        Unblock outgoing connection
        """
        if not unblockOutgoingConnection(config.HOSTS[2], config.VDS_ROOT,
                                         config.VDS_PASSWORDS[-1],
                                         config.STORAGE_SERVERS[-1]):
            logging.debug("Failed to unblock outgoing connection")


    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_disconnect_storage(self):
        """
        Test that after disconnecting storage from the spm,
        backend send spmStop and
        reconstruct master on SPM, and doesn't try to use other hosts
        """
        # Make sure the the new spm is the host with the highest priority
        self._check_host_for_spm(config.HOSTS[2])
        self.assertTrue(blockOutgoingConnection(
            config.HOSTS[2], config.VDS_ROOT, config.VDS_PASSWORDS[-1],
            config.STORAGE_SERVERS[-1]))
        self._check_no_spm()

        assert hosts.setSPMPriority(False, config.HOSTS[1], DEFAULT_SPM_PRIORITY)
        self._check_host_for_spm(config.HOSTS[1])
