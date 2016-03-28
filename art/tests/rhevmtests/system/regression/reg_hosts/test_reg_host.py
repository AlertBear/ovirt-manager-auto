"""
Regression host test
Checks host deployment, updating and authentication methods
"""

from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.core_api.apis_exceptions import EntityNotFound
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from rhevmtests.system.regression.reg_hosts import config
import logging
from art.test_handler.exceptions import HostException


PINNED = config.ENUMS['vm_affinity_pinned']
HOST_CONNECTING = config.ENUMS['host_state_connecting']
VM_DOWN = config.ENUMS['vm_state_down']
HOST = None  # Filled in setup_module
HOST_IP = None  # Filled in setup_module
HOST2 = None  # Filled in setup_module
HOST2_IP = None  # Filled in setup_module
HOST_PW = None  # Filled in setup_module
PM1_TYPE = config.PM1_TYPE
PM2_TYPE = config.PM2_TYPE
PM1_ADDRESS = config.PM1_ADDRESS
PM2_ADDRESS = config.PM2_ADDRESS
PM1_USER = config.PM1_USER
PM2_USER = config.PM2_USER
PM1_PASS = config.PM1_PASS
PM2_PASS = config.PM2_PASS
HOST_FALSE_IP = config.HOST_FALSE_IP


logger = logging.getLogger(__name__)

########################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    global HOST, HOST_IP, HOST2, HOST2_IP, HOST_PW
    HOST = config.HOSTS[0]
    HOST_IP = config.HOSTS_IP[0]
    HOST2 = config.HOSTS[1]
    HOST2_IP = config.HOSTS_IP[1]
    HOST_PW = config.HOSTS_PW


def _add_host_if_missing():
    try:
        ll_hosts.get_host_object(HOST)
    except EntityNotFound:
        logger.info("adding host %s", HOST)
        if not ll_hosts.addHost(
                True, name=HOST, address=HOST_IP, root_password=HOST_PW,
                port=54321, cluster=config.CLUSTER_NAME[0], wait=False,
        ):
            raise HostException("Add host %s failed" % HOST)


class TestPowerManagement(TestCase):
    """
    Base class for test cases including power management
    """

    __test__ = False
    pm_type = None
    pm_address = None
    pm_user = None
    pm_password = None

    @classmethod
    def setup_class(cls):
        agent = {
            "agent_type": cls.pm_type,
            "agent_address": cls.pm_address,
            "agent_username": cls.pm_user,
            "agent_password": cls.pm_password,
            "concurrent": False,
            "order": 1
        }
        if not hl_hosts.add_power_management(
            host_name=HOST, pm_agents=[agent]
        ):
            raise HostException()

    @classmethod
    def teardown_class(cls):
        hl_hosts.remove_power_management(host_name=HOST)


class TestActiveHost(TestCase):
    """
    Base class for test cases using an active host
    """

    __test__ = False

    @classmethod
    def setup_class(cls):
        if not ll_hosts.isHostUp(True, host=HOST):
            if not ll_hosts.activateHost(True, host=HOST):
                raise HostException("cannot activate host: %s" % HOST)

    @classmethod
    def teardown_class(cls):
        cls.setup_class()


class TestHostInMaintenance(TestCase):
    """
    Base class for test cases using a host in maintenance state
    """

    __test__ = False

    @classmethod
    def setup_class(cls):
        if ll_hosts.isHostUp(True, host=HOST):
            logger.info("setting host: %s to maintenance", HOST)
            if not ll_hosts.deactivateHost(True, host=HOST):
                raise HostException(
                    "Could not set host: %s to maintenance" % HOST
                )

    @classmethod
    def teardown_class(cls):
        if not ll_hosts.isHostUp(True, host=HOST):
            logger.info("Activating host: %s", HOST)
            if not ll_hosts.activateHost(True, host=HOST):
                raise HostException("cannot activate host: %s" % HOST)


@attr(tier=1)
class TestActivateActiveHost(TestActiveHost):
    """
    Negative - Try to activate an active host - should fail
    """
    __test__ = True

    @polarion("RHEVM3-8433")
    def test_activate_active_host(self):
        logger.info("Trying to activate host %s", HOST)
        self.assertFalse(
            ll_hosts.activateHost(True, host=HOST))


@attr(tier=1)
class TestUpdateHostName(TestCase):
    """
    Positive  - Update host's name
    """
    __test__ = True

    new_name = 'test_new_name'

    @polarion("RHEVM3-8418")
    def test_update_host_name(self):
        logger.info("Updating host %s's name", HOST)
        self.assertTrue(
            ll_hosts.updateHost(True, host=HOST, name=self.new_name)
        )

    @classmethod
    def teardown_class(cls):
        """
        Update host's name back.
        """
        logger.info("Updating host %s's name back", HOST)
        if not ll_hosts.updateHost(True, host=cls.new_name, name=HOST):
            raise HostException("Cannot change host %s's name" % HOST)


