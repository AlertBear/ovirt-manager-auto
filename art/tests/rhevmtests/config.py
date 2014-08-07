"""
Consolidated config module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG, opts

GOLDEN_ENV = False

# RHEVM related constants
ENUMS = opts['elements_conf']['RHEVM Enums']
PERMITS = opts['elements_conf']['RHEVM Permits']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']

TEST_NAME = "Global"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_CONF = ART_CONFIG['STORAGE']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']

PRODUCT_NAME = PARAMETERS['product_name']

# ENGINE SECTION
VDC_HOST = REST_CONNECTION['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
VDC_ROOT_USER = "root"
VDC_PASSWORD = REST_CONNECTION['password']
VDC_PORT = REST_CONNECTION['port']
VDC_ADMIN_USER = REST_CONNECTION['user']
VDC_ADMIN_DOMAIN = REST_CONNECTION['user_domain']
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']

# DATABASE SECTION - TODO: make it configurable
DB_ENGINE_HOST = VDC_HOST
DB_ENGINE_NAME = "engine"
DB_ENGINE_USER = "engine"
DB_ENGINE_PASSWORD = "123456"
DB_DWH_HOST = VDC_HOST
DB_DWH_NAME = "ovirt_engine_history"
DB_DWH_USER = "ovirt_engine_history"
DB_DWH_PASSWORD = "123456"
DB_REPORTS_HOST = VDC_HOST
DB_REPORTS_NAME = "ovirt_engine_reports"
DB_REPORTS_USER = "ovirt_engine_reports"
DB_REPORTS_PASSWORD = "123456"

# DATA CENTER SECTION
DC_NAME = ["_".join([TEST_NAME, "DC", str(i)]) for i in range(1, 6)]
# CLUSTER SECTION
CLUSTER_NAME = ["_".join([TEST_NAME, "Cluster", str(i)]) for i in range(1, 6)]
CPU_NAME = PARAMETERS['cpu_name']
CPU_CORES = PARAMETERS['cpu_cores']
CPU_SOCKET = PARAMETERS['cpu_socket']
COMP_VERSION = PARAMETERS['compatibility_version']
# HOST SECTION
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
HOST_OS = PARAMETERS['host_os']
# STORAGE SECTION
STORAGE_TYPE = PARAMETERS['storage_type']
UNCOMP_DC_NAME = PARAMETERS.get("dc_name", "%s_DC30" % TEST_NAME)
UNCOMP_CL_NAME = ["".join([CLUSTER_NAME[0], "CL3", str(i)]) for i in range(2)]
VERSION = ["3.0", "3.1", "3.2", "3.3", "3.4"]
SAMPLER_TIMEOUT = 60
CONNECT_TIMEOUT = 60
VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
VM_NAME = ["_".join([TEST_NAME, 'vm', str(num)]) for num in xrange(1, 6)]
TEMPLATE_NAME = ["".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]
STORAGE_NAME = [
    "_".join(
        [
            STORAGE_TYPE.lower(),
            str(i)
        ]
    ) for i in xrange(
        int(
            STORAGE_CONF.get(
                "%s_devices" % STORAGE_TYPE.lower(),
                0
            )
        )
    )
]
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
INSTALLATION = PARAMETERS.get('installation', 'true')
PGPASS = "123456"
MB = 1024 ** 2
GB = 1024 ** 3
DISK_SIZE = 5 * GB
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_INTERFACE = ENUMS['interface_virtio']
# USERS & ROLES
AD_USER_DOMAIN = PARAMETERS['ad_user_domain']
AD_USERNAME = PARAMETERS['ad_user']
AD_USER_NO_ROLES = PARAMETERS['no_roles_user']

# MISC PARAMETERS
MAX_WORKERS = PARAMETERS.get('max_workers', 10)
