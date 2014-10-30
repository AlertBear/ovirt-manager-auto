'''
Sanity testing of report installation
'''

from art.unittest_lib import attr
from art.unittest_lib import CoreSystemTest as TestCase
from reports import config


def is_dwh_running(machine):
    try:
        return machine.service(config.OVIRT_ENGINE_DWH_SERVICE).status()
    except ValueError:
        return False


@attr(tier=0)
class ReportsLocalDbScratchInstallSanityTest(TestCase):
    """ Basic run vm test """
    __test__ = True

    def setUp(self):
        config.LOGGER.info("class ReportsLocalDbScratchInstallSanityTest "
                           "setUp")

    def tearDown(self):
        config.LOGGER.info("class ReportsLocalDbScratchInstallSanityTest "
                           "tearDown")

    def test_dwh_service_is_installed(self):
        """
         Test if ovirt-engine-dwhd is up and log file exists
        """
        config.LOGGER.info("Test if %s service is running",
                           config.OVIRT_ENGINE_DWH_SERVICE)
        self.assertTrue(is_dwh_running(config.MACHINE),
                        "%s is not running" % config.OVIRT_ENGINE_DWH_SERVICE)

        for log_file in [config.OVIRT_ENGINE_DWH_LOG,
                         config.JASPER_SERVER_LOG]:
            config.LOGGER.info("Test if %s exists", log_file)
            self.assertTrue(config.MACHINE.executor().
                            run_cmd(['[', '-e', log_file, ']'])[0] == 0,
                            # checking if return code of [ -e $log_file ] is 0
                            config.FILE_DOES_NOT_EXIST_MSG % log_file)
