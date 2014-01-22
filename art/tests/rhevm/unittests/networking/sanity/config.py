"""
sanity config module
"""

__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "Network_Sanity"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['data_center_type']

DC_NAME = PARAMETERS.get('dc_name', '%s_DC' % TEST_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', '%s_Cluster' % TEST_NAME)
CPU_NAME = PARAMETERS['cpu_name']
STORAGE_NAME = '%s_data_domain0' % DC_NAME
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
LUN_TARGET = PARAMETERS.as_list('lun_target')[0]
LUN_ADDRESS = PARAMETERS.as_list('lun_address')[0]
LUN = PARAMETERS.as_list('lun')[0]
TIMEOUT = 7200

#import_export domain
EXPORT_STORAGE_NAME = 'Sanity_DC_export_domain'
EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]

HOST_NICS = PARAMETERS.as_list('host_nics')
NETWORKS = PARAMETERS.as_list('networks')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           PARAMETERS.as_list('vm_name')]
TEMPLATE_NAME = "".join(['%s_', PARAMETERS['template_name']]) % TEST_NAME
VM_OS = PARAMETERS['vm_os']
VNIC_PROFILE = PARAMETERS['vnic_profile']
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)

DISK_TYPE = ENUMS['disk_type_system']
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']
NONOPERATIONAL = ENUMS['host_state_non_operational']
NONRESPONSIVE = ENUMS['host_state_non_responsive']
MAINTENANCE = ENUMS['host_state_maintenance']

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
RHEVM_NAME = REST_CONNECTION['host']
