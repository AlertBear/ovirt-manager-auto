"""
Config module for Guest Agent
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

# Our chance to access config object of config file
from . import ART_CONFIG
import logging
# Name of the test
TESTNAME = "RHEL guest agent"
log = logging.getLogger('setup')
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']


DATA_CENTER_NAME = PARAMETERS.get('dc_name', "datacenter_%s" % TESTNAME)

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
CLUSTER_NAME = PARAMETERS['cluster_name']
STORAGE_DOMAIN = PARAMETERS['storage_domain']
EXPORT_STORAGE_DOMAIN = PARAMETERS['export_storage_domain']
VDS = PARAMETERS.as_list('vds')
VDS_PASSWORD = PARAMETERS.as_list('vds_password')

USER_ROOT = PARAMETERS['user_root']
USER_PASSWORD = PARAMETERS['user_password']
EXPORT_DOMAIN_ADDRESS = PARAMETERS['exportaddress']
EXPORT_DOMAIN_PATH = PARAMETERS['exportpath']
SUBNET_CLASS = PARAMETERS.get('subnet_class', '10')

RHEL_6_64b = PARAMETERS['rhel_6_64b']
RHEL_6_32b = PARAMETERS['rhel_6_32b']
RHEL_5_32b = PARAMETERS['rhel_5_32b']
RHEL_5_64b = PARAMETERS['rhel_5_64b']
TCMS_PLAN_ID = 3146
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
INSTALL_TIMEOUT = PARAMETERS.get('install_timeout', 480)
