"""
Config module for data center sanity tests
"""

# This must be here so nose doesn't consider this as a test
__test__ = False


from art.test_handler import settings
from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
ENUMS = settings.opts['elements_conf']['RHEVM Enums']
PERMITS = settings.opts['elements_conf']['RHEVM Permits']

TESTNAME = 'Regression mixed'
PRODUCT_NAME = PARAMETERS['product_name']

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
VDS_PASSWORD = PARAMETERS.as_list('vds_password')[0]
VDC_PORT = REST_CONNECTION['port']

DATA_CENTER_1_NAME = PARAMETERS['data_center_1_name']
DATA_CENTER_1_NAME_UPDATED = PARAMETERS['data_center_1_name_updated']
DATA_CENTER_2_NAME = PARAMETERS['data_center_2_name']
DATA_CENTER_3_NAME = PARAMETERS['data_center_3_name']

CPU_NAME = PARAMETERS['cpu_name']

CLUSTER_1_NAME = PARAMETERS['cluster_1_name']
CLUSTER_2_NAME = PARAMETERS['cluster_2_name']
CLUSTER_3_NAME = PARAMETERS['cluster_3_name']
CLUSTER_4_NAME = PARAMETERS['cluster_4_name']

HOST_NAME = PARAMETERS.as_list('vds')[0]

STORAGE_TYPE = PARAMETERS['storage_type']
STORAGE_DOMAIN_NAME = PARAMETERS['storage_domain_name']
DATA_DOMAIN_ADDRESS = PARAMETERS.as_list('data_domain_address')[0]
DATA_DOMAIN_PATH = PARAMETERS.as_list('data_domain_path')[0]

VM_NAME = PARAMETERS['vm_name']
TEMPLATE_NAME = PARAMETERS['template_name']

USER_VDCADMIN = PARAMETERS['vdc_user']
USERNAME = PARAMETERS['new_user']
USER_DOMAIN = PARAMETERS['ad_user_domain']
USER_NO_ROLES = PARAMETERS['no_roles_user']
USER_NON_EXISTING = PARAMETERS['not_existing_user']

TAG_1_NAME = PARAMETERS['tag_1_name']
TAG_2_NAME = PARAMETERS['tag_2_name']
TAG_3_NAME = PARAMETERS['tag_3_name']
TAG_4_NAME = PARAMETERS['tag_4_name']
TAG_5_NAME = PARAMETERS['tag_5_name']
TAG_SUB_NAME = PARAMETERS['tag_sub_name']
GROUP = PARAMETERS['group']

ENTRY_POINT = REST_CONNECTION['entry_point']
