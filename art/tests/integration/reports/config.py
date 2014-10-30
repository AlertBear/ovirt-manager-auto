__test__ = False

import logging

from art.test_handler.settings import ART_CONFIG
from rhevm_api.resources.host import Host
from rhevm_api.resources.user import RootUser

LOGGER = logging.getLogger(__name__)

TEST_NAME = "ReportsLocalDbScratchInstallSanityTest"
PARAMETERS = ART_CONFIG['PARAMETERS']

VDC_HOST = PARAMETERS.get('host', None)
VDC_ROOT_USER = 'root'
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', None)

OVIRT_ENGINE_DWH_LOG = "/var/log/ovirt-engine-dwh/ovirt-engine-dwhd.log"
OVIRT_ENGINE_DWH_SERVICE = "ovirt-engine-dwhd"
JASPER_SERVER_LOG = "/var/log/ovirt-engine-reports/jasperserver.log"
SERVICE_IS_NOT_RUNNING_MSG = "Service %s is not running"
SERVICE_IS_RUNNING_MSG = "Service %s is running"
FILE_DOES_NOT_EXIST_MSG = "File %s does not exist"
MACHINE = Host(VDC_HOST)
MACHINE.users.append(RootUser(VDC_ROOT_PASSWORD))
