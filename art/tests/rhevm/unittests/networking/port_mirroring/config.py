"""
Port Mirroring config module
"""

__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "PortMirroring"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['data_center_type']

DC_NAME = PARAMETERS.get('dc_name', '%s_DC' % TEST_NAME)
STORAGE_DOMAIN_NAME = '%s_data_domain0' % DC_NAME
CLUSTER_NAME = PARAMETERS.get('cluster_name', '%s_Cluster' % TEST_NAME)
CPU_NAME = PARAMETERS['cpu_name']
DATA_NAME = PARAMETERS.get('data_domain_name', '%s_storage' % TEST_NAME)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']

HOSTS = PARAMETERS.get('vds')
HOSTS_PW = PARAMETERS.get('vds_password')
HOSTS_USER = 'root'
HOST_NICS = PARAMETERS.as_list('host_nics')

LUN_TARGET = PARAMETERS.as_list('lun_target')[0]
LUN_ADDRESS = PARAMETERS.as_list('lun_address')[0]
LUN = PARAMETERS.as_list('lun')[0]

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
# For profiles with port mirroring:
VNIC_PROFILE = ['%s_PM' % net for net in [MGMT_BRIDGE] + VLAN_NETWORKS]

VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           ['VMTest1', 'VMTest2', 'VMTest3', 'VMTest4', 'VMTest5']]
TEMPLATE_NAME = "".join(['%s_', PARAMETERS['template_name']]) % TEST_NAME
VM_OS = PARAMETERS['vm_os']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']
USE_AGENT = PARAMETERS['useAgent']
VM_NICS = ['nic1', 'nic2', 'nic3']
NUM_VMS = 5  # Number of VM's used in the test

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)

DISK_TYPE = ENUMS['disk_type_system']
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']

# IP's for all networks:
RHEVM_IPS = []  # Gets filled up during the test
NET1_IPS = ['5.5.5.1%s' % i for i in range(NUM_VMS + 1)]
NET2_IPS = ['6.6.6.1%s' % i for i in range(NUM_VMS + 1)]
NET2_TEMP_IP = '6.6.6.100'
