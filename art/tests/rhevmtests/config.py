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
ENGINE_URL = '%s://%s:%s/%s' % (
    REST_CONNECTION.get('scheme'),
    VDC_HOST,
    VDC_PORT,
    ENGINE_ENTRY_POINT
)

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

# # DATA CENTER SECTION
DC_NAME = ["_".join([TEST_NAME, "DC", str(i)]) for i in range(1, 6)]
PARAMETERS['dc_name'] = DC_NAME[0]
# CLUSTER SECTION
CLUSTER_NAME = ["_".join([TEST_NAME, "Cluster", str(i)]) for i in range(1, 6)]
PARAMETERS['cluster_name'] = CLUSTER_NAME[0]
CPU_NAME = PARAMETERS['cpu_name']
CPU_SOCKET = PARAMETERS.get('cpu_socket', 2)
CPU_CORES = PARAMETERS.get('cpu_cores', 2)

USE_AGENT = PARAMETERS['useAgent']
COMP_VERSION = PARAMETERS['compatibility_version']

# HOST SECTION
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
HOST_OS = PARAMETERS['host_os']


# STORAGE SECTION
# Storage types
STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']
STORAGE_TYPE_FCP = ENUMS['storage_type_fcp']
STORAGE_TYPE_LOCAL = ENUMS['storage_type_local']
STORAGE_TYPE_POSIX = ENUMS['storage_type_posixfs']
STORAGE_TYPE_GLANCE = ENUMS['storage_type_glance']

STORAGE_TYPE = PARAMETERS['storage_type']

STORAGE_TYPE_PROVIDERS = [STORAGE_TYPE_GLANCE]
# We provision for posix with the subtype, like: "posixfs_subfix"
# For the moment just revert back
if STORAGE_TYPE.startswith(STORAGE_TYPE_POSIX):
    STORAGE_TYPE = STORAGE_TYPE_POSIX

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

# run on local DC?
LOCAL = STORAGE_TYPE == STORAGE_TYPE_LOCAL

LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')

if STORAGE_TYPE == STORAGE_TYPE_NFS:
    ADDRESS = PARAMETERS.as_list('data_domain_address')
    PATH = PARAMETERS.as_list('data_domain_path')
elif STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    LUNS = PARAMETERS.as_list('lun')
    LUN_ADDRESS = PARAMETERS.as_list('lun_address')
    LUN_TARGET = PARAMETERS.as_list('lun_target')
    LUN_PORT = 3260
elif STORAGE_TYPE == STORAGE_TYPE_POSIX:
    VFS_TYPE = (PARAMETERS['storage_type']).split("_")[1]
    if VFS_TYPE == "pnfs":
        VFS_TYPE = STORAGE_TYPE_NFS
        PARAMETERS['data_domain_mount_options'] = "vers=4.1"
    PARAMETERS['vfs_type'] = VFS_TYPE

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


# Disk interfaces
INTERFACE_VIRTIO = ENUMS['interface_virtio']
INTERFACE_IDE = ENUMS['interface_ide']
INTERFACE_VIRTIO_SCSI = ENUMS['interface_virtio_scsi']
DISK_INTERFACE = INTERFACE_VIRTIO

# Disk formats
DISK_FORMAT_COW = ENUMS['format_cow']
DISK_FORMAT_RAW = ENUMS['format_raw']

# Disk types
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_LOCKED = ENUMS['disk_state_locked']

# Disk sizes
MB = 1024 ** 2
GB = 1024 ** 3
DISK_SIZE = 5 * GB

# Storage Domain states
SD_ACTIVE = ENUMS['storage_domain_state_active']
SD_MAINTENANCE = ENUMS['storage_domain_state_maintenance']

# DC states
DATA_CENTER_PROBLEMATIC = ENUMS['data_center_state_problematic']

# VM states
VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['vm_affinity_migratable']
VM_UP = ENUMS['vm_state_up']
VM_DOWN = ENUMS['vm_state_down']
VM_POWER_UP = ENUMS['vm_state_powering_up']
VM_POWER_DOWN = ENUMS['vm_state_powering_down']
VM_SUSPENDED = ENUMS['vm_state_suspended']
VM_PAUSED = ENUMS['vm_state_paused']
VM_LOCKED = ENUMS["vm_state_image_locked"]
VM_DOWN_STATE = ENUMS["vm_state_down"]
VM_RESTORING = ENUMS['vm_state_restoring_state']
VM_SAVING = ENUMS['vm_state_saving_state']
VM_WAIT_FOR_LAUNCH = ENUMS['vm_state_wait_for_launch']
VM_POWERING_UP = ENUMS['vm_state_powering_up']


# VM types
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']

# Host states
HOST_UP = ENUMS['host_state_up']
HOST_NONOPERATIONAL = ENUMS["host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["host_state_non_responsive"]

# Snapshot states
SNAPSHOT_OK = ENUMS['snapshot_state_ok']

# Import/Export parameters
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM"
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE"
EXPORT_TYPE = ENUMS['storage_dom_type_export']
EXPORT_STORAGE_NAME = "Export"
EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]

ISO_DOMAIN_ADDRESS = PARAMETERS.as_list("tests_iso_domain_address")[0]
ISO_DOMAIN_PATH = PARAMETERS.as_list("tests_iso_domain_path")[0]

# USERS & ROLES
AD_USER_DOMAIN = PARAMETERS['ad_user_domain']
AD_USERNAME = PARAMETERS['ad_user']
AD_USER_NO_ROLES = PARAMETERS['no_roles_user']

# MISC PARAMETERS
MAX_WORKERS = PARAMETERS.get('max_workers', 10)

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
