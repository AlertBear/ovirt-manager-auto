"""
Regression host test module.
Checks host deployment, updating and authentication methods.
"""
import logging
import pytest

from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.utils import test_utils
from art.core_api.apis_exceptions import EntityNotFound
from art.test_handler.exceptions import HostException
from art.test_handler.tools import polarion
from art.unittest_lib import (
    attr, testflow,
    CoreSystemTest as TestCase,
)

from rhevmtests.system.config import (
    PM1_TYPE, PM2_TYPE,
    HOST_FALSE_IP,
    CLUSTER_NAME as clusters_names,
    DC_NAME as dcs_names,
    HOSTS as hosts,
    HOSTS_IP as hosts_ips,
    HOSTS_PW as hosts_password,
    ISO_IMAGE as iso_image,
    VDC_HOST as vdc_host,
    VDC_ROOT_PASSWORD as vdc_root_password,
)

import config


logger = logging.getLogger(__name__)


def add_host_if_missing():
    try:
        ll_hosts.get_host_object(hosts[0])
    except EntityNotFound:
        logger.info("Adding host %s", hosts[0])
        if not ll_hosts.add_host(
            name=hosts[0],
            address=hosts_ips[0],
            root_password=hosts_password,
            port=54321,
            cluster=clusters_names[0],
            wait=False,
        ):
            raise HostException("Add host {0} failed.".format(hosts[0]))


class TestPowerManagement(TestCase):
    """
    Base class for test cases including power management
    """
    pm_type = None
    pm_address = None
    pm_user = None
    pm_password = None

    __test__ = False

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Removing power management from host.")
            hl_hosts.remove_power_management(host_name=hosts[0])
        request.addfinalizer(finalize)

        agent = {
            "agent_type": cls.pm_type,
            "agent_address": cls.pm_address,
            "agent_username": cls.pm_user,
            "agent_password": cls.pm_password,
            "concurrent": False,
            "order": 1
        }

        testflow.setup("Adding power management to host.")
        if not hl_hosts.add_power_management(
            host_name=hosts[0],
            pm_agents=[agent]
        ):
            raise HostException()


class TestActiveHost(TestCase):
    """
    Base class for test cases using an active host
    """

    __test__ = False

    @classmethod
    @pytest.fixture(scope="class")
    def setup_class(cls, request):
        testflow.setup("Checking if host is not active.")
        if not ll_hosts.isHostUp(True, host=hosts[0]):
            testflow.setup("Activating host.")
            if not ll_hosts.activate_host(True, host=hosts[0]):
                raise HostException(
                    "Cannot activate host: {0}.",
                    hosts[0]
                )


class TestHostInMaintenance(TestCase):
    """
    Base class for test cases using a host in maintenance state
    """

    __test__ = False

    @classmethod
    @pytest.fixture(scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Checking if host if active.")
            if not ll_hosts.isHostUp(True, host=hosts[0]):
                testflow.teardown("Activating host: %s.", hosts[0])
                if not ll_hosts.activate_host(True, host=hosts[0]):
                    raise HostException(
                        "Cannot activate host: {0}.".format(hosts[0])
                    )
        request.addfinalizer(finalize)

        testflow.setup("Waiting for tasks on host.")
        test_utils.wait_for_tasks(
            vdc_host,
            vdc_root_password,
            dcs_names[0]
        )

        testflow.setup("Checking if host is active.")
        if ll_hosts.isHostUp(True, host=hosts[0]):
            testflow.setup(
                "Setting host: %s to maintenance.",
                hosts[0]
            )
            if not ll_hosts.deactivate_host(True, host=hosts[0]):
                raise HostException(
                    "Could not set host: {0} to maintenance.".format(
                        hosts[0]
                    )
                )


@attr(tier=1)
class TestActivateActiveHost(TestActiveHost):
    """
    Negative - Try to activate an active host - should fail
    """
    __test__ = True

    @polarion("RHEVM3-8821")
    def test_activate_active_host(self):
        testflow.step("Activating host %s.", hosts[0])
        assert ll_hosts.activate_host(False, host=hosts[0])


@attr(tier=1)
class TestUpdateHostName(TestCase):
    """
    Positive  - Update host's name
    """
    NEW_NAME = "test_new_name"

    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """
            Restore host's name.
            """
            testflow.teardown("Restoring host %s's name.", hosts[0])
            if not ll_hosts.updateHost(
                True,
                host=cls.NEW_NAME,
                name=hosts[0]
            ):
                raise HostException(
                    "Cannot change {0} host name.".format(hosts[0])
                )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8839")
    def test_update_host_name(self):
        testflow.step("Updating host %s's name.", hosts[0])
        assert ll_hosts.updateHost(
            True,
            host=hosts[0],
            name=self.NEW_NAME
        )


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
            "agent_address": config.PM1_ADDRESS,
            "agent_username": config.PM1_USER,
            "agent_password": config.PM1_PASS,
            "concurrent": False,
            "order": 1
        }

        testflow.step("Adding power management to host %s.", hosts[0])
        if not hl_hosts.add_power_management(
            host_name=hosts[0],
            pm_agents=[agent]
        ):
            raise HostException()

    @polarion("RHEVM3-8843")
    def test_remove_power_management(self):
        testflow.step(
            "Removing power management from host %s.",
            hosts[0]
        )
        hl_hosts.remove_power_management(host_name=hosts[0])


