"""
Regression host test module.
Checks host deployment, updating and authentication methods.
"""
import logging
import pytest

from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.utils import test_utils
from art.test_handler.exceptions import HostException
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    tier1,
    testflow,
)

import config

logger = logging.getLogger(__name__)


@bz({"1508023": {}})
class PowerManagement(TestCase):
    """
    Base class for test cases including power management
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Removing power management from host.")
            hl_hosts.remove_power_management(host_name=config.HOSTS[0])
        request.addfinalizer(finalize)

        agent = {
            "agent_type": config.PM1_TYPE,
            "agent_address": config.PM1_ADDRESS,
            "agent_username": config.PM1_USER,
            "agent_password": config.PM1_PASS,
            "concurrent": False,
            "order": 1
        }
        testflow.setup("Adding power management to host.")
        if not hl_hosts.add_power_management(
            host_name=config.HOSTS[0],
            pm_agents=[agent]
        ):
            raise HostException()


class ActiveHost(TestCase):
    """
    Base class for test cases using an active host
    """
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Activate host %s if not up.", config.HOSTS[0])
            if not hl_hosts.activate_host_if_not_up(host=config.HOSTS[0]):
                raise HostException(
                    "Cannot activate host: {0}.".format(config.HOSTS[0])
                )
        request.addfinalizer(finalize)
        testflow.setup("Activate host if not up.")
        if not hl_hosts.activate_host_if_not_up(host=config.HOSTS[0]):
            raise HostException("Cannot activate host: {0}.", config.HOSTS[0])


class HostInMaintenance(TestCase):
    """
    Base class for test cases using a host in maintenance state
    """
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Activate host %s if not up.", config.HOSTS[0])
            if not hl_hosts.activate_host_if_not_up(host=config.HOSTS[0]):
                raise HostException(
                    "Cannot activate host: {0}.".format(config.HOSTS[0])
                )
        request.addfinalizer(finalize)

        testflow.setup("Waiting for tasks on host.")
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])

        testflow.setup("Put host %s to maintenance")
        if not hl_hosts.deactivate_host_if_up(host=config.HOSTS[0]):
            raise HostException(
                "Could not set host: {0} to maintenance.".format(
                    config.HOSTS[0]
                )
            )


@tier1
class TestActivateActiveHost(ActiveHost):
    """
    Negative - Try to activate an active host - should fail
    """
    @polarion("RHEVM3-8821")
    def test_activate_active_host(self):
        testflow.step("Activating host %s.", config.HOSTS[0])
        assert ll_hosts.activate_host(False, host=config.HOSTS[0])


@tier1
class TestUpdateHostName(TestCase):
    """
    Positive  - Update host's name
    """
    NEW_NAME = "test_new_name"

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """
            Restore host's name.
            """
            testflow.teardown("Restoring host %s's name.", config.HOSTS[0])
            if not ll_hosts.update_host(
                True,
                host=cls.NEW_NAME,
                name=config.HOSTS[0]
            ):
                raise HostException(
                    "Cannot change {0} host name.".format(config.HOSTS[0])
                )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8839")
    def test_update_host_name(self):
        testflow.step("Updating host %s's name.", config.HOSTS[0])
        assert ll_hosts.update_host(
            True,
            host=config.HOSTS[0],
            name=self.NEW_NAME
        )


@tier1
@bz({"1508023": {}})
class TestAddRemovePowerManagement(TestCase):
    """
    Positive - add power management to host then remove it
    Test does not check PM only adding PM entity
    """
    @polarion("RHEVM3-8840")
    def test_add_power_management(self):
        agent = {
            "agent_type": config.PM1_TYPE,
            "agent_address": config.PM1_ADDRESS,
            "agent_username": config.PM1_USER,
            "agent_password": config.PM1_PASS,
            "concurrent": False,
            "order": 1
        }

        testflow.step("Adding power management to host %s.", config.HOSTS[0])
        assert hl_hosts.add_power_management(
            host_name=config.HOSTS[0],
            pm_agents=[agent]
        )

    @polarion("RHEVM3-8843")
    def test_remove_power_management(self):
        testflow.step(
            "Removing power management from host %s.",
            config.HOSTS[0]
        )
        assert hl_hosts.remove_power_management(host_name=config.HOSTS[0])


@tier1
class TestUpdatePowerManagementType(PowerManagement):
    """
    Positive - update power management type on host
    """
    @polarion("RHEVM3-8841")
    def test_update_power_management_type(self):
        testflow.step(
            "Update power management type to %s on host: %s.",
            config.PM2_TYPE,
            config.HOSTS[0]
        )
        assert ll_hosts.update_fence_agent(
            host_name=config.HOSTS[0],
            agent_address=config.PM1_ADDRESS,
            agent_type=config.PM2_TYPE
        ), "Cannot change power management type in host: {0}.".format(
            config.HOSTS[0]
        )


@tier1
class TestUpdatePowerManagementInvalidType(PowerManagement):
    """
    Negative - update power management type on host
    """
    INVALID_TYPE = 'invalid_type'

    @polarion("RHEVM3-8842")
    def test_update_power_management_invalid_type(self):
        testflow.step(
            "Updating power management type to %s on host: %s.",
            self.INVALID_TYPE,
            config.HOSTS[0]
        )
        assert not ll_hosts.update_fence_agent(
            host_name=config.HOSTS[0],
            agent_address=config.PM1_ADDRESS,
            agent_type=self.INVALID_TYPE
        ), (
            "Power management type changed successfully "
            "although provided with an invalid type."
        )


@tier1
class TestSetSPMToLow(TestCase):
    """
    Positive - Set SPM priority on host to low
    """
    NORMAL_SPM_LEVEL = 5
    LOW_SPM_LEVEL = 2

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """
            Set SPM priority back to Normal
            """
            testflow.teardown(
                "Set SPM priority on host: %s back to normal.",
                config.HOSTS[0]
            )
            if not ll_hosts.update_host(
                True,
                host=config.HOSTS[0],
                spm_priority=cls.NORMAL_SPM_LEVEL
            ):
                raise HostException(
                    "Cannot set SPM level on host: {0} to normal.".format(
                        config.HOSTS[0]
                    )
                )
        request.addfinalizer(finalize)

        testflow.setup(
            "Check that SPM priority on host: %s is set to normal.",
            config.HOSTS[0]
        )
        if not ll_hosts.check_spm_priority(
            True,
            host=config.HOSTS[0],
            expected_priority=cls.NORMAL_SPM_LEVEL
        ):
            testflow.setup("Updating host.")
            if not ll_hosts.update_host(
                True,
                host=config.HOSTS[0],
                spm_priority=cls.NORMAL_SPM_LEVEL
            ):
                raise HostException(
                    "Cannot set SPM level on host: {0} to normal.".format(
                        config.HOSTS[0]
                    )
                )

    @polarion("RHEVM3-8834")
    def test_set_spm_to_low(self):
        testflow.step("Set SPM priority on host: %s to low.", config.HOSTS[0])
        assert ll_hosts.update_host(
            True,
            host=config.HOSTS[0],
            spm_priority=self.LOW_SPM_LEVEL
        ), "Cannot set SPM level on host: {0} to low.".format(config.HOSTS[0])


@tier1
class TestUpdateIPOfActiveHost(ActiveHost):
    """
    Negative - update ip address on the active host expecting failure
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="function")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown(
                "Set host %s to correct address.",
                config.HOSTS[0]
            )
            if not ll_hosts.update_host(
                True,
                host=config.HOSTS[0],
                address=config.HOSTS_IP[0]
            ):
                raise HostException(
                    "Cannot change address for host {0}.".format(
                        config.HOSTS[0]
                    )
                )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8844")
    def test_update_ip_of_active_host(self):
        testflow.step(
            "Changing ip address for the active host: %s.",
            config.HOSTS[0]
        )
        assert ll_hosts.update_host(
            False,
            host=config.HOSTS[0],
            address=config.HOSTS_IP[1]
        ), (
            "Host: {0} update was successful "
            "although host is still active.".format(config.HOSTS[0])
        )


