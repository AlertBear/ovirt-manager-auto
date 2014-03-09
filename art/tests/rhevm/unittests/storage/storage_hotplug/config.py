from . import ART_CONFIG

__test__ = False

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

CLUSTER_NAME = PARAMETERS['cluster_name']
IMAGES = PARAMETERS['images']
TEMPLATE_NAMES = PARAMETERS.as_list('template_names')
WAIT_TIME = 120
BLOCK_FS = PARAMETERS['data_center_type'] in ('iscsi',)
STORAGE_CONF = ART_CONFIG[STORAGE_TYPE.upper()]
STORAGE_DOMAIN_NAME = "%s_%d" % (STORAGE_TYPE.lower(), 0)
TESTNAME = 'hotplug'

# cobbler related settings
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

MAX_WORKERS = PARAMETERS.get('max_workers', 10)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
