'''
Sanity testing of report and dwh installation
'''

from art.unittest_lib import attr

import config
from service_base import ServiceTest


@attr(tier=1)
class SanityServicesLogs(ServiceTest):
    """Service and logs tests"""
    __test__ = True

    def setUp(self):
        config.LOGGER.info("class SanityServicesLogs "
                           "setUp")

    def tearDown(self):
        config.LOGGER.info("class SanityServicesLogs "
                           "tearDown")

    def test_dwh_service_is_running(self):
        """
         Test if ovirt-engine-dwhd is up and log file exists
        """
        self.assert_service_running_logs_exist(
            config.MACHINE,
            config.OVIRT_ENGINE_DWH_SERVICE,
            config.OVIRT_ENGINE_DWH_LOGS
        )

    def test_dwh_service_is_enabled(self):
        """
        Test if ovirt-engine-dwhd is enabled
        """
        self.assert_service_is_enabled(
            config.MACHINE,
            config.OVIRT_ENGINE_DWH_SERVICE
        )

    def test_dwh_service_restart(self):
        """
        Test restart of ovirt-engine-dwhd service
        """
        self.assert_service_restart(
            config.MACHINE,
            config.OVIRT_ENGINE_DWH_SERVICE
        )

    def test_reports_service_is_running(self):
        """
         Test if ovirt-engine-reportsd is up and log files exist
        """
        self.assert_service_running_logs_exist(
            config.MACHINE,
            config.OVIRT_ENGINE_REPORTS_SERVICE,
            config.OVIRT_ENGINE_REPORTS_LOGS
        )

    def test_reports_service_is_enabled(self):
        """
        Test if ovirt-engine-reportsd is enabled
        """
        self.assert_service_is_enabled(
            config.MACHINE,
            config.OVIRT_ENGINE_REPORTS_SERVICE
        )

    def test_reports_service_restart(self):
        """
        Test restart of ovirt-engine-reportsd service
        """
        self.assert_service_restart(
            config.MACHINE,
            config.OVIRT_ENGINE_REPORTS_SERVICE
        )
