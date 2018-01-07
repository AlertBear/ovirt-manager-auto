"""
Sanity testing of report and dwh installation
"""
import pytest
from time import sleep

from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier3,
    testflow,
)

from logging_base import LoggingTest
import config


@tier3
class TestDebugLogs(LoggingTest):
    """Log tests"""
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def set_up(cls, request):
        def fin():
            testflow.teardown("Class %s tearDown", cls.__name__)
            testflow.step("Disabling debug mode")

            assert config.ENGINE_HOST.run_command(['rm', config.DEBUG_CONF])
            cls.assert_service_restart(
                config.ENGINE_HOST,
                config.OVIRT_ENGINE_DWH_SERVICE
            )

            cls.assert_remove_backup(config.DWH_LOG_BACKUP)

        request.addfinalizer(fin)

        testflow.setup("Set up class %s", cls.__name__)
        testflow.step("Enabling debug mode")
        assert config.ENGINE_HOST.run_command(
            ['echo', config.ENABLE_LOG, '>', config.DEBUG_CONF]
        )
        cls.assert_service_restart(
                config.ENGINE_HOST,
                config.OVIRT_ENGINE_DWH_SERVICE
        )
        cls.assert_backup_file(config.DWH_LOG, config.DWH_LOG_BACKUP)

        testflow.step("Wait 1 minutes for logs to fill")
        sleep(60)

    @polarion("RHEVM-17082")
    def test_dwh_debug_aggregation_samples(self):
        """
         Test aggregation is logged properly for lowest interval
        """
        self.assert_grep_diff_logs("SampleTime")