@attr(tier=1, extra_reqs={'pm': PM1_TYPE})
class TestAddRemovePowerManagement(TestCase):
    """
    Positive - add power management to host then remove it
    Test does not check PM only adding PM entity
    """
    __test__ = True

    @polarion("RHEVM3-8840")
    def test_add_power_management(self):
        agent = {
            "agent_type": PM1_TYPE,
            "agent_address": PM1_ADDRESS,
            "agent_username": PM1_USER,
            "agent_password": PM1_PASS,
            "concurrent": False,
            "order": 1
        }
        if not hl_hosts.add_power_management(
            host_name=HOST, pm_agents=[agent]
        ):
            raise HostException()

    @polarion("RHEVM3-8843")
    def test_remove_power_management(self):
        hl_hosts.remove_power_management(host_name=HOST)


@attr(tier=1, extra_reqs={'pm': PM1_TYPE})
class TestUpdatePowerManagementType(TestPowerManagement):
    """
    Positive - update power management type on host
    """
    __test__ = True
    pm_type = PM1_TYPE
    pm_address = PM1_ADDRESS
    pm_user = PM1_USER
    pm_password = PM1_PASS

    @polarion("RHEVM3-8841")
    def test_update_power_management_type(self):
        logger.info(
            "Update power management type to %s  on host: %s", PM2_TYPE, HOST)
        if not ll_hosts.update_fence_agent(
            host_name=HOST,
            agent_address=self.pm_address,
            agent_type=PM2_TYPE
        ):
            raise HostException(
                "Cannot change power management type in host: %s" % HOST
            )


@attr(tier=1, extra_reqs={'pm': PM1_TYPE})
class TestUpdatePowerManagementInvalidType(TestPowerManagement):
    """
    Negative - update power management type on host
    """
    __test__ = True
    pm_type = PM1_TYPE
    pm_address = PM1_ADDRESS
    pm_user = PM1_USER
    pm_password = PM1_PASS
    invalid_type = 'invalid_type'

    @polarion("RHEVM3-8842")
    def test_update_power_management_invalid_type(self):
        logger.info(
            "Update power management type to %s on host: %s",
            self.invalid_type, HOST
        )
        if not ll_hosts.update_fence_agent(
            host_name=HOST,
            agent_address=self.pm_address,
            agent_type=self.invalid_type
        ):
            raise HostException(
                "Power management type changed successfully "
                "although provided with an invalid type"
            )


