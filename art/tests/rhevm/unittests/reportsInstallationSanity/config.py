__test__ = False

from art.test_handler.settings import ART_CONFIG

TEST_NAME = "ReportsLocalDbScratchInstallSanityTest"
PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
RHEVM_MACHINE = REST_CONNECTION['host']
USERNAME_ROOT = "root"
VDC_ROOT_PASSWORD = PARAMETERS['vdc_root_password']
