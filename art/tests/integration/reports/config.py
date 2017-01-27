"""
Reports and dwh testing module
"""

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG

# RHEVM related constants
PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
VDC_PASSWORD = REST_CONNECTION['password']
VDC_PORT = REST_CONNECTION['port']
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']

VDC_ADMIN_USER = 'admin'
VDC_ADMIN_DOMAIN = 'internal'

# ENGINE SECTION
VDC_HOST = REST_CONNECTION['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)

ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        VDC_ADMIN_USER,
        VDC_PASSWORD,
        resources.Domain(VDC_ADMIN_DOMAIN),
    ),
    schema=REST_CONNECTION.get('schema'),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT,
)

# DWH SECTION
OVIRT_ENGINE_DWH_LOGS = ["/var/log/ovirt-engine-dwh/ovirt-engine-dwhd.log"]
DWH_LOG = OVIRT_ENGINE_DWH_LOGS[0]
OVIRT_ENGINE_DWH_SERVICE = "ovirt-engine-dwhd"
OVIRT_ENGINE_SERVICE = "ovirt-engine"
