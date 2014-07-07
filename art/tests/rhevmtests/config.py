"""
Consolidated config module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG, opts

# RHEVM related constants
ENUMS = opts['elements_conf']['RHEVM Enums']

TEST_NAME = "Global"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_CONF = ART_CONFIG['STORAGE']


# ENGINE SECTION
VDC_HOST = ART_CONFIG['REST_CONNECTION']['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
VDC_PASSWORD = ART_CONFIG['REST_CONNECTION']['password']
VDC_USER = "root"
# DATA CENTER SECTION
DC_NAME = ["".join([TEST_NAME, "_DC", str(i)]) for i in range(5)]
# CLUSTER SECTION
CLUSTER_NAME = ["".join([TEST_NAME, "_Cluster", str(i)]) for i in range(5)]
CPU_NAME = PARAMETERS['cpu_name']
CPU_CORES = PARAMETERS['cpu_cores']
CPU_SOCKET = PARAMETERS['cpu_socket']
COMP_VERSION = PARAMETERS['compatibility_version']
# STORAGE SECTION
STORAGE_TYPE = PARAMETERS['storage_type']
UNCOMP_DC_NAME = PARAMETERS.get("dc_name", "%s_DC30" % TEST_NAME)
UNCOMP_CL_NAME = ["".join([CLUSTER_NAME[0], "CL3", str(i)]) for i in range(2)]
VERSION = ["3.0", "3.1", "3.2", "3.3", "3.4"]
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
HOST_OS = PARAMETERS['host_os']
SAMPLER_TIMEOUT = 60
CONNECT_TIMEOUT = 60
VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           PARAMETERS.as_list('vm_name')]
TEMPLATE_NAME = ["".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]
STORAGE_NAME = ["".join([elm, "_data_domain0"]) for elm in DC_NAME]
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
MB = 1024 ** 2
GB = 1024 ** 3
DISK_SIZE = 5 * GB
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_INTERFACE = ENUMS['interface_virtio']
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
PGPASS = "123456"
