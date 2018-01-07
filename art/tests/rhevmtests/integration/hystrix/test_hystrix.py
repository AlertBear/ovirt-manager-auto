import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion
from art.unittest_lib import (
    CoreSystemTest,
    testflow,
    tier3,
)

from . import (
    check_hystrix_status, config,
    check_hystrix_monitoring, init_pipes,
    cleanup_pipes, logger
)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        """
        Description:
            If there are any errors in event generation vm will not be removed.
            So for cleanup reason we need to do this.
        """
        testflow.teardown("Removing %s VM.", config.HYSTRIX_VM_NAME)
        try:
            ll_vms.removeVm(
                positive=True,
                vm=config.HYSTRIX_VM_NAME,
                stopVM=True,
                wait=True
            )
        except EntityNotFound:
            logger.info("%s was not found but it's ok", config.HYSTRIX_VM_NAME)
    request.addfinalizer(finalize)


@tier3
class HystrixTemplate(CoreSystemTest):
    need_restart = False

    @classmethod
    @pytest.fixture(scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown(
                "Setting %s property to default value.",
                config.HYSTRIX_PROPERTY_KEY
            )

            assert config.engine.engine_config(
                action="set",
                param=[
                    "{0}=false".format(config.HYSTRIX_PROPERTY_KEY),
                    " --cver=general"
                ],
                restart=cls.need_restart
            )

        request.addfinalizer(finalize)

        testflow.setup(
            "Setting %s property to new value.\nEnabling Hystrix.",
            config.HYSTRIX_PROPERTY_KEY
        )
        assert config.engine.engine_config(
            action="set",
            param=[
                "{0}=true".format(config.HYSTRIX_PROPERTY_KEY),
                " --cver=general"
            ],
            restart=cls.need_restart
        )


class TestHystrixSanity(HystrixTemplate):
    """
    Defaults sanity check.
    """
    @polarion("RHEVM-17609")
    def test_hystrix_default_property_value(self):
        testflow.step(
            "Checking if %s default value is 'false'.",
            config.HYSTRIX_PROPERTY_KEY
        )
        hystrix_property = config.engine.engine_config(
            action="get",
            param=config.HYSTRIX_PROPERTY_KEY,
            restart=self.need_restart
        )
        key = config.HYSTRIX_PROPERTY_KEY
        value = hystrix_property["results"][key]["value"]
        assert value == "false", "Default value is not right: {}!".format(
            value
        )

    @staticmethod
    @polarion("RHEVM-17611")
    def test_hystrix_default_status():
        testflow.step("Checking if Hystrix is disabled by default.")
        assert not check_hystrix_status(), "Hystrix must be off by default!"


class TestHystrixIntegration(HystrixTemplate):
    need_restart = True

    pipes = [config.event_pipe, config.status_pipe]

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestHystrixIntegration, cls).setup_class(request)

        def finalize():
            testflow.teardown("Cleaning environment")
            cleanup_pipes(cls.pipes)
        request.addfinalizer(finalize)

        testflow.setup("Initializing message pipes.")
        init_pipes(cls.pipes)

    @polarion("RHEVM-17612")
    def test_hystrix_new_property_value(self):
        testflow.step(
            "Checking if %s value doesn't flush after engine restart.",
            config.HYSTRIX_PROPERTY_KEY
        )
        hystrix_property = config.engine.engine_config(
            action="get",
            param=config.HYSTRIX_PROPERTY_KEY,
            restart=self.need_restart
        )
        key = config.HYSTRIX_PROPERTY_KEY
        value = hystrix_property["results"][key]["value"]
        assert value == "true", "New value was not set right: {}!".format(
            value
        )

    @staticmethod
    @polarion("RHEVM-17613")
    def test_hystrix_status():
        testflow.step("Checking if Hystrix is enabled.")
        assert check_hystrix_status(), "Hystrix must be running!"

    @staticmethod
    @polarion("RHEVM-18287")
    def test_hystrix_stream():
        testflow.step("Checking if Hystrix does monitor engine events.")
        check_hystrix_monitoring()
