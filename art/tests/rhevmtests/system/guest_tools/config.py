"""
Config module for Guest Tools
"""

__test__ = False

import logging
from rhevmtests.system.config import *  # flake8: noqa

log = logging.getLogger('setup')

WIN7_TEMPLATE_NAME = 'dk-win7-64'
WIN7_VM_NAME = "GTwin764"
WIN7_32_TEMPLATE_NAME = "dk-win7-32"
WIN7_32_VM_NAME = "GTwin732"

CD_WITH_TOOLS = 'RHEV-toolsSetup_3.5_9.iso'
SUBNET_CLASS = '10'

EXPORT_STORAGE_DOMAIN = EXPORT_STORAGE_NAME if GOLDEN_ENV else 'tlv-export'
EXPORT_DOMAIN_ADDRESS = '10.35.160.108'
ISO_DOMAIN_ADDRESS = '10.35.160.108'
EXPORT_DOMAIN_PATH = '/RHEV/guest_tools_templates'
ISO_STORAGE_DOMAIN = 'iso'
ISO_DOMAIN_PATH = '/RHEV/guest_tools'
STORAGE_DOMAIN = 'nfs_0'
