"""
Test configuration - Log Collector
"""

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG

LOGCOLLECTOR_UTIL = "ovirt-log-collector"

PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
VDC_PASSWORD = REST_CONNECTION['password']
ADMIN_PASSWORD = '123456'

CONFIG_FILE_LOCATION = '/etc/ovirt-engine/logcollector.conf'

VDC_HOST = REST_CONNECTION['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)
