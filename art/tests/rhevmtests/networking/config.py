"""
network config module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG, opts

TEST_NAME = "Network"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']

DC_NAME = ["".join([TEST_NAME, "_DC", str(i)]) for i in range(5)]
CLUSTER_NAME = ["".join([TEST_NAME, "_Cluster", str(i)]) for i in range(5)]
CPU_NAME = PARAMETERS['cpu_name']

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
RHEVM_NAME = REST_CONNECTION['host']
VDC = PARAMETERS.get('host', None)
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', None)
VDC_PASSWORD = PARAMETERS.get('vdc_password', None)
VDC_USER = "root"

COMP_VERSION = PARAMETERS['compatibility_version']
UNCOMP_DC_NAME = PARAMETERS.get("dc_name", "%s_DC30" % TEST_NAME)
UNCOMP_CL_NAME = ["".join([CLUSTER_NAME[0], "CL3", str(i)]) for i in range(2)]
VERSION = ["3.0", "3.1", "3.2", "3.3", "3.4"]

HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'

VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           PARAMETERS.as_list('vm_name')]
TEMPLATE_NAME = ["".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]

STORAGE_NAME = ["".join([elm, "_data_domain0"]) for elm in DC_NAME]
STORAGE_TYPE = PARAMETERS['storage_type']
LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')
LUN = PARAMETERS.as_list('lun')

MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')
HOST_NICS = PARAMETERS.as_list('host_nics')
NETWORKS = PARAMETERS.as_list('networks')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
BOND_MODES = PARAMETERS.as_list("bond_modes")
MTU = [9000, 5000, 2000, 1500]
NIC_NAME = ["nic1", "nic2", "nic3", "nic4", "nic5", "nic6", "nic7", "nic8",
                                                                    "nic9"]
VNIC_PROFILE = PARAMETERS.as_list('vnic_profile')
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']

NETMASK = '255.255.255.0'

# Network Migration
NM_SOURCE_IP = '101.1.1.1'
NM_DEST_IP = '101.1.1.2'

# MultiHost parameters
TIMEOUT = 60
SUBNET = "1.1.1.0"
MG_GATEWAY = "1.1.1.254"

# Network migration parameters
FIREWALL_SRV = "iptables"

# Jumbo frame parameters
VM_NICS = ['eth0', 'eth1', 'eth2', 'eth3']
NUM_PACKETS = 1000
INTER_SUBNET = '3.3.3.'
IPS = ['3.3.3.1', '3.3.3.2']
SEND_MTU = [4500, 8500, 1500, 1000]
SOURCE_IP = '100.1.1.1'
DEST_IP = '100.1.1.2'
GATEWAY = '3.3.3.254'
TRAFFIC_TIMEOUT = 120
CONNECT_TIMEOUT = 60
J_VLAN_NETWORKS = ['sw201', 'sw202', 'sw203', 'sw204', 'sw205']
J_VLAN_ID = ['201', '202', '203', '204', '205']

# Import/Export parameters
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM"
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE"
EXPORT_TYPE = ENUMS['storage_dom_type_export']
EXPORT_STORAGE_NAME = "Export"
EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]

# Topologies parameters
ADDR_AND_MASK = ["172.16.200.100", "255.255.255.0"]
DST_HOST_IP = "172.16.200.2"

# Port mirroring parameters
PM_VNIC_PROFILE = ['%s_PM' % net for net in [MGMT_BRIDGE] + VLAN_NETWORKS]
NUM_VMS = 5
MGMT_IPS = []  # Gets filled up during the test
NET1_IPS = ['5.5.5.1%s' % i for i in range(NUM_VMS + 1)]
NET2_IPS = ['6.6.6.1%s' % i for i in range(NUM_VMS + 1)]
NET2_TEMP_IP = '6.6.6.100'

# VERSION = ["3.3", "3.4"]  # import-export
# DATA_NAME = PARAMETERS.get('data_domain_name', '%s_storage' % TEST_NAME)
# DATA_PATHS = PARAMETERS.as_list('data_domain_path')
# DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
# STORAGE_NAME = '%s_data_domain0' % DC_NAME
# STORAGE_DOMAIN_NAME = '%s_data_domain0' % DC_NAME     portMirroring
# DC_NAME = PARAMETERS.get('dc_name', '%s_DC' % TEST_NAME)
# CLUSTER_NAME = PARAMETERS.get('cluster_name', '%s_Cluster' % TEST_NAME)
# USE_AGENT = PARAMETERS['useAgent']
# J_MTU = [5000, 9000, 2000, 1500]
# VM_NIC_NAMES = ['nic1', 'nic2', 'nic3']   Jumbo
# VM_NICS = ['nic1', 'nic2', 'nic3']    portMirroring
# For profiles with port mirroring:
# PM_VNIC_PROFILE = ['%s_PM' % net for net in [MGMT_BRIDGE] + VLAN_NETWORKS]
# DISK_TYPE = ENUMS['disk_type_system']
# IMP_VM = ["_".join([VM_NAME[i], "Imported"]) for i in range(2)]
# VM_OS = PARAMETERS['vm_os']
# NONOPERATIONAL = ENUMS['host_state_non_operational']
# NONRESPONSIVE = ENUMS['host_state_non_responsive']
# MAINTENANCE = ENUMS['host_state_maintenance']
