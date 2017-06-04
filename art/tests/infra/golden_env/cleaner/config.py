from art.test_handler.settings import ART_CONFIG, GE
from art.rhevm_api import resources


PARAMETERS = ART_CONFIG['PARAMETERS']

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']

VDC = REST_CONNECTION.get('host')
VDC_PASSWORD = PARAMETERS.get('vdc_root_password')

ENGINE_HOST = resources.Host(VDC)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_PASSWORD)
)
ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        REST_CONNECTION['user'],
        REST_CONNECTION['password'],
        resources.Domain(REST_CONNECTION['user_domain']),
    ),
    schema=REST_CONNECTION.get('schema'),
    port=REST_CONNECTION['port'],
    entry_point=REST_CONNECTION['entry_point'],
)

# Hosted engine parameters
HOSTED_ENGINE = ART_CONFIG.get('HOSTED_ENGINE')

# Hosted engine parameters
HE_HOST_IP = GE['hosts'][0]['address']
HE_ADDITIONAL_HOSTS = [host['address'] for host in GE['hosts'][1:]]
HE_VM_NAME = 'HostedEngine'
HE_SD_NAME = 'hosted_storage'
HE_CL_NAME = GE['clusters'][0]['name']
HE_DC_NAME = GE['datacenters'][0]['name']
HE_SD_TYPE = (
    GE.get('hosted_engine_details', {}).get('storage', {}).get('type')
)
HE_SD_ADDRESS = (
    GE.get('hosted_engine_details', {}).get('storage', {}).get('address')
)
HE_SD_LUN = (
    GE.get('hosted_engine_details', {}).get('storage', {}).get('lun')
)
HE_SD_PATH = GE.get('hosted_engine_details', {}).get('storage', {}).get('path')
