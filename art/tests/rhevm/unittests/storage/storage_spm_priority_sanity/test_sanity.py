"""
Storage SPM priority sanity test - 5299
https://tcms.engineering.redhat.com/plan/5299/
"""

import logging
import time
from unittest import TestCase

from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from art.test_handler import exceptions
from art.unittest_lib.common import is_bz_state
import config


LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']
HOST_API = get_api('host', 'hosts')

BZ986961_NOT_FIXED = not is_bz_state('986961')


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_plan_id = '5299'
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
        if False in res:
            fhosts = [config.HOSTS[i] for i, result in res if not result]
            raise exceptions.HostException(
                "Setting SPM priority failed on hosts %s", fhosts)

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
            assert hosts.waitForSPM(config.DC_NAME, 600, 10)

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


class TwoHostsAndOneWithHigherPriority(BaseTestCase):
    """
    Two hosts with same spm priority id and one host is higher

    https://tcms.engineering.redhat.com/case/136167

    In this the behaviour must be as in the test when all hosts have different
    SPM value.
    The host with the highest value always choosen to be SPM host.
    """
    __test__ = True
    tcms_test_case = '136167'

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

    def test_priority(self):
        """
        Ensure that hosts with -1 value as spm priority won't be selected as
        SPM
        """
        time.sleep(config.PARAMETERS.as_float('sleep_amount'))
        self.assertTrue(hosts.checkSPMPresence(False, self.STRING_HOSTS))
        LOGGER.info("No SPM was selected, that's correct")

    @classmethod
    def teardown_class(cls):
        """
        Set some SPM in order to clean up
        """
        assert hosts.setSPMPriority(True, config.HOSTS[0], '5')
        assert datacenters.waitForDataCenterState(config.DC_NAME)
        super(SPMPriorityMinusOne, cls).teardown_class()


class SeveralHosts(AllHostsUp):
    """
    Several hosts with different SPM priority

    https://tcms.engineering.redhat.com/case/136171/
    """
    __test__ = True
    tcms_test_case = '136171'

    def test_priority(self):
        """
        SPM host is always the host with the highest SPM Priority value.
        """
        self._get_new_spm(config.HOSTS[0], config.HOSTS[2])
        self._get_new_spm(config.HOSTS[2], config.HOSTS[1])
        self._get_new_spm(config.HOSTS[1], config.HOSTS[2])
