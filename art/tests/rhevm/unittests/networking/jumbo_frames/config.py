"""
Jumbo Frames config module
"""

__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "Jumbo"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['storage_type']

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
LUN_TARGET = PARAMETERS.as_list('lun_target')[0]
LUN_ADDRESS = PARAMETERS.as_list('lun_address')[0]
LUN = PARAMETERS.as_list('lun')[0]

HOST_NICS = PARAMETERS.as_list('host_nics')
VM_NICS = ['eth0', 'eth1', 'eth2', 'eth3']
VM_NIC_NAMES = ['nic1', 'nic2', 'nic3']
BONDS = PARAMETERS.as_list('bond')
NETWORKS = PARAMETERS.as_list('networks')
VLAN_NETWORKS = ['sw201', 'sw202', 'sw203', 'sw204', 'sw205']
VLAN_ID = ['201', '202', '203', '204', '205']
VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           PARAMETERS.as_list('vm_name')]
TEMPLATE_NAME = "".join(['%s_', PARAMETERS['template_name']]) % TEST_NAME
VM_OS = PARAMETERS['vm_os']
NUM_PACKETS = 1000
INTER_SUBNET = '3.3.3.'
IPS = ['3.3.3.1', '3.3.3.2']
MTU = [5000, 9000, 2000, 1500]
SEND_MTU = [4500, 8500, 1500, 1000]
SOURCE_IP = '1.1.1.1'
DEST_IP = '1.1.1.2'
NETMASK = '255.255.255.0'
GATEWAY = '3.3.3.254'
TRAFFIC_TIMEOUT = 120
CONNECT_TIMEOUT = 60
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)

DISK_TYPE = ENUMS['disk_type_system']
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']
