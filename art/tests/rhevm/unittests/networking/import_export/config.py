
"""
Import Export config module
"""

__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "Imp_Exp"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['storage_type']
DC_NAME = ["".join([TEST_NAME, "_DC", str(i)]) for i in range(2)]
CLUSTER_NAME = ["".join([TEST_NAME, "_Cluster", str(i)]) for i in range(2)]
CPU_NAME = PARAMETERS['cpu_name']
STORAGE_NAME = ["".join([elm, "_data_domain0"]) for elm in DC_NAME]
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = ["3.3", "3.4"]

HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
VDC_USER = "root"
LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')
LUN = PARAMETERS.as_list('lun')

HOST_NICS = PARAMETERS.as_list('host_nics')
NETWORKS = PARAMETERS.as_list('networks')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
MTU = [9000, 1500]
VM_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
           PARAMETERS.as_list('vm_name')]
TEMPLATE_NAME = ["".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM"
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE"
IMP_VM = ["_".join([VM_NAME[i], "Imported"]) for i in range(2)]
VM_OS = PARAMETERS['vm_os']
VNIC_PROFILE = PARAMETERS['vnic_profile']
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)

NIC_NAME = ["nic2", "nic3", "nic4", "nic5", "nic6", "nic7", "nic8", "nic9"]
DISK_TYPE = ENUMS['disk_type_system']
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']
NONOPERATIONAL = ENUMS['host_state_non_operational']
NONRESPONSIVE = ENUMS['host_state_non_responsive']
MAINTENANCE = ENUMS['host_state_maintenance']
EXPORT_TYPE = ENUMS['storage_dom_type_export']

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
RHEVM_NAME = REST_CONNECTION['host']

EXPORT_STORAGE_NAME = "Export"
EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]
