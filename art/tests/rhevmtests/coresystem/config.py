"""
 CoreSystem config
"""
from rhevmtests.config import *  # flake8: noqa

PM1_TYPE = 'ipmilan'
PM2_TYPE = 'apc_snmp'

HOST_FALSE_IP = '10.1.1.256'
ISO_IMAGE = PARAMETERS.get('iso_image', None)
