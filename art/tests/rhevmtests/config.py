"""
Consolidated config module
"""

__test__ = False

import logging

from art.test_handler.settings import ART_CONFIG, opts
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api import resources

logger = logging.getLogger(__name__)

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
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'

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

USE_AGENT = PARAMETERS['useAgent']

# STORAGE SECTION
STORAGE_TYPE = PARAMETERS.get('storage_type', None)

STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']
STORAGE_TYPE_FCP = ENUMS['storage_type_fcp']
STORAGE_TYPE_LOCAL = ENUMS['storage_type_local']
STORAGE_TYPE_POSIX = ENUMS['storage_type_posixfs']
STORAGE_TYPE_GLANCE = ENUMS['storage_type_glance']
STORAGE_TYPE_GLUSTER = ENUMS['storage_type_gluster']

if STORAGE_TYPE is None:
    LOCAL = PARAMETERS.get('local', None)
else:
    LOCAL = (STORAGE_TYPE == STORAGE_TYPE_LOCAL)


STORAGE_TYPE_PROVIDERS = [STORAGE_TYPE_GLANCE]
# We provision for posix with the subtype, like: "posixfs_subfix"
# For the moment just revert back
if STORAGE_TYPE.startswith(STORAGE_TYPE_POSIX):
    STORAGE_TYPE = STORAGE_TYPE_POSIX

NUM_OF_DEVICES = int(STORAGE_CONF.get("%s_devices" % STORAGE_TYPE.lower(), 0))
STORAGE_NAME = ["_".join([STORAGE_TYPE.lower(), str(i)])
                for i in xrange(NUM_OF_DEVICES)]

if 'prepared_env' in ART_CONFIG:
    GOLDEN_ENV = ART_CONFIG['prepared_env']

    dcs = GOLDEN_ENV[0]['dcs']
    for dc in dcs:
        if int(dc['dc']['local']) == LOCAL:
            DC = dc['dc']
    DC_NAME = [DC['name']]
    COMP_VERSION = DC['compatibility_version']

    CLUSTERS = [x['cluster'] for x in DC['clusters']]
    CLUSTER_NAME = [x['name'] for x in CLUSTERS]
    CPU_NAME = CLUSTERS[0]['cpu_name']

    HOSTS = []
    HOST_NICS = set()
    HOSTS_IP = []
    HOST_OBJS = []
    NETWORK_HOSTS = []

    for cluster in CLUSTERS:
        for host in cluster['hosts']:
            host_obj = hosts.HostObject(
                host['host']['name'], host['host']['passwd'])
            HOST_OBJS.append(host_obj)
            HOSTS.append(host_obj.name)
            HOSTS_PW = host_obj.password
            logger.info("getting nics of host %s", host['host']['name'])
            host_nics = list(host_obj.nics)
            up = host_obj.up_nics
            logger.info("host nics: %s, all: %s, up: %s",
                        host_nics, HOST_NICS, up)
            HOST_NICS.update(set(host_nics))
            HOSTS_IP.append(host_obj.ip)
            logger.info("host ips: %s", HOSTS_IP)
            if len(up) > 3:
                NETWORK_HOSTS.append(host_obj)

    HOST_NICS = list(HOST_NICS)
    HOST_NICS.reverse()
    VMS = []
    for cluster in CLUSTERS:
        for vm in cluster['vms']:
            VMS.append(vm['vm'])
    VM_NAME = [x['name'] for x in VMS]
    VMS_LINUX_USER = VMS[0]['user']
    VMS_LINUX_PW = VMS[0]['password']

    TEMPLATES = []
    for cluster in CLUSTERS:
        for templ in cluster['templates']:
            TEMPLATES.append(templ['template'])
    TEMPLATE_NAME = [x['name'] for x in TEMPLATES]

    export_sds = GOLDEN_ENV[1]['export_domains']
    EXPORT_STORAGE_NAME = export_sds[0]['export_domain']['name']

    iso_sds = GOLDEN_ENV[2]['iso_domains']
    ISO_DOMAIN_NAME = iso_sds[0]['iso_domain']['name']
    ISO_DOMAIN_ADDRESS = PARAMETERS.as_list("tests_iso_domain_address")[0]
    ISO_DOMAIN_PATH = PARAMETERS.as_list("tests_iso_domain_path")[0]

    CPU_CORES = int(VMS[0]['cpu_cores'])
    CPU_SOCKET = int(VMS[0]['cpu_socket'])

    UNUSED_DATA_DOMAIN_ADDRESSES = PARAMETERS.as_list('data_domain_address')
    UNUSED_DATA_DOMAIN_PATHS = PARAMETERS.as_list('data_domain_path')
    logger.info("Free nfs shares: %s %s",
                UNUSED_DATA_DOMAIN_ADDRESSES, UNUSED_DATA_DOMAIN_PATHS)

    UNUSED_LUNS = PARAMETERS.as_list('lun')
    UNUSED_LUN_ADDRESSES = PARAMETERS.as_list('lun_address')
    UNUSED_LUN_TARGETS = PARAMETERS.as_list('lun_target')
    logger.info("Free iscsi shares: %s %s %s", UNUSED_LUNS,
                UNUSED_LUN_ADDRESSES, UNUSED_LUN_TARGETS)
