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

WINDOWS_VM = 'windows_vm'
NIC_NAME = 'nic1'

ISO_DOMAIN_NAME = 'rhevm3iso'

# TODO: add genric name to this iso, currently need to be updated manually
CD_WITH_TOOLS = 'RHEV-toolsSetup_3.5_9.iso'
SUBNET_CLASS = '10'
