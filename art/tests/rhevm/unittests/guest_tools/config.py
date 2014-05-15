"""
Config module for Guest Tools
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

# Our chance to access config object of config file
from art.test_handler.settings import ART_CONFIG
import logging
# Name of the test
TESTNAME = "Guest Tools"
log = logging.getLogger('setup')
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']


# STORAGE_CONF = ART_CONFIG[STORAGE_TYPE.upper()]

DATA_CENTER_NAME = PARAMETERS.get('dc_name', "datacenter_%s" % TESTNAME)

# VM_NAME = PARAMETERS.get('vm_name', 'vm_name')

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
CLUSTER_NAME = PARAMETERS['cluster_name']
STORAGE_DOMAIN = PARAMETERS['storage_domain']
ISO_STORAGE_DOMAIN = PARAMETERS['iso_storage_domain']
EXPORT_STORAGE_DOMAIN = PARAMETERS['export_storage_domain']
WIN7_TEMPLATE_NAME = PARAMETERS['win7_template_name']
WIN7_IMPORTED_TEMPLATE_NAME = PARAMETERS['win7_imported_template_name']
WIN7_VM_NAME = PARAMETERS['win7_VM_name']
VDS = PARAMETERS['vds']
VDS_PASSWORD = PARAMETERS['vds_password']
VM_USER = PARAMETERS['VM_user']
VM_PASSWORD = PARAMETERS['VM_password']
TOOLSVERSION = PARAMETERS['toolsVersion']
TOOLS_DICT = PARAMETERS['tools_dict']
VM_LIST = PARAMETERS['VM_list']
CD_WITH_TOOLS = PARAMETERS['cd_with_tools']
SUBNET_CLASS = PARAMETERS['subnet_class']

EXPORT_DOMAIN_ADDRESS = PARAMETERS['exportaddress']
ISO_DOMAIN_ADDRESS = PARAMETERS['isoaddress']
EXPORT_DOMAIN_PATH = PARAMETERS['exportpath']
ISO_DOMAIN_PATH = PARAMETERS['isopath']
