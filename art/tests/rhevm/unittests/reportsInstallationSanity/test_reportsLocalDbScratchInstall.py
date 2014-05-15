'''
Sanity testing of report installation
'''

import logging
from utilities.machine import LINUX, Machine
from art.unittest_lib import attr
from art.unittest_lib import CoreSystemTest as TestCase
import config as cfg


LOGGER = logging.getLogger(__name__)

OVIRT_ENGINE_DWH_LOG = "/var/log/ovirt-engine-dwh/ovirt-engine-dwhd.log"
OVIRT_ENGINE_DWH_SERVICE = "ovirt-engine-dwhd"
JASPER_SERVER_LOG = "/var/log/ovirt-engine-reports/jasperserver.log"
SERVICE_IS_NOT_RUNNING_MSG = "Service %s is not running"
SERVICE_IS_RUNNING_MSG = "Service %s is running"
FILE_DOES_NOT_EXIST_MSG = "File %s does not exist"

MACHINE = Machine(host=cfg.RHEVM_MACHINE,
                  user=cfg.USERNAME_ROOT,
                  password=cfg.VDC_ROOT_PASSWORD).util(LINUX)


def is_dwh_running(machine):
    try:
        return machine.isServiceRunning(OVIRT_ENGINE_DWH_SERVICE)
    except ValueError:
        return False


@attr(tier=0)
class ReportsLocalDbScratchInstallSanityTest(TestCase):
    """ Basic run vm test """
    __test__ = True

    def setUp(self):
        LOGGER.info("class ReportsLocalDbScratchInstallSanityTest setUp")

    def tearDown(self):
        LOGGER.info("class ReportsLocalDbScratchInstallSanityTest tearDown")

    def test_dwh_service_is_installed(self):
        """
         Test if ovirt-engine-dwhd is up and log file exists
        """
        LOGGER.info("Test if %s service is running", OVIRT_ENGINE_DWH_SERVICE)
        self.assertTrue(is_dwh_running(MACHINE),
                        "%s is not running" % OVIRT_ENGINE_DWH_SERVICE)

        for log_file in [OVIRT_ENGINE_DWH_LOG, JASPER_SERVER_LOG]:
            LOGGER.info("Test if %s exists", log_file)
            self.assertTrue(MACHINE.isFileExists(log_file),
                            FILE_DOES_NOT_EXIST_MSG % log_file)
