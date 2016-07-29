"""
Config module for Guest Tools
"""

__test__ = False

import logging
from rhevmtests.system.config import *  # flake8: noqa

log = logging.getLogger('setup')

GLANCE_NAME = 'rhevm-qe-infra-glance'

WIN7_DISK_64b = 'Windows7_64b_Disk1'
WIN7_DISK_32b = 'Windows7_32b_Disk1'
WIN8_DISK_64b = 'windows8_x64_Disk1'
WIN8_DISK_32b = 'windows8_x86_Disk1'
WIN8_1_DISK_64b = 'windows8.1_x64_Disk1'
WIN8_1_DISK_32b = 'windows8.1_x86_Disk1'
WIN2008_DISK_32b = 'Windows_2008_x86_Disk1'
WIN2008_DISK_64b = 'Windows_2008_x64_Disk1'
WIN2008R2_DISK_64b = 'Windows_2008R2_x64_Disk1'
WIN2012_DISK_64b = 'Windows_2012_x64_Disk1'
WIN2012R2_DISK_64b = 'Windows_20012R2_x64_Disk1'
WIN10_DISK_64b = 'win10_Disk1'

NIC_NAME = 'nic1'

CD_WITH_TOOLS = RHEVM_UTILS_ENUMS['CD_WITH_TOOLS']
SUBNET_CLASS = '10'

if GOLDEN_ENV:
    EXPORT_STORAGE_DOMAIN = EXPORT_DOMAIN_NAME
    ISO_STORAGE_DOMAIN = ISO_DOMAIN_NAME
else:
    EXPORT_STORAGE_DOMAIN = PARAMETERS.get('export_name', None)
    ISO_STORAGE_DOMAIN = PARAMETERS.get('iso_name', None)
    ISO_DOMAIN_PATH = PARAMETERS.get('iso_path', None)
    ISO_DOMAIN_ADDRESS = PARAMETERS.get('iso_address', None)
    EXPORT_DOMAIN_PATH = PARAMETERS.get('export_path', None)
    EXPORT_DOMAIN_ADDRESS = PARAMETERS.get('export_address', None)
