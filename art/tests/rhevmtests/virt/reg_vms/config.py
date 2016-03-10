"""
Virt - Reg vms
"""
from rhevmtests.virt.config import *  # flake8: noqa

TWO_GB = 2 * GB
NIC_NAME = 'nic'
WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
RHEL_TZ = ENUMS['timezone_rhel_etc_gmt']
# Timeout for VM creation in Vmpool
VMPOOL_TIMEOUT = 30
RHEL6_64 = ENUMS['rhel6x64']
WIN_2008 = ENUMS['windows2008r2x64']
WIN_7 = ENUMS['windows7']

ticket_expire_time = 120
template_name = TEMPLATE_NAME[0]
