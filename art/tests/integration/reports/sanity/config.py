__test__ = False

from reports.config import *  # flake8: noqa
from art.test_handler.settings import ART_CONFIG
from art.rhevm_api.resources.host import Host
from art.rhevm_api.resources.user import RootUser

import logging

LOGGER = logging.getLogger(__name__)

TEST_NAME = "SanityServicesLogs"
PARAMETERS = ART_CONFIG['PARAMETERS']

VDC_HOST = PARAMETERS.get('host', None)
VDC_ROOT_USER = 'root'
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', None)

SERVICE_IS_NOT_RUNNING_MSG = "Service %s is not running"
SERVICE_IS_RUNNING_MSG = "Service %s is running"
FILE_DOES_NOT_EXIST_MSG = "File %s does not exist"
MACHINE = Host(VDC_HOST)
MACHINE.users.append(RootUser(VDC_ROOT_PASSWORD))
