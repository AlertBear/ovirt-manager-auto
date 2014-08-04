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
VM_NAME = ["_".join([TEST_NAME, 'vm', str(num)]) for num in xrange(1, 6)]
TEMPLATE_NAME = ["".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]
STORAGE_NAME = ["".join([elm, "_data_domain0"]) for elm in DC_NAME]
LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')
LUN = PARAMETERS.as_list('lun')
MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')
HOST_NICS = PARAMETERS.as_list('host_nics')
NIC_NAME = ["nic1", "nic2", "nic3", "nic4", "nic5", "nic6", "nic7", "nic8",
                                                                    "nic9"]
DISPLAY_TYPE = ENUMS['display_type_spice']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
PGPASS = "123456"
MB = 1024 ** 2
GB = 1024 ** 3
DISK_SIZE = 5 * GB
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_INTERFACE = ENUMS['interface_virtio']
