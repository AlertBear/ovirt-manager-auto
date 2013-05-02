from . import ART_CONFIG

__test__ = False

PARAMETERS = ART_CONFIG['PARAMETERS']
CLUSTER_NAME = PARAMETERS['cluster_name']
IMAGES = PARAMETERS['images']
TEMPLATE_NAMES = PARAMETERS.as_list('template_names')
WAIT_TIME = 120
BLOCK_FS = PARAMETERS['data_center_type'] in ('iscsi',)
STORAGE_TYPE = PARAMETERS['data_center_type']
STORAGE_CONF = ART_CONFIG[STORAGE_TYPE.upper()]
STORAGE_DOMAIN_NAME = "%s_%d" % (STORAGE_TYPE.lower(), 0)
TESTNAME = 'hotplug'

# cobbler related settings
COBBLER_ADDRESS = PARAMETERS['cobbler_address']
COBBLER_USER = PARAMETERS['cobbler_user']
COBBLER_PASSWORD = PARAMETERS['cobbler_passwd']

MAX_WORKERS = PARAMETERS.get('max_workers', 10)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