@attr(tier=1)
class SetSPMToLow(TestCase):
    """
    Positive - Set SPM priority on host to low
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info(
            "Check that SPM priority on host: %s is set to normal", HOST
        )
        if not ll_hosts.checkSPMPriority(
                True, hostName=HOST, expectedPriority=5
        ):
            if not ll_hosts.updateHost(True, host=HOST, spm_priority=5):
                raise HostException(
                    "Cannot set SPM level on host:%s to normal" % HOST
                )

    @polarion("RHEVM3-8432")
    def test_set_spm_to_low(self):
        logger.info("Set SPM priority on host: %s to low", HOST)
        if not ll_hosts.updateHost(True, host=HOST, spm_priority=2):
            raise HostException(
                "Cannot set SPM level on host: %s to low" % HOST
            )

    @classmethod
    def teardown_class(cls):
        """
        Set SPM priority back to Normal
        """
        logger.info("Set SPM priority on host: %s back to normal", HOST)
        if not ll_hosts.updateHost(True, host=HOST, spm_priority=5):
            raise HostException(
                "Cannot set SPM level on host: %s to normal" % HOST
            )


@attr(tier=1)
class UpdateIPOfActiveHost(TestActiveHost):
    """
    Negative - update ip address on the active host expecting failure
    """
    __test__ = True

    @polarion("RHEVM3-8419")
    def test_update_ip_of_activeHost(self):
        logger.info("changing ip address for the active host: %s", HOST)
        if not ll_hosts.updateHost(False, host=HOST, address=HOST2_IP):
            raise HostException(
                "Host: %s update was successful although host is still active"
                % HOST
            )

    @classmethod
    def teardown_class(cls):
        logger.info("set host %s to correct address", HOST)
        if not ll_hosts.updateHost(True, host=HOST, address=HOST_IP):
            raise HostException("Cannot change address for host %s" % HOST)


@attr(tier=1)
class SetActiveHostToMaintenanceForReinstallation(TestActiveHost):
    """
    Positive = set host to maintenance
    """
    __test__ = True

    @polarion("RHEVM3-8420")
    def test_set_active_host_to_maintenance(self):
        logger.info("setting host %s to maintenance", HOST)
        if not ll_hosts.deactivateHost(True, host=HOST):
            raise HostException("Could not set host: %s to maintenance" % HOST)


@attr(tier=1)
class ReinstallHost(TestHostInMaintenance):
    """
    Positive - Reinstall host using password authentication
    """
    __test__ = True

    os_rhel = 'rhel'
    os_rhevh = 'rhevh'

    @polarion("RHEVM3-8421")
    def test_reinstall_host(self):
        logger.info("reinstall host: %s", HOST)
        if not ll_hosts.installHost(
                True, host=HOST, root_password=HOST_PW,
                iso_image=config.ISO_IMAGE
        ):
            raise HostException("re installation of host: %s failed" % HOST)


# TODO: add reinstallation with ssh authentication and negative tests
# installation of rhevh - here or in rhevh test suite??


@attr(tier=1)
class ManualFenceForHost(TestHostInMaintenance):
    """
    Positive - Manual fence host
    """
    __test__ = True

    @polarion("RHEVM3-8835")
    def test_manual_fence_for_host(self):
        logger.info("Manual fence host: %s", HOST)
        if not ll_hosts.fenceHost(True, host=HOST, fence_type='manual'):
            raise HostException("Manual fence for host: %s failed" % HOST)


@attr(tier=1)
class ActivateInactiveHost(TestHostInMaintenance):
    """
    Positive - activate host
    """
    __test__ = True

    @polarion("RHEVM3-8422")
    def test_activate_inactive_host(self):
        logger.info("activate host: %s", HOST)
        if not ll_hosts.activateHost(True, host=HOST):
            raise HostException("host activation failed")


@attr(tier=1)
class ReinstallActiveHost(TestActiveHost):
    """
    Negative - re install host when active should fail
    """
    __test__ = True

    @polarion("RHEVM3-8423")
    def test_reinstall_active_host(self):
        logger.info("attempting to re install host: %s ", HOST)
        if not ll_hosts.installHost(
                False, host=HOST, root_password=HOST_PW,
                iso_image=config.ISO_IMAGE
        ):
            raise HostException(
                "re install host: %s worked although host is active" % HOST
            )


@attr(tier=1)
class CreateHostWithWrongIPAddress(TestCase):
    """
    Negative - add host with wrong ip
    """
    __test__ = True

    name = 'newhost'

    @polarion("RHEVM3-8424")
    def test_create_host_with_wrong_IP_address(self):
        logger.info("attempting to add a host with an invalid ip address")
        if not ll_hosts.addHost(
                False, name=self.name, address=HOST_FALSE_IP,
                root_password=HOST_PW
        ):
            raise HostException("added a host with an invalid ip address")

    @classmethod
    def teardown_class(cls):
        if ll_hosts.validateHostExist(True, host=cls.name):
            if not ll_hosts.removeHost(True, host=cls.name):
                raise HostException("unable to remove host: %s" % cls.name)


@attr(tier=1)
class CreateHostWithEmptyRootPassword(TestCase):
    """
    Negative - add host without filling out the root password field
    """
    __test__ = True

    name = 'newhost'

    @polarion("RHEVM3-8425")
    def test_create_host_with_empty_root_password(self):
        logger.info("attempting to add a host without root password")
        if not ll_hosts.addHost(
                False, name=self.name, root_password='', address=HOST2_IP
        ):
            raise HostException("added a host without providing root password")

    @classmethod
    def teardown_class(cls):
        if ll_hosts.validateHostExist(True, host=cls.name):
            if not ll_hosts.removeHost(True, host=cls.name):
                raise HostException("unable to remove host: %s" % cls.name)


@attr(tier=1)
class RemoveActiveHost(TestActiveHost):
    """
    Negative - attempt to remove host while active
    """
    __test__ = True

    @polarion("RHEVM3-8427")
    def test_remove_active_host(self):
        logger.info("attempting to remove host: %s while active", HOST)
        if not ll_hosts.removeHost(False, host=HOST):
            raise HostException(
                "Host %s was removed although still active" % HOST
            )

    @classmethod
    def teardown_class(cls):
        _add_host_if_missing()


@attr(tier=1)
class SearchForHost(TestCase):
    """
    Positive - send a query to search for host
    """
    __test__ = True

    query_key = 'name'
    key_name = 'name'

    @classmethod
    def setup_class(cls):
        _add_host_if_missing()

    @polarion("RHEVM3-8428")
    def test_search_for_host(self):
        logger.info("search for host: %s", HOST)
        if not ll_hosts.searchForHost(
                True, query_key=self.query_key, query_val=HOST,
                key_name=self.key_name
        ):
            raise HostException("couldn't find host %s" % HOST)


@attr(tier=1, extra_reqs={'pm': PM1_TYPE})
class AddSecondaryPowerManagement(TestPowerManagement):
    """
    Positive - add secondary power management
    """
    __test__ = True

    pm_type = PM1_TYPE
    pm_address = PM1_ADDRESS
    pm_user = PM1_USER
    pm_password = PM1_PASS

    @polarion("RHEVM3-8836")
    def test_add_secondary_power_management(self):
        logger.info("Set secondary power management to host: %s", HOST)
        agent = {
            "agent_type": PM2_TYPE,
            "agent_address": PM2_ADDRESS,
            "agent_username": PM2_USER,
            "agent_password": PM2_PASS,
            "concurrent": False,
            "order": 2
        }
        if not ll_hosts.add_fence_agent(host_name=HOST, **agent):
            raise HostException(
                "adding secondary power management to host s% failed" % HOST
            )
