from art.test_handler.settings import ART_CONFIG
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
