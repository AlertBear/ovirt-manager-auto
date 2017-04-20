"""
Config module for Guest Tools
"""
import logging
from rhevmtests.system.config import *  # flake8: noqa

log = logging.getLogger('setup')

NIC_NAME = 'nic1'
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
