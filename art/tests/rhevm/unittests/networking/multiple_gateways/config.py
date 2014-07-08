"""
Multiple Gateways network config module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "Multiple_Gateways"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['storage_type']

DC_NAME = PARAMETERS.get('dc_name', '%s_DC' % TEST_NAME)
DC_NAME2 = PARAMETERS.get('dc_name', '%s_DC2' % TEST_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', '%s_Cluster' % TEST_NAME)
CLUSTER_NAME2 = PARAMETERS.get('cluster_name', '%s_Cluster2' % TEST_NAME)
CPU_NAME = PARAMETERS['cpu_name']
STORAGE_NAME = '%s_data_domain0' % DC_NAME
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
LUN_TARGET = PARAMETERS.as_list('lun_target')[0]
LUN_ADDRESS = PARAMETERS.as_list('lun_address')[0]
LUN = PARAMETERS.as_list('lun')[0]

HOST_NICS = PARAMETERS.as_list('host_nics')
NETWORKS = PARAMETERS.as_list('networks')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           PARAMETERS.as_list('vm_name')]
TEMPLATE_NAME = "".join(['%s_', PARAMETERS['template_name']]) % TEST_NAME
VM_OS = PARAMETERS['vm_os']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)

DISK_TYPE = ENUMS['disk_type_system']
DISPLAY_TYPE = ENUMS['display_type_spice']
NONOPERATIONAL = ENUMS['host_state_non_operational']
NONRESPONSIVE = ENUMS['host_state_non_responsive']
MAINTENANCE = ENUMS['host_state_maintenance']