@tier1
class TestSetActiveHostToMaintenanceForReinstallation(ActiveHost):
    """
    Positive = set host to maintenance
    """
    @polarion("RHEVM3-8845")
    def test_set_active_host_to_maintenance(self):
        testflow.step("Waiting for tasks on host.")
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])

        testflow.step("Setting host %s to maintenance.", config.HOSTS[0])
        assert ll_hosts.deactivate_host(True, host=config.HOSTS[0]), (
            "Could not set host: {0} to maintenance.".format(config.HOSTS[0])
        )


@tier1
class TestReinstallHost(HostInMaintenance):
    """
    Positive - Reinstall host using password authentication
    """
    # TODO: add reinstallation with ssh authentication and negative tests
    # installation of rhevh - here or in rhevh test suite??
    # OS_RHEL = 'rhel'
    # OS_RHEVH = 'rhevh'

    @polarion("RHEVM3-8846")
    def test_reinstall_host(self):
        testflow.step("Reinstall host: %s.", config.HOSTS[0])
        assert ll_hosts.install_host(
            host=config.HOSTS[0],
            root_password=config.HOSTS_PW,
            image=config.ISO_IMAGE,
        ), "Reinstallation of host: {0} failed.".format(config.HOSTS[0])


@tier1
class TestActivateInactiveHost(HostInMaintenance):
    """
    Positive - activate host
    """
    @polarion("RHEVM3-8847")
    def test_activate_inactive_host(self):
        testflow.step("Activating host: %s.", config.HOSTS[0])
        assert ll_hosts.activate_host(True, host=config.HOSTS[0]), (
            "Host activation failed."
        )