@attr(tier=1, extra_reqs={"pm": PM1_TYPE})
class TestUpdatePowerManagementType(TestPowerManagement):
    """
    Positive - update power management type on host
    """
    pm_type = PM1_TYPE
    pm_address = config.PM1_ADDRESS
    pm_user = config.PM1_USER
    pm_password = config.PM1_PASS

    __test__ = True

    @polarion("RHEVM3-8841")
    def test_update_power_management_type(self):
        testflow.step(
            "Update power management type to %s  on host: %s.",
            PM2_TYPE,
            hosts[0]
        )
        if not ll_hosts.update_fence_agent(
            host_name=hosts[0],
            agent_address=self.pm_address,
            agent_type=PM2_TYPE
        ):
            raise HostException(
                "Cannot change power management type in host: {0}.".format(
                    hosts[0]
                )
            )


@attr(tier=1, extra_reqs={'pm': PM1_TYPE})
class TestUpdatePowerManagementInvalidType(TestPowerManagement):
    """
    Negative - update power management type on host
    """
    INVALID_TYPE = 'invalid_type'

    pm_type = PM1_TYPE
    pm_address = config.PM1_ADDRESS
    pm_user = config.PM1_USER
    pm_password = config.PM1_PASS

    __test__ = True

    @polarion("RHEVM3-8842")
    def test_update_power_management_invalid_type(self):
        testflow.step(
            "Updating power management type to %s on host: %s.",
            self.INVALID_TYPE,
            hosts[0]
        )
        if not ll_hosts.update_fence_agent(
            host_name=hosts[0],
            agent_address=self.pm_address,
            agent_type=self.INVALID_TYPE
        ):
            raise HostException(
                "Power management type changed successfully "
                "although provided with an invalid type."
            )


@attr(tier=1)
class SetSPMToLow(TestCase):
    """
    Positive - Set SPM priority on host to low
    """
    NORMAL_SPM_LEVEL = 5
    LOW_SPM_LEVEL = 2

    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """
            Set SPM priority back to Normal
            """
            testflow.teardown(
                "Set SPM priority on host: %s back to normal.",
                hosts[0]
            )
            if not ll_hosts.updateHost(
                True,
                host=hosts[0],
                spm_priority=cls.NORMAL_SPM_LEVEL
            ):
                raise HostException(
                    "Cannot set SPM level on host: {0} to normal.".format(
                        hosts[0]
                    )
                )
        request.addfinalizer(finalize)

        testflow.setup(
            "Check that SPM priority on host: %s is set to normal.",
            hosts[0]
        )
        if not ll_hosts.checkSPMPriority(
            True,
            hostName=hosts[0],
            expectedPriority=cls.NORMAL_SPM_LEVEL
        ):
            testflow.setup("Updating host.")
            if not ll_hosts.updateHost(
                True,
                host=hosts[0],
                spm_priority=cls.NORMAL_SPM_LEVEL
            ):
                raise HostException(
                    "Cannot set SPM level on host: {0} to normal.".format(
                        hosts[0]
                    )
                )

    @polarion("RHEVM3-8834")
    def test_set_spm_to_low(self):
        testflow.step("Set SPM priority on host: %s to low.", hosts[0])
        if not ll_hosts.updateHost(
            True,
            host=hosts[0],
            spm_priority=self.LOW_SPM_LEVEL
        ):
            raise HostException(
                "Cannot set SPM level on host: {0} to low.".format(
                    hosts[0]
                )
            )


