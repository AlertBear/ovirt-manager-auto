import pytest
from os import path

from art.test_handler.tools import polarion
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    testflow,
    tier1,
    tier2,
)

from snmp_traps import (
    restore_selinux_context,
    configs_dir,
    copy_ovirt_notifier_config_file,
    generate_events,
    get_snmp_result,
    finalize_class_helper,
    flush_logs,
    install_snmp_packages,
    remove_snmp_packages,
    setup_class_helper,
    start_ovirt_notifier_service,
    stop_ovirt_notifier_service,
)

from config import NOTIFIER_LOG, OVIRT_USER, OVIRT_GROUP, ENGINE


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        remove_snmp_packages()

    request.addfinalizer(finalize)

    install_snmp_packages()


@tier1
class TestNotifierLogOwnership(TestCase):
    """
    Class to test ovirt-notifier log ownership.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        if not ENGINE.host.fs.exists(NOTIFIER_LOG):
            pytest.skip("No log file exists.")

    @polarion("RHEVM-21772")
    def test_log_ownership(self):
        assert ENGINE.host.os.get_file_owner(
            NOTIFIER_LOG
        ) == [OVIRT_USER, OVIRT_GROUP], "Wrong log file ownership."


@tier2
class SNMPTestTemplate(TestCase):
    """
    Template class for SNMP traps tests.
    """

    @classmethod
    @pytest.fixture(scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Stopping oVirt notifier service.")
            stop_ovirt_notifier_service()

            testflow.teardown("Flushing logs.")
            flush_logs()

            testflow.teardown("Cleaning environment.")
            finalize_class_helper()

        request.addfinalizer(finalize)

        testflow.setup("Generating environment.")
        setup_class_helper()

        testflow.setup("Copying SNMP oVirt notifier config.")
        copy_ovirt_notifier_config_file(cls.init_config_file_path())

        testflow.setup("Restore selinux context on log file.")
        restore_selinux_context()

        testflow.setup("Starting ovirt notifier service.")
        start_ovirt_notifier_service()

    @classmethod
    def class_name_to_snake_case(cls):
        def helper(letter):
            if letter.isupper():
                return "_" + letter.lower()
            else:
                return letter

        return "".join(map(helper, cls.__name__[4:])).lstrip("_")

    @classmethod
    def init_config_file_name(cls):
        return ".".join([cls.class_name_to_snake_case(), "conf"])

    @classmethod
    def init_config_file_path(cls):
        return path.join(configs_dir, cls.init_config_file_name())

    @polarion("RHEVM-16356")
    def test_snmp_traps(self):
        testflow.step("Generating events on engine.")
        generate_events()
        testflow.step("Checking if the number of events logged right.")
        assert get_snmp_result()


class TestNoAuthNoPriv(SNMPTestTemplate):
    """
    Test if events from engine traps without authentication.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNoAuthNoPriv, cls).setup_class(request)


class TestAuthNoPriv(SNMPTestTemplate):
    """
    Test if events from engine traps with authentication.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAuthNoPriv, cls).setup_class(request)


class TestAuthPriv(SNMPTestTemplate):
    """
    Test if events from engine traps with authentication and privacy.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAuthPriv, cls).setup_class(request)
