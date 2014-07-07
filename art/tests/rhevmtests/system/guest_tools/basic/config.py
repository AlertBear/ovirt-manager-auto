"""
Config module for Guest Tools
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

# Our chance to access config object of config file
from art.test_handler.settings import ART_CONFIG
import logging
from rhevmtests.system.config import *  # flake8: noqa

# Name of the test
TEST_NAME = "GuestTools"
log = logging.getLogger('setup')
# PARAMETERS = ART_CONFIG['PARAMETERS']
#STORAGE_TYPE = PARAMETERS['storage_type']


# STORAGE_CONF = ART_CONFIG[STORAGE_TYPE.upper()]

#DC_NAME = 'DatacenterForGT'

# VM_NAME = PARAMETERS.get('vm_name', 'vm_name')

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)

#COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
#CLUSTER_NAME = 'ClusterForGT'
STORAGE_DOMAIN = 'nfs_0'
ISO_STORAGE_DOMAIN = 'iso'
EXPORT_STORAGE_DOMAIN = 'tlv-export'
#VDS = PARAMETERS['vds']
#VDS_PASSWORD = PARAMETERS['vds_password']
VM_USER = PARAMETERS['VM_user']
VM_PASSWORD = PARAMETERS['VM_password']
TOOLSVERSION = PARAMETERS['toolsVersion']
WINXP_TOOLS_DICT = '{"RHEV-Tools":"3.2.8", "RHEV-Agent":"3.2.5",\
                     "RHEV-Serial":"3.2.4", "RHEV-Network":"3.2.4",\
                     "RHEV-Spice-Agent":"3.2.5", "RHEV-USB":"3.2.3",\
                     "RHEV-SSO":"3.2.4", "RHEV-Spice":"3.2.3"}'
WIN7_TOOLS_DICT = '{ "RHEV-Tools":"3.2.8", "RHEV-Agent":"3.2.5",\
                     "RHEV-Serial":"3.2.4", "RHEV-Network":"3.2.4",\
                     "RHEV-Spice-Agent":"3.2.5", "RHEV-USB":"3.2.3",\
                     "RHEV-SSO":"3.2.4", "RHEV-Spice":"3.2.3"}'
VM_LIST = '{"Windows7":"x64"}'
CD_WITH_TOOLS = 'RHEV-toolsSetup_3.3_10.iso'
SUBNET_CLASS = 10
SKIP_UNINSTALL = 0
SKIP_INSTALL = 1


WIN7_TEMPLATE_NAME = 'dk-win7-64'
WIN7_IMPORTED_TEMPLATE_NAME = 'dk-win7-64'
WIN7_VM_NAME = "GTwin764"

WIN7_32_TEMPLATE_NAME = 'dk-win7-32'
WIN7_32_IMPORTED_TEMPLATE_NAME = 'dk-win7-32'
WIN7_32_VM_NAME = 'GTwin732'


WINXP_TEMPLATE_NAME = 'dk-winxp'
WINXP_IMPORTED_TEMPLATE_NAME = 'dk-winxp'
WINXP_VM_NAME = 'GTwinXP'






MGMT_BRIDGE = PARAMETERS['mgmt_bridge']


EXPORT_DOMAIN_ADDRESS = 'lion.qa.lab.tlv.redhat.com'
ISO_DOMAIN_ADDRESS = 'lion.qa.lab.tlv.redhat.com'
EXPORT_DOMAIN_PATH = '/export/virt-qe-export'
ISO_DOMAIN_PATH = '/export/guest_tools'


