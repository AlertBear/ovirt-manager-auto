"""
Regression host test
Checks host deployment, updating and authentication methods
"""

import art.rhevm_api.tests_lib.low_level.hosts as hosts
from art.rhevm_api.utils.test_utils import get_api
from art.core_api.apis_exceptions import EntityNotFound
from art.test_handler.tools import tcms
from art.unittest_lib import CoreSystemTest as TestCase
from nose.tools import istest
from art.unittest_lib import attr
from rhevmtests.system.reg_hosts import config
import logging
from art.test_handler.exceptions import HostException
from art.rhevm_api.tests_lib.high_level.hosts import \
    add_power_management, remove_power_management


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
DISK_SIZE = 3 * 1024 * 1024 * 1024
PINNED = config.ENUMS['vm_affinity_pinned']
HOST_CONNECTING = config.ENUMS['host_state_connecting']
VM_DOWN = config.ENUMS['vm_state_down']
HOST = config.HOSTS[0]
HOST2 = config.HOSTS[1]
HOST_PW = config.HOSTS_PW
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


def _add_host_if_missing():
        try:
            HOST_API.find(HOST)
        except EntityNotFound:
            logger.info("adding host %s", HOST)
            if not hosts.addHost(True, name=HOST, address=HOST,
                                 root_password=HOST_PW,
                                 port=54321, cluster=config.CLUSTER_NAME,
                                 wait=False):
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
        add_power_management(host=HOST, pm_type=cls.pm_type,
                             pm_address=cls.pm_address, pm_user=cls.pm_user,
                             pm_password=cls.pm_password)

    @classmethod
    def teardown_class(cls):
        if not remove_power_management(host=HOST, pm_type=PM2_TYPE):
            remove_power_management(host=HOST, pm_type=PM1_TYPE)


class TestActiveHost(TestCase):
    """
    Base class for test cases using an active host
    """

    __test__ = False

    @classmethod
    def setup_class(cls):
        if not hosts.isHostUp(True, host=HOST):
            if not hosts.activateHost(True, host=HOST):
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
        if hosts.isHostUp(True, host=HOST):
            logger.info("setting host: %s to maintenance", HOST)
            if not hosts.deactivateHost(True, host=HOST):
                raise HostException("Could not set host: %s "
                                    "to maintenance" % HOST)

    @classmethod
    def teardown_class(cls):
        if not hosts.isHostUp(True, host=HOST):
            logger.info("Activating host: %s", HOST)
            if not hosts.activateHost(True, host=HOST):
                raise HostException("cannot activate host: %s" % HOST)


@attr(tier=0)
class TestActivateActiveHost(TestActiveHost):
    """
    Negative - Try to activate an active host - should fail
    """
    __test__ = True

    @istest
    @tcms('9608', '275952')
    def activate_active_host(self):
        logger.info("Trying to activate host %s", HOST)
        self.assertFalse(
            hosts.activateHost(True, host=HOST))


@attr(tier=0)
class TestUpdateHostName(TestCase):
    """
    Positive  - Update host's name
    """
    __test__ = True

    new_name = 'test_new_name'

    @istest
    @tcms('9608', '275953')
    def update_host_name(self):
        logger.info("Updating host %s's name", HOST)
        self.assertTrue(
            hosts.updateHost(True, host=HOST, name=self.new_name))

    @classmethod
    def teardown_class(cls):
        """
        Update host's name back.
        """
        logger.info("Updating host %s's name back", HOST)
        if not hosts.updateHost(True, host=cls.new_name, name=HOST):
            raise HostException("Cannot change host %s's name" % HOST)


@attr(tier=0)
class TestAddRemovePowerManagement(TestCase):
    """
    Positive - add power management to host then remove it
    Test does not check PM only adding PM entity
    """
    __test__ = True

    @istest
    @tcms('9608', '275955')
    def add_power_management(self):
        add_power_management(host=HOST, pm_type=PM1_TYPE,
                             pm_address=PM1_ADDRESS, pm_user=PM1_USER,
                             pm_password=PM1_PASS)

    @istest
    @tcms('9608', '275958')
    def remove_power_management(self):
        remove_power_management(host=HOST, pm_type=PM1_TYPE)