@attr(tier=1)
class UpdateIPOfActiveHost(TestActiveHost):
    """
    Negative - update ip address on the active host expecting failure
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(UpdateIPOfActiveHost, cls).setup_class(request)

        def finalize():
            testflow.teardown(
                "Set host %s to correct address.",
                hosts[0]
            )
            if not ll_hosts.updateHost(
                True,
                host=hosts[0],
                address=hosts_ips[0]
            ):
                raise HostException(
                    "Cannot change address for host {0}.".format(
                        hosts[0]
                    )
                )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8844")
    def test_update_ip_of_activeHost(self):
        testflow.step(
            "Changing ip address for the active host: %s.",
            hosts[0]
        )
        if not ll_hosts.updateHost(
            False,
            host=hosts[0],
            address=hosts_ips[1]
        ):
            raise HostException(
                "Host: {0} update was successful "
                "although host is still active.".format(hosts[0])
            )


@attr(tier=1)
class SetActiveHostToMaintenanceForReinstallation(TestActiveHost):
    """
    Positive = set host to maintenance
    """
    __test__ = True

    @polarion("RHEVM3-8845")
    def test_set_active_host_to_maintenance(self):
        testflow.step("Waiting for tasks on host.")
        test_utils.wait_for_tasks(
            vdc_host,
            vdc_root_password,
            dcs_names[0]
        )

        testflow.step("Setting host %s to maintenance.", hosts[0])
        if not ll_hosts.deactivate_host(True, host=hosts[0]):
            raise HostException(
                "Could not set host: {0} to maintenance.".format(
                    hosts[0]
                )
            )


@attr(tier=1)
class ReinstallHost(TestHostInMaintenance):
    """
    Positive - Reinstall host using password authentication
    """
    # TODO: add reinstallation with ssh authentication and negative tests
    # installation of rhevh - here or in rhevh test suite??
    # OS_RHEL = 'rhel'
    # OS_RHEVH = 'rhevh'

    __test__ = True

    @polarion("RHEVM3-8846")
    def test_reinstall_host(self):
        testflow.step("Reinstall host: %s.", hosts[0])
        if not ll_hosts.install_host(
            host=hosts[0],
            root_password=hosts_password,
            image=iso_image,
        ):
            raise HostException(
                "Reinstallation of host: {0} failed.".format(hosts[0])
            )


@attr(tier=1)
class ManualFenceForHost(TestHostInMaintenance):
    """
    Positive - Manual fence host
    """
    __test__ = True

    @polarion("RHEVM3-8835")
    def test_manual_fence_for_host(self):
        testflow.step("Manual fence host: %s.", hosts[0])
        if not ll_hosts.fence_host(host=hosts[0], fence_type='manual'):
            raise HostException(
                "Manual fence for host: {0} failed.".format(hosts[0])
            )


@attr(tier=1)
class ActivateInactiveHost(TestHostInMaintenance):
    """
    Positive - activate host
    """
    __test__ = True

    @polarion("RHEVM3-8847")
    def test_activate_inactive_host(self):
        testflow.step("Activating host: %s.", hosts[0])
        if not ll_hosts.activate_host(True, host=hosts[0]):
            raise HostException("Host activation failed.")


@attr(tier=1)
class ReinstallActiveHost(TestActiveHost):
    """
    Negative - re install host when active should fail
    """
    __test__ = True

    @polarion("RHEVM3-8848")
    def test_reinstall_active_host(self):
        testflow.step("Reinstalling host: %s.", hosts[0])
        if ll_hosts.install_host(
            host=hosts[0],
            root_password=hosts_password,
            image=iso_image,
        ):
            raise HostException(
                "Reinstall host: {0} worked although host is active.".format(
                    hosts[0]
                )
            )


@attr(tier=1)
class CreateHostWithWrongIPAddress(TestCase):
    """
    Negative - add host with wrong ip
    """
    NAME = "newhost"

    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Checking if host exists.")
            if ll_hosts.is_host_exist(host_name=cls.NAME):
                testflow.teardown("Removing host.")
                if not ll_hosts.removeHost(True, host=cls.NAME):
                    raise HostException(
                        "Unable to remove host: {0}.".format(cls.NAME)
                    )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8849")
    def test_create_host_with_wrong_IP_address(self):
        testflow.step("Adding a host with an invalid ip address.")
        if ll_hosts.add_host(
            name=self.NAME,
            address=HOST_FALSE_IP,
            root_password=hosts_password,
            cluster=clusters_names[0],
        ):
            raise HostException("Added a host with an invalid ip address.")


@attr(tier=1)
class CreateHostWithEmptyRootPassword(TestCase):
    """
    Negative - add host without filling out the root password field
    """
    NAME = "newhost"

    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Checking if host exists.")
            if ll_hosts.is_host_exist(host_name=cls.NAME):
                testflow.teardown("Removing host.")
                if not ll_hosts.removeHost(True, host=cls.NAME):
                    raise HostException(
                        "Unable to remove host: {0}.".format(cls.NAME)
                    )
        request.addfinalizer(finalize)

    @polarion("RHEVM3-8850")
    def test_create_host_with_empty_root_password(self):
        testflow.step("Adding a host without root password.")
        if ll_hosts.add_host(
            name=self.NAME,
            root_password="",
            address=hosts[1],
            cluster=clusters_names[0],
        ):
            raise HostException("Added host without root password.")


@attr(tier=1)
class RemoveActiveHost(TestActiveHost):
    """
    Negative - attempt to remove host while active
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(RemoveActiveHost, cls).setup_class(request)

        def finalizer():
            testflow.teardown("Adding host if it's missing.")
            add_host_if_missing()

        request.addfinalizer(finalizer)

    @polarion("RHEVM3-8851")
    def test_remove_active_host(self):
        testflow.step("Removing host %s while active.", hosts[0])
        if not ll_hosts.removeHost(False, host=hosts[0]):
            raise HostException(
                "Host {0} was removed although still active.".format(
                    hosts[0]
                )
            )