else:
    GOLDEN_ENV = False
    # DATA CENTER SECTION
    DC_NAME = ["".join([TEST_NAME, "_DC", str(i)]) for i in range(5)]
    PARAMETERS['dc_name'] = DC_NAME[0]

    # CLUSTER SECTION
    CLUSTER_NAME = ["".join([TEST_NAME, "_Cluster", str(i)]) for i in range(5)]
    PARAMETERS['cluster_name'] = CLUSTER_NAME[0]

    CPU_NAME = PARAMETERS['cpu_name']
    COMP_VERSION = PARAMETERS['compatibility_version']
    HOSTS = PARAMETERS.as_list('vds')
    HOSTS_IP = list(HOSTS)
    HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
    HOST_NICS = PARAMETERS.as_list('host_nics')

    HOST_OBJS = []
    NETWORK_HOSTS = []

    for host in HOSTS:
        host_obj = hosts.HostObject(host, HOSTS_PW, host, HOST_NICS)
        HOST_OBJS.append(host_obj)
        NETWORK_HOSTS.append(host_obj)

    HOST_OS = PARAMETERS['host_os']

    VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
    VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
    VM_NAME = ["_".join([TEST_NAME, 'vm', str(num)]) for num in xrange(1, 6)]
    TEMPLATE_NAME = [
        "".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]

    EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
    EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]
    EXPORT_STORAGE_NAME = "Export"

    CPU_CORES = PARAMETERS['cpu_cores']
    CPU_SOCKET = PARAMETERS['cpu_socket']

    ISO_DOMAIN_NAME = PARAMETERS.get("shared_iso_domain_name", None)
    ISO_DOMAIN_ADDRESS = PARAMETERS.as_list("tests_iso_domain_address")[0]
    ISO_DOMAIN_PATH = PARAMETERS.as_list("tests_iso_domain_path")[0]

    if STORAGE_TYPE == STORAGE_TYPE_NFS:
        ADDRESS = PARAMETERS.as_list('data_domain_address')
        PATH = PARAMETERS.as_list('data_domain_path')
    elif STORAGE_TYPE == STORAGE_TYPE_ISCSI:
        LUNS = PARAMETERS.as_list('lun')
        LUN = LUNS
        LUN_ADDRESS = PARAMETERS.as_list('lun_address')
        LUN_TARGET = PARAMETERS.as_list('lun_target')
        LUN_PORT = 3260
    elif STORAGE_TYPE == ENUMS['storage_type_posixfs']:
        VFS_TYPE = (PARAMETERS['storage_type']).split("_")[1]
        if VFS_TYPE == "pnfs":
            VFS_TYPE = STORAGE_TYPE_NFS
            PARAMETERS['data_domain_mount_options'] = "vers=4.1"
            ADDRESS = PARAMETERS.as_list('data_domain_address')
            PATH = PARAMETERS.as_list('data_domain_path')

        PARAMETERS['vfs_type'] = VFS_TYPE

HOSTS_USER = 'root'

UNCOMP_DC_NAME = PARAMETERS.get("dc_name", "%s_DC30" % TEST_NAME)
UNCOMP_CL_NAME = ["".join([CLUSTER_NAME[0], "CL3", str(i)]) for i in range(2)]

VERSION = ["3.0", "3.1", "3.2", "3.3", "3.4", "3.5"]

SAMPLER_TIMEOUT = 60
CONNECT_TIMEOUT = 60

MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')

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
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_INTERFACE = ENUMS['interface_virtio']

# Storage Domain states     DISK_INTERFACE = ENUMS['interface_virtio']
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

# USERS & ROLES
AD_USER_DOMAIN = PARAMETERS.get('ad_user_domain', None)
AD_USERNAME = PARAMETERS.get('ad_user', None)
AD_USER_NO_ROLES = PARAMETERS.get('no_roles_user', None)

# MISC PARAMETERS
MAX_WORKERS = PARAMETERS.get('max_workers', 10)

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

# ### New object oriented approach
VDS_HOSTS = [
    resources.VDS(
        h, HOSTS_PW,
    ) for h in HOSTS
]
OVIRT_SERVICE = 'ovirt-engine'
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)
ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        VDC_ADMIN_USER,
        VDC_PASSWORD,
        resources.Domain(VDC_ADMIN_DOMAIN),
    ),
    schema=REST_CONNECTION.get('schema'),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT,
)
