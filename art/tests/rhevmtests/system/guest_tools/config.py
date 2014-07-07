"""
Config module for Guest Tools
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

# Our chance to access config object of config file
#from art.test_handler.settings import ART_CONFIG
import logging
from rhevmtests.system.config import *  # flake8: noqa

# Name of the test
TEST_NAME = "Guest_Tools"
log = logging.getLogger('setup')
#DC_NAME = "gt_datacenter"
# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)
#CLUSTER_NAME = 'ClusterForGT'
STORAGE_DOMAIN = 'nfs_0'
ISO_STORAGE_DOMAIN = 'iso'
EXPORT_STORAGE_DOMAIN = 'tlv-export'
WIN7_TEMPLATE_NAME = 'dk-win7-64'
WIN7_IMPORTED_TEMPLATE_NAME = 'dk-win7-64'
WIN7_VM_NAME = "GTwin764"
# VDS = PARAMETERS['vds']
# VDS_PASSWORD = PARAMETERS['vds_password']
VM_USER = 'admin'
#  should be in global conf VM_PASSWORD = PARAMETERS['VM_password']
TOOLSVERSION = 3.3.5
TOOLS_DICT = '{ "RHEV-Tools":"3.2.8"   , "RHEV-Agent":"3.2.5"  , "RHEV-Serial":"3.2.4", \
                "RHEV-Network":"3.2.4" , "RHEV-Block":"3.2.4"  , "RHEV-Spice-Agent":"3.2.5", \
                "RHEV-USB":"3.2.3"     , "RHEV-SSO":"3.2.4"    , "RHEV-Spice":"3.2.3"}'
VM_LIST = '{"Windows7":"x64"}'
CD_WITH_TOOLS = 'RHEV-toolsSetup_3.3_10.iso'
SUBNET_CLASS = 10

EXPORT_DOMAIN_ADDRESS = 'lion.qa.lab.tlv.redhat.com'
ISO_DOMAIN_ADDRESS = 'lion.qa.lab.tlv.redhat.com'
EXPORT_DOMAIN_PATH = '/export/virt-qe-export'
ISO_DOMAIN_PATH = '/export/guest_tools'

win7_32_template_name = dk-win7-32
win7_32_imported_template_name = dk-win7-32
win7_32_VM_name = "GTwin732"
winXP_template_name = dk-winxp
winXP_imported_template_name = dk-winxp
winXP_VM_name = "GTwinXP"

WIN7_tools_dict = """{"RHEV-Agent":"3.3.3",
"RHEV-Block":"3.3.1", "RHEV-Network":"3.3.1",
"RHEV-Serial":"3.3.1", "RHEV-Spice-Agent":"3.3.1",
"RHEV-SSO":"3.3.1", "RHEV-USB":"3.3.1", "RHEV-Spice":"3.3.1"}"""
WINXP_tools_dict = """{"RHEV-Tools":"3.2.8", "RHEV-Agent":"3.2.5",
"RHEV-Serial":"3.2.4", "RHEV-Network":"3.2.4", "RHEV-Spice-Agent":"3.2.5",
"RHEV-USB":"3.2.3", "RHEV-SSO":"3.2.4", "RHEV-Spice":"3.2.3"}"""
skip_install = 0
skip_uninstall = 1