@tier1
class TestReinstallActiveHost(ActiveHost):
    """
    Negative - re install host when active should fail
    """
    @polarion("RHEVM3-8848")
    def test_reinstall_active_host(self):
        testflow.step("Reinstalling host: %s.", config.HOSTS[0])
        assert not ll_hosts.install_host(
            host=config.HOSTS[0],
            root_password=config.HOSTS_PW,
            image=config.ISO_IMAGE,
        ), "Reinstall host: {0} worked although host is active.".format(
            config.HOSTS[0]
        )


@tier1
class TestCreateHostWithWrongIPAddress(TestCase):
    """
    Negative - add host with wrong ip
    """
    NAME = "newhost"

    @classmethod
    @pytest.fixture(autouse=True, scope="function")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Checking if host exists.")
            if ll_hosts.is_host_exist(host=cls.NAME):
                testflow.teardown("Removing host.")
                if not ll_hosts.remove_host(True, host=cls.NAME):
                    raise HostException(
                        "Unable to remove host: {0}.".format(cls.NAME)
                    )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8849")
    def test_create_host_with_wrong_ip_address(self):
        testflow.step("Adding a host with an invalid ip address.")
        assert not ll_hosts.add_host(
            name=self.NAME,
            address=config.HOST_FALSE_IP,
            root_password=config.HOSTS_PW,
            cluster=config.CLUSTER_NAME[0],
        ), "Added a host with an invalid ip address."


@tier1
class TestCreateHostWithEmptyRootPassword(TestCase):
    """
    Negative - add host without filling out the root password field
    """
    NAME = "newhost"

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Checking if host exists.")
            if ll_hosts.is_host_exist(host=cls.NAME):
                testflow.teardown("Removing host.")
                if not ll_hosts.remove_host(True, host=cls.NAME):
                    raise HostException(
                        "Unable to remove host: {0}.".format(cls.NAME)
                    )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8850")
    def test_create_host_with_empty_root_password(self):
        testflow.step("Adding a host without root password.")
        assert not ll_hosts.add_host(
            name=self.NAME,
            root_password="",
            address=config.HOSTS[1],
            cluster=config.CLUSTER_NAME[0],
        ), "Added host without root password."


@tier1
class TestRemoveActiveHost(ActiveHost):
    """
    Negative - attempt to remove host while active
    """
    @polarion("RHEVM3-8851")
    def test_remove_active_host(self):
        testflow.step("Removing host %s while active.", config.HOSTS[0])
        assert ll_hosts.remove_host(False, host=config.HOSTS[0]), (
            "Host {0} was removed although still active.".format(
                config.HOSTS[0]
            )
        )


@tier1
class TestSearchForHost(TestCase):
    """
    Positive - send a query to search for host
    """
    QUERY_KEY = "name"
    KEY_NAME = "name"

    @polarion("RHEVM3-8852")
    def test_search_for_host(self):
        testflow.step("Searching for host: %s.", config.HOSTS[0])
        assert ll_hosts.search_for_host(
                True,
                query_key=self.QUERY_KEY,
                query_val=config.HOSTS[0],
                key_name=self.KEY_NAME
        ), "Couldn't find host {0}.".format(config.HOSTS[0])


@tier1
class TestAddSecondaryPowerManagement(PowerManagement):
    """
    Positive - add secondary power management
    """
    @polarion("RHEVM3-8836")
    def test_add_secondary_power_management(self):
        agent = {
            "agent_type": config.PM2_TYPE,
            "agent_address": config.PM2_ADDRESS,
            "agent_username": config.PM2_USER,
            "agent_password": config.PM2_PASS,
            "concurrent": False,
            "order": 2
        }

        testflow.step(
            "Set secondary power management to host: %s.",
            config.HOSTS[0]
        )
        assert ll_hosts.add_fence_agent(host_name=config.HOSTS[0], **agent), (
            "Adding secondary power management to host {0} failed.".format(
                config.HOSTS[0]
            )
        )