@attr(tier=0)
class TestUpdatePowerManagementType(TestPowerManagement):
    """
    Positive - update power management type on host
    """
    __test__ = True
    pm_type = PM1_TYPE
    pm_address = PM1_ADDRESS
    pm_user = PM1_USER
    pm_password = PM1_PASS

    @istest
    @tcms('9608', '275956')
    def update_power_management_type(self):
        logger.info("Update power management type "
                    "to %s  on host: %s", PM2_TYPE, HOST)
        if not hosts.updateHost(True, host=HOST, pm='true', pm_type=PM2_TYPE):
            raise HostException("Cannot change power management type"
                                " in host: %s" % HOST)


@attr(tier=0)
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

    @istest
    @tcms('9608', '275957')
    def update_power_management_invalid_type(self):
        logger.info("Update power management type to %s"
                    "on host: %s", self.invalid_type, HOST)
        if not hosts.updateHost(False, host=HOST, pm='true',
                                pm_type=self.invalid_type):
            raise HostException("Power management type changed successfully"
                                "although provided with an invalid type")


@attr(tier=0)
class SetSPMToLow(TestCase):
    """
    Positive - Set SPM priority on host to low
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info("Check that SPM priority on host: %s is"
                    " set to normal", HOST)
        if not hosts.checkSPMPriority(True, hostName=HOST, expectedPriority=5):
            if not hosts.updateHost(True, host=HOST,
                                    storage_manager_priority=5):
                raise HostException("Cannot set SPM level on host:"
                                    "%s to normal" % HOST)

    @istest
    @tcms('9608', '280721')
    def set_spm_to_low(self):
        logger.info("Set SPM priority on host: %s to low", HOST)
        if not hosts.updateHost(True, host=HOST, storage_manager_priority=2):
            raise HostException("Cannot set SPM level on host:"
                                " %s to low" % HOST)

    @classmethod
    def teardown_class(cls):
        """
        Set SPM priority back to Normal
        """
        logger.info("Set SPM priority on host: %s back to normal", HOST)
        if not hosts.updateHost(True, host=HOST, storage_manager_priority=5):
            raise HostException("Cannot set SPM level on host:"
                                " %s to normal" % HOST)


@attr(tier=0)
class UpdateIPOfActiveHost(TestActiveHost):
    """
    Negative - update ip address on the active host expecting failure
    """
    __test__ = True

    @istest
    @tcms('9608', '275959')
    def update_ip_of_activeHost(self):
        logger.info("changing ip address for the active host: %s", HOST)
        if not hosts.updateHost(False, host=HOST, address=HOST2):
            raise HostException("Host: %s update was successful although host"
                                "is still active" % HOST)

    @classmethod
    def teardown_class(cls):
        logger.info("set host %s to correct address", HOST)
        if not hosts.updateHost(True, host=HOST, address=HOST):
            raise HostException("Cannot change address for host %s" % HOST)


@attr(tier=0)
class SetActiveHostToMaintenanceForReinstallation(TestActiveHost):
    """
    Positive = set host to maintenance
    """
    __test__ = True

    @istest
    @tcms('9608', '275960')
    def set_active_host_to_maintenance(self):
        logger.info("setting host %s to maintenance", HOST)
        if not hosts.deactivateHost(True, host=HOST):
            raise HostException("Could not set host: %s to maintenance" % HOST)


@attr(tier=0)
class ReinstallHost(TestHostInMaintenance):
    """
    Positive - Reinstall host using password authentication
    """
    __test__ = True

    os_rhel = 'rhel'
    os_rhevh = 'rhevh'

    @istest
    @tcms('9608', '275961')
    def reinstall_host(self):
        logger.info("reinstall host: %s", HOST)
        if not hosts.installHost(True, host=HOST, root_password=HOST_PW,
                                 iso_image=config.ISO_IMAGE):
            raise HostException("re installation of host: %s failed" % HOST)


# TODO: add reinstallation with ssh authentication and negative tests
# installation of rhevh - here or in rhevh test suite??


@attr(tier=0)
class ManualFenceForHost(TestHostInMaintenance):
    """
    Positive - Manual fence host
    """
    __test__ = True

    @istest
    @tcms('9608', '280727')
    def manual_fence_for_host(self):
        logger.info("Manual fence host: %s", HOST)
        if not hosts.fenceHost(True, host=HOST, fence_type='manual'):
            raise HostException("Manual fence for host: %s failed" % HOST)


@attr(tier=0)
class ActivateInactiveHost(TestHostInMaintenance):
    """
    Positive - activate host
    """
    __test__ = True

    @istest
    @tcms('9608', '275963')
    def activate_inactive_host(self):
        logger.info("activate host: %s", HOST)
        if not hosts.activateHost(True, host=HOST):
            raise HostException("host activation failed")


@attr(tier=0)
class ReinstallActiveHost(TestActiveHost):
    """
    Negative - re install host when active should fail
    """
    __test__ = True

    @istest
    @tcms('9608', '275964')
    def reinstall_active_host(self):
        logger.info("attempting to re install host: %s ", HOST)
        if not hosts.installHost(False, host=HOST, root_password=HOST_PW,
                                 iso_image=config.ISO_IMAGE):
            raise HostException("re install host: %s worked although "
                                "host is active" % HOST)


@attr(tier=0)
class CreateHostWithWrongIPAddress(TestCase):
    """
    Negative - add host with wrong ip
    """
    __test__ = True

    name = 'newhost'

    @istest
    @tcms('9608', '275965')
    def create_host_with_wrong_IP_address(self):
        logger.info("attempting to add a host with an invalid ip address")
        if not hosts.addHost(False, name=self.name, address=HOST_FALSE_IP,
                             root_password=HOST_PW):
            raise HostException("added a host with an invalid ip address")

    @classmethod
    def teardown_class(cls):
        if hosts.validateHostExist(True, host=cls.name):
            if not hosts.removeHost(True, host=cls.name):
                raise HostException("unable to remove host: %s" % cls.name)


@attr(tier=0)
class CreateHostWithEmptyRootPassword(TestCase):
    """
    Negative - add host without filling out the root password field
    """
    __test__ = True

    name = 'newhost'

    @istest
    @tcms('9608', '275966')
    def create_host_with_empty_root_password(self):
        logger.info("attempting to add a host without root password")
        if not hosts.addHost(False, name=self.name, root_password='',
                             address=HOST2):
            raise HostException("added a host without providing root password")

    @classmethod
    def teardown_class(cls):
        if hosts.validateHostExist(True, host=cls.name):
            if not hosts.removeHost(True, host=cls.name):
                raise HostException("unable to remove host: %s" % cls.name)


@attr(tier=0)
class RemoveActiveHost(TestActiveHost):
    """
    Negative - attempt to remove host while active
    """
    __test__ = True

    @istest
    @tcms('9608', '275967')
    def remove_active_host(self):
        logger.info("attempting to remove host: %s while active", HOST)
        if not hosts.removeHost(False, host=HOST):
            raise HostException("Host %s was removed although"
                                " still active" % HOST)

    @classmethod
    def teardown_class(cls):
        _add_host_if_missing()


@attr(tier=0)
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

    @istest
    @tcms('9608', '275968')
    def search_for_host(self):
        logger.info("search for host: %s", HOST)
        if not hosts.searchForHost(True, query_key=self.query_key,
                                   query_val=HOST, key_name=self.key_name):
            raise HostException("couldn't find host %s" % HOST)


@attr(tier=0)
class AddSecondaryPowerManagement(TestPowerManagement):
    """
    Positive - add secondary power management
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info("Add primary power management to host: %s", HOST)
        add_power_management(host=HOST, pm_type=PM1_TYPE,
                             pm_address=PM1_ADDRESS, pm_user=PM1_USER,
                             pm_password=PM1_PASS)

    @istest
    @tcms('9608', '282899')
    def add_secondary_power_management(self):
        logger.info("Set secondary power management to host: %s", HOST)
        if not hosts.updateHost(True, host=HOST, pm='true',
                                pm_proxies=['cluster', 'dc'],
                                agents=[(PM1_TYPE, PM1_ADDRESS, PM1_USER,
                                         PM1_PASS, None, False, 1),
                                        (PM2_TYPE, PM2_ADDRESS, PM2_USER,
                                         PM2_PASS, None, False, 2)]):
            raise HostException("adding secondary power management to "
                                "host s% failed" % HOST)
