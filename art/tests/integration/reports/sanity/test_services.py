"""
Sanity testing of report and dwh installation
"""

from art.unittest_lib import tier1
from art.test_handler.tools import polarion

from service_base import ServiceTest
import config


@tier1
class TestSanityServicesLogs(ServiceTest):
    """Service and logs tests"""
    @polarion("RHEVM-17077")
    def test_dwh_service_is_running(self):
        """
         Test if ovirt-engine-dwhd is up and log file exists
        """
        self.assert_service_running_logs_exist(
            config.ENGINE_HOST,
            config.OVIRT_ENGINE_DWH_SERVICE,
            config.OVIRT_ENGINE_DWH_LOGS
        )

    @polarion("RHEVM-17078")
    def test_dwh_service_is_enabled(self):
        """
        Test if ovirt-engine-dwhd is enabled
        """
        self.assert_service_is_enabled(
            config.ENGINE_HOST,
            config.OVIRT_ENGINE_DWH_SERVICE
        )

    @polarion("RHEVM-17080")
    def test_dwh_service_restart(self):
        """
        Test restart of ovirt-engine-dwhd service
        """
        self.assert_service_restart(
            config.ENGINE_HOST,
            config.OVIRT_ENGINE_DWH_SERVICE
        )
