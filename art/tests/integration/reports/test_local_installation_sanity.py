'''
Sanity testing of report installation
'''

from art.unittest_lib import attr
from reports import config
from reports.service_base import ServiceTest


@attr(tier=0)
class ReportsLocalDbScratchInstallSanityTest(ServiceTest):
    """ Basic run vm test """
    __test__ = True

    def setUp(self):
        config.LOGGER.info("class ReportsLocalDbScratchInstallSanityTest "
                           "setUp")

    def tearDown(self):
        config.LOGGER.info("class ReportsLocalDbScratchInstallSanityTest "
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
