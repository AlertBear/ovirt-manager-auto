import pytest
from os import path

from art.test_handler.tools import polarion
from art.unittest_lib import (
    attr, testflow,
    CoreSystemTest as TestCase
)

from snmp_traps import (
    configs_dir,
    copy_ovirt_notifier_config_file,
    generate_events,
    get_snmp_result,
    finalize_class_helper,
    flush_logs,
    setup_class_helper,
    start_ovirt_notifier_service,
    stop_ovirt_notifier_service,
)


@attr(tier=2)
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

        testflow.setup("Starting ovirt notifier service.")
        start_ovirt_notifier_service()

    @classmethod
    def class_name_to_snake_case(cls):
        def helper(letter):
            if letter.isupper():
                return "_" + letter.lower()
            else:
                return letter
        return "".join(map(helper, cls.__name__[4:-5])).lstrip("_")

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
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNoAuthNoPriv, cls).setup_class(request)


class TestAuthNoPriv(SNMPTestTemplate):
    """
    Test if events from engine traps with authentication.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAuthNoPriv, cls).setup_class(request)


class TestAuthPriv(SNMPTestTemplate):
    """
    Test if events from engine traps with authentication and privacy.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAuthPriv, cls).setup_class(request)
