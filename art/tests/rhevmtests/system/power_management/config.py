"""
power management config module
"""

__test__ = False

from rhevmtests.system.config import *  # flake8: noqa
import copy

from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']
VM_TYPE = ENUMS['vm_type_server']
FORMAT = ENUMS['format_raw']
FENCE_RESTART = ENUMS['fence_type_restart']
FENCE_START = ENUMS['fence_type_start']
FENCE_STOP = ENUMS['fence_type_stop']
FENCE_STATUS = ENUMS['fence_type_status']
HOST_STATE_CONNECTING = ENUMS['host_state_connecting']
HOST_STATE_NONOP = ENUMS['host_state_non_operational']
HOST_STATE_UP = ENUMS['host_state_up']
HOST_STATE_DOWN = ENUMS['host_state_down']
HOST_STATE_NON_RES = ENUMS['host_state_non_responsive']
MIGRATABLE = ENUMS['vm_affinity_migratable']
VM_STATE_DOWN = ENUMS['vm_state_down']


TEST_NAME = "power_management"
PARAMETERS = ART_CONFIG['PARAMETERS']

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])
STORAGE['data_domain_path'] = [PARAMETERS.as_list('data_domain_path')[0]]
STORAGE['data_domain_address'] = [PARAMETERS.as_list('data_domain_address')[0]]

PM1_ADDRESS = PARAMETERS['pm_address_ipmilan']
PM2_ADDRESS = PARAMETERS['pm_address_apc_snmp']
PM1_USER = PARAMETERS['pm_username_ipmilan']
PM2_USER = PARAMETERS['pm_username_apc_snmp']
PM1_PASS = PARAMETERS['pm_password_ipmilan']
PM2_PASS = PARAMETERS['pm_password_apc_snmp']
PM2_SLOT = PARAMETERS['pm_slot']