@attr(tier=1)
class SearchForHost(TestCase):
    """
    Positive - send a query to search for host
    """
    QUERY_KEY = "name"
    KEY_NAME = "name"

    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls):
        testflow.setup("Adding host if it's missing.")
        add_host_if_missing()

    @polarion("RHEVM3-8852")
    def test_search_for_host(self):
        testflow.step("Searching for host: %s.", hosts[0])
        if not ll_hosts.searchForHost(
                True,
                query_key=self.QUERY_KEY,
                query_val=hosts[0],
                key_name=self.KEY_NAME
        ):
            raise HostException(
                "Couldn't find host {0}.".format(hosts[0])
            )


@attr(tier=1, extra_reqs={'pm': PM1_TYPE})
class AddSecondaryPowerManagement(TestPowerManagement):
    """
    Positive - add secondary power management
    """
    pm_type = PM1_TYPE
    pm_address = config.PM1_ADDRESS
    pm_user = config.PM1_USER
    pm_password = config.PM1_PASS

    __test__ = True

    @polarion("RHEVM3-8836")
    def test_add_secondary_power_management(self):
        agent = {
            "agent_type": PM2_TYPE,
            "agent_address": config.PM2_ADDRESS,
            "agent_username": config.PM2_USER,
            "agent_password": config.PM2_PASS,
            "concurrent": False,
            "order": 2
        }

        testflow.step(
            "Set secondary power management to host: %s.",
            hosts[0]
        )
        if not ll_hosts.add_fence_agent(host_name=hosts[0], **agent):
            raise HostException(
                "Adding secondary power management to host {0} failed.".format(
                    hosts[0]
                )
            )
