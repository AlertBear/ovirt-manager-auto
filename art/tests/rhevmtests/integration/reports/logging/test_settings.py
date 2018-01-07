"""
Sanity testing of report and dwh installation
"""

import pytest

from art.test_handler.tools import polarion
from art.unittest_lib import (
    testflow,
    tier2,
)

from logging_base import LoggingTest
import config


@tier2
class TestApplicationSettings(LoggingTest):
    """
    Test application setting of dwh
    """
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def set_up(cls, request):

        def fin():
            testflow.teardown("class %s tearDown", cls.__name__)
            cls.assert_remove_backup(config.DWH_LOG_BACKUP)

        request.addfinalizer(fin)

        testflow.setup("Set up class %s", cls.__name__)
        cls.assert_backup_file(config.DWH_LOG, config.DWH_LOG_BACKUP)

        cls.assert_service_restart(
            config.ENGINE_HOST,
            config.OVIRT_ENGINE_DWH_SERVICE,
            config.SLEEP_TIME_SETTINGS
        )

        cls.settings = cls.assert_grep_diff_logs(
            "ETL Service Started",
            config.DWH_LOG,
            config.DWH_LOG_BACKUP,
            config.SETTINGS_COUNT
        )

    @polarion("RHEVM-17085")
    def test_settings(self):
        """
        Test settings displayed after restart
        """
        options = dict(
            (line.split('|')[0], line.split('|')[-1])
            for line in self.settings.splitlines()
        )
        for (var, val) in config.DWH_VARS.iteritems():
            testflow.step("Check variable {0} for value {1}".format(var, val))
            self.assert_setting_variable(options, var, val)
