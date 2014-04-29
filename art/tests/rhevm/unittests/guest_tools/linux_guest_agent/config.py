"""
Config module for Guest Agent
"""

__test__ = False

from . import ART_CONFIG
from utilities.enum import Enum


eOS = Enum(RHEL_6_64b='RHEL_6_64b', RHEL_6_32b='RHEL_6_32b',
           RHEL_5_64b='RHEL_5_64b', RHEL_5_32b='RHEL_5_32b',
           UBUNTU_14_04_64b='UBUNTU_14_04_64b',
           SUSE_13_1_64b='SUSE_13_1_64b')
TESTNAME = "RHEL guest agent"
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
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
INSTALL_TIMEOUT = PARAMETERS.get('install_timeout', 480)
TIMEOUT = PARAMETERS.get('timeout', 320)

TEMPLATES = {eOS.RHEL_6_64b: {'name': PARAMETERS['rhel_6_64b']},
             eOS.RHEL_6_32b: {'name': PARAMETERS['rhel_6_32b']},
             eOS.RHEL_5_64b: {'name': PARAMETERS['rhel_5_32b']},
             eOS.RHEL_5_32b: {'name': PARAMETERS['rhel_5_64b']},
             eOS.UBUNTU_14_04_64b: {'name': PARAMETERS['ubuntu_14_04_64b']}}
# eOS.SUSE_13_1_64b: {'name': PARAMETERS['suse_13_1_64b']}}

AGENT_SERVICE_NAME = 'ovirt-guest-agent'

# TCMS plans
TCMS_PLAN_ID_RHEL = 3146
TCMS_PLAN_ID_UBUNTU = 12286
TCMS_PLAN_ID_SUSE = 12287

# GA repositories
UBUNTU_REPOSITORY = PARAMETERS.get('latest_ubuntu_34')
SUSE_REPOSITORY = PARAMETERS.get('latest_suse_34')
RHEL_REPOSITORY = PARAMETERS.get('latest_rhel_34')
RHEL_BEFORE_REPOSITORY = PARAMETERS.get('before_repo_rhel_34')
