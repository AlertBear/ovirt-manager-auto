"""
Sanity testing of report and dwh installation
"""
import pytest
from time import sleep

from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, testflow

from logging_base import LoggingTest
import config


@bz({'1434326': {}})
@attr(tier=3)
class DebugLogs(LoggingTest):
    """Log tests"""
    __test__ = True

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def set_up(cls, request):
        def fin():
            testflow.teardown("Class %s tearDown", cls.__name__)
            testflow.step("Disabling debug mode")

            assert config.ENGINE_HOST.run_command(['rm', config.DEBUG_CONF])

            cls.assert_remove_backup(config.DWH_LOG_BACKUP)

            testflow.step("Restarting ntp")
            assert config.ENGINE_HOST.service("ntpd").start()

            cls.assert_service_restart(
                config.ENGINE_HOST,
                config.OVIRT_ENGINE_DWH_SERVICE
            )

            cls.assert_service_restart(
                config.ENGINE_HOST,
                config.OVIRT_ENGINE_SERVICE
            )

        request.addfinalizer(fin)

        testflow.setup("Set up class %s", cls.__name__)
        testflow.step("Enabling debug mode")
        assert config.ENGINE_HOST.run_command(
            ['echo', config.ENABLE_LOG, '>', config.DEBUG_CONF]
        )
        cls.assert_backup_file(config.DWH_LOG, config.DWH_LOG_BACKUP)

        testflow.step("Stopping ntp")
        assert config.ENGINE_HOST.service("ntpd").stop()

        testflow.step("Change time to end of the date")
        cmd = ['date', '+%T', '-s', '23:58:00']
        assert config.ENGINE_HOST.run_command(command=cmd), (
            "Error: Unable to backup dwhd.log"
        )

        config.ENGINE.restart()
        config.OVIRT_ENGINE_DWH_SERVICE.restart()

        testflow.step("Wait 2 minutes till next day")
        sleep(120)

    @polarion("RHEVM-17082")
    def test_dwh_debug_aggregation_samples(self):
        """
         Test aggregation is logged properly for lowest interval
        """
        self.assert_grep_diff_logs("Sample")

    @polarion("RHEVM-17084")
    def test_dwh_debug_aggregation_hours(self):
        """
         Test aggregation is logged properly for minutes
        """
        self.assert_grep_diff_logs("Hourly")

    @polarion("RHEVM-17085")
    def test_dwh_debug_aggregation_days(self):
        """
         Test aggregation is logged properly days
        """
        self.assert_grep_diff_logs("Daily")
