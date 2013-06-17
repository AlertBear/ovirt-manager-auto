"""
Migration config module
"""

__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "Migration"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['data_center_type']

basename = PARAMETERS.get('TEST_NAME', 'test')
DC_NAME = PARAMETERS.get('dc_name', '%s_DC' % basename)
CLUSTER_NAME = PARAMETERS.get('cluster_name', '%s_Cluster' % basename)
CPU_NAME = PARAMETERS['cpu_name']
DATA_NAME = PARAMETERS.get('data_domain_name', '%s_storage' % basename)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')
HOSTS_USER = 'root'
LUN_TARGET = PARAMETERS.as_list('lun_target')[0]
LUN_ADDRESS = PARAMETERS.as_list('lun_address')[0]
LUN = PARAMETERS.as_list('lun')[0]

HOST_NICS = PARAMETERS.as_list('host_nics')
NETWORKS = PARAMETERS.as_list('networks')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
VM_NAME = PARAMETERS.as_list('vm_name')
TEMPLATE_NAME = PARAMETERS['template_name']
VM_OS = PARAMETERS['vm_os']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)

DISK_TYPE = ENUMS['disk_type_system']
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']
