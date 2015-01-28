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

STORAGE_DOMAIN = 'nfs_0'
ISO_STORAGE_DOMAIN = 'iso'
EXPORT_STORAGE_DOMAIN = 'tlv-export'
EXPORT_DOMAIN_ADDRESS = 'lion.qa.lab.tlv.redhat.com'
ISO_DOMAIN_ADDRESS = 'lion.qa.lab.tlv.redhat.com'
EXPORT_DOMAIN_PATH = '/export/virt-qe-export'
ISO_DOMAIN_PATH = '/export/guest_tools'
