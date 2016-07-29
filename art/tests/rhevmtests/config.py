"""
Consolidated config module
"""
__test__ = False

import logging
import copy

from art.test_handler.settings import ART_CONFIG, opts
from art.rhevm_api.utils import test_utils
from art.rhevm_api import resources
from urlparse import urlparse

logger = logging.getLogger(__name__)


def get_list(params, key):
    """
    Get element from configuration section as list

    :param params: configuration section
    :type params: ConfigObj section
    :param key: element to get
    :type key: str
    :return: return element of configuration section as list
    :rtype: list
    """
    return params.as_list(key) if key in params else []

# RHEVM related constants
ENUMS = opts['elements_conf']['RHEVM Enums']
PERMITS = opts['elements_conf']['RHEVM Permits']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']
NOT_APPLICABLE = 'N/A'

TEST_NAME = "Global"
PREFIX = "net"
NUM_OF_OBJECT = 5

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_CONF = ART_CONFIG['STORAGE']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']

PRODUCT_NAME = PARAMETERS['product_name']
PRODUCT_BUILD = ART_CONFIG['DEFAULT'].get('RHEVM_BUILD', None)

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
ENGINE_EXTENSIONS_DIR = '/etc/ovirt-engine/extensions.d'
VDSM_LOG = '/var/log/vdsm/vdsm.log'
VDSMD_SERVICE = "vdsmd"
LIBVIRTD_SERVICE = "libvirtd"

# FOREMAN DETAILS
FOREMAN_URL = PARAMETERS.get('foreman_url')
FOREMAN_USER = PARAMETERS.get('foreman_user')
FOREMAN_PASSWD = PARAMETERS.get('foreman_password')


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
STORAGE_TYPE_CEPH = ENUMS['storage_type_ceph']
STORAGE_TYPE_LOCAL = ENUMS['storage_type_local']
STORAGE_TYPE_POSIX = ENUMS['storage_type_posixfs']
STORAGE_TYPE_GLANCE = ENUMS['storage_type_glance']
STORAGE_TYPE_CINDER = ENUMS['storage_type_cinder']
STORAGE_TYPE_GLUSTER = ENUMS['storage_type_gluster']

if STORAGE_TYPE is None:
    LOCAL = PARAMETERS.get('local', None)
else:
    LOCAL = (STORAGE_TYPE == STORAGE_TYPE_LOCAL)


STORAGE_TYPE_PROVIDERS = [STORAGE_TYPE_GLANCE, STORAGE_TYPE_CINDER]
# We provision for posix with the subtype, like: "posixfs_subfix"
# For the moment just revert back
if STORAGE_TYPE.startswith(STORAGE_TYPE_POSIX):
    STORAGE_TYPE = STORAGE_TYPE_POSIX

NUM_OF_DEVICES = int(STORAGE_CONF.get("%s_devices" % STORAGE_TYPE.lower(), 0))
STORAGE_NAME = ["_".join([STORAGE_TYPE.lower(), str(i)])
                for i in xrange(NUM_OF_DEVICES)]

CPU_NAME = PARAMETERS['cpu_name']

IBM_POWER_8 = 'IBM POWER8'
IBM_POWER_8E = 'IBM POWER8E'
PPC_CPUS = [IBM_POWER_8, IBM_POWER_8E]
PPC_ARCH = True if CPU_NAME in PPC_CPUS else False
PPC_SKIP_MESSAGE = 'Test not supported under PPC64 architecture'
PPC_TWO_HOSTS = "Test requires three hosts, when PPC GE has only two"

HOSTS = []
HOSTS_IP = []
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
VDS_HOSTS = []

# list of Host object. one only for rhel and the second only for rhev-h
HOSTS_RHEL = []
HOSTS_RHEVH = []

CEPHFS_ADDRESS = get_list(PARAMETERS, 'cephfs_domain_address')
CEPHFS_PATH = get_list(PARAMETERS, 'cephfs_domain_path')
CEPH_SERVER_SECRET = PARAMETERS.get('ceph_server_secret', None)
CEPH_MOUNT_OPTIONS = "name=admin,secret={0}".format(CEPH_SERVER_SECRET)


ADDRESS = get_list(PARAMETERS, 'data_domain_address')
PATH = get_list(PARAMETERS, 'data_domain_path')
LUNS = get_list(PARAMETERS, 'lun')
LUN = LUNS
LUN_ADDRESS = get_list(PARAMETERS, 'lun_address')
LUN_TARGET = get_list(PARAMETERS, 'lun_target')
GLUSTER_ADDRESS = get_list(PARAMETERS, 'gluster_data_domain_address')
GLUSTER_PATH = get_list(PARAMETERS, 'gluster_data_domain_path')
VFS_TYPE = ENUMS['vfs_type_glusterfs']
SD_LIST = []

# Hosted engine constants
HE_VM = "HostedEngine"
HE_STORAGE_DOMAIN = "hosted_storage"

if 'prepared_env' in ART_CONFIG:
    GOLDEN_ENV = ART_CONFIG['prepared_env']

    dcs = GOLDEN_ENV['dcs']
    DC = None

    for dc in dcs:
        if int(dc['local']) == LOCAL:
            DC = dc
    DC_NAME = [DC['name']]
    COMP_VERSION = DC['compatibility_version']

    CLUSTERS = DC['clusters']
    CLUSTER_NAME = [x['name'] for x in CLUSTERS]

    VMS = []
    NFS_VMS = []
    ISCSI_VMS = []
    GLUSTER_VMS = []
    FCP_VMS = []
    for cluster in CLUSTERS:
        for vm in cluster['vms']:
            if 'number_of_vms' in vm:
                num_of_vms = repr(vm['number_of_vms'])
                suffix_n = 0
                vm_name = vm['name']
                while suffix_n < int(num_of_vms):
                    another_vm = copy.deepcopy(vm)
                    another_vm['name'] = vm_name + str(suffix_n)
                    if STORAGE_TYPE_NFS in vm['storage_domain']:
                        NFS_VMS.append(another_vm['name'])
                    if STORAGE_TYPE_ISCSI in vm['storage_domain']:
                        ISCSI_VMS.append(another_vm['name'])
                    # 'glusterfs'[:-2] -> 'gluster' which is a substring of
                    # GE's gluster storage domain name 'test_gluster_X'
                    if STORAGE_TYPE_GLUSTER[:-2] in vm['storage_domain']:
                        GLUSTER_VMS.append(another_vm['name'])
                    if STORAGE_TYPE_FCP in vm['storage_domain']:
                        FCP_VMS.append(another_vm['name'])
                    suffix_n += 1
                    VMS.append(another_vm)
            else:
                VMS.append(vm)
    VM_NAME = [x['name'] for x in VMS]

    logger.info(
        "VMS in golden environment: %s", VM_NAME
    )
    VMS_LINUX_USER = VDC_ROOT_USER
    VMS_LINUX_PW = VDC_ROOT_PASSWORD

    EXTERNAL_TEMPLATES = []
    TEMPLATES = []
    for cluster in CLUSTERS:
        for templ in cluster['templates']:
            TEMPLATES.append(templ)
        for external_sources in cluster['external_templates']:
            for source_type in ('glance', 'export_domain'):
                if external_sources[source_type]:
                    for external_template in external_sources[source_type]:
                        EXTERNAL_TEMPLATES.append(external_template)

    TEMPLATE_NAME = [x['name'] for x in TEMPLATES]
    TEMPLATE_NAME = TEMPLATE_NAME + [x['name'] for x in EXTERNAL_TEMPLATES]

    logger.info(
        "Templates in golden environment: %s", TEMPLATE_NAME
    )
    storage_domains = DC['storage_domains']
    STORAGE_NAME = [x['name'] for x in storage_domains]

    export_sds = DC['export_domains']
    EXPORT_DOMAIN_NAME = export_sds[0]['name']

    iso_sds = GOLDEN_ENV['iso_domains']
    ISO_DOMAIN_NAME = iso_sds[0]['name']
    ISO_DOMAIN_ADDRESS = get_list(PARAMETERS, "tests_iso_domain_address")[0]
    ISO_DOMAIN_ADDRESS = get_list(PARAMETERS, "tests_iso_domain_address")[0]
    ISO_DOMAIN_PATH = get_list(PARAMETERS, "tests_iso_domain_path")[0]

    CPU_CORES = 1
    CPU_SOCKET = 1
    CPU_THREADS = 1

    # External Provider types
    GLANCE = 'OpenStackImageProvider'
    CINDER = 'OpenStackVolumeProvider'

    EXTERNAL_PROVIDERS = {}

    EPS = ART_CONFIG.get('EPS')

    eps_to_add = EPS.as_list('ep_to_add') if EPS else []
    for ep_to_add in eps_to_add:
        if EPS[ep_to_add]['type'] == GLANCE:
            provider_type = GLANCE
        elif EPS[ep_to_add]['type'] == CINDER:
            provider_type = CINDER
        if not EXTERNAL_PROVIDERS.get(provider_type):
            EXTERNAL_PROVIDERS[provider_type] = list()
        EXTERNAL_PROVIDERS[provider_type].append(EPS[ep_to_add]['name'])
    GLANCE_EPS = EXTERNAL_PROVIDERS.get(GLANCE)
    if GLANCE_EPS:
        # we assume that our glance is the first one in the list
        GLANCE_DOMAIN = GLANCE_EPS[0]
        GLANCE_URL = EPS[GLANCE_DOMAIN].get('url')
        if GLANCE_URL:
            GLANCE_HOSTNAME = urlparse(GLANCE_URL).hostname
        for glance_ep in GLANCE_EPS:
            SD_LIST.append(glance_ep)
    GOLDEN_GLANCE_IMAGE = 'golden_env_mixed_virtio_0_Disk1'

    DATA_DOMAIN_ADDRESSES = get_list(PARAMETERS, 'data_domain_address')
    DATA_DOMAIN_PATHS = get_list(PARAMETERS, 'data_domain_path')
    logger.info(
        "nfs storage for building GE: %s %s",
        DATA_DOMAIN_ADDRESSES, DATA_DOMAIN_PATHS
    )

    GLUSTER_DATA_DOMAIN_ADDRESSES = get_list(
        PARAMETERS, 'gluster_data_domain_address'
    )
    GLUSTER_DATA_DOMAIN_PATHS = get_list(
        PARAMETERS, 'gluster_data_domain_path'
    )
    logger.info(
        "Gluster storage for building GE: %s %s",
        GLUSTER_DATA_DOMAIN_ADDRESSES, GLUSTER_DATA_DOMAIN_PATHS
    )

    LUN_ADDRESSES = get_list(PARAMETERS, 'lun_address')
    LUN_TARGETS = get_list(PARAMETERS, 'lun_target')
    logger.info(
        "iscsi luns for building GE: %s %s %s",
        LUNS, LUN_ADDRESSES, LUN_TARGETS
    )

else:
    GOLDEN_ENV = False
    # DATA CENTER SECTION
    DC_NAME = ["".join([TEST_NAME, "_DC", str(i)]) for i in range(5)]
    PARAMETERS['dc_name'] = DC_NAME[0]

    # CLUSTER SECTION
    CLUSTER_NAME = ["".join([TEST_NAME, "_Cluster", str(i)]) for i in range(5)]
    PARAMETERS['cluster_name'] = CLUSTER_NAME[0]

    COMP_VERSION = PARAMETERS['compatibility_version']
    HOSTS = PARAMETERS.as_list('vds')
    HOSTS_IP = list(HOSTS)
    VDS_HOSTS = [resources.VDS(host_ip, HOSTS_PW) for host_ip in HOSTS_IP]

    HOST_NICS = PARAMETERS.as_list('host_nics')

    HOST_OS = PARAMETERS.get('host_os')

    VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
    VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
    VM_NAME = ["_".join([TEST_NAME, 'vm', str(num)]) for num in xrange(1, 6)]
    TEMPLATE_NAME = [
        "".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]

    EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
    EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]
    EXPORT_DOMAIN_NAME = "Export"

    CPU_CORES = PARAMETERS.get('cpu_cores')
    CPU_SOCKET = PARAMETERS.get('cpu_socket')

    ISO_DOMAIN_NAME = PARAMETERS.get("shared_iso_domain_name", None)
    ISO_DOMAIN_ADDRESS = PARAMETERS.as_list("tests_iso_domain_address")[0]
    ISO_DOMAIN_PATH = PARAMETERS.as_list("tests_iso_domain_path")[0]

    if STORAGE_TYPE == ENUMS['storage_type_posixfs']:
        VFS_TYPE = (PARAMETERS['storage_type']).split("_")[1]
        if VFS_TYPE == "pnfs":
            VFS_TYPE = STORAGE_TYPE_NFS
            PARAMETERS['data_domain_mount_options'] = "vers=4.1"

        PARAMETERS['vfs_type'] = VFS_TYPE

DEFAULT_ISO_DOMAIN = 'ISO_DOMAIN'
ISO_DOMAIN_NAME_LIST = [ISO_DOMAIN_NAME] if ISO_DOMAIN_NAME else []

SD_LIST += (
    STORAGE_NAME +
    [EXPORT_DOMAIN_NAME] +
    ISO_DOMAIN_NAME_LIST +
    [DEFAULT_ISO_DOMAIN]
)

UNUSED_DATA_DOMAIN_ADDRESSES = get_list(
    PARAMETERS, 'extra_data_domain_address'
)
UNUSED_DATA_DOMAIN_PATHS = get_list(PARAMETERS, 'extra_data_domain_path')
logger.info(
    "Free nfs shares: %s %s",
    UNUSED_DATA_DOMAIN_ADDRESSES, UNUSED_DATA_DOMAIN_PATHS
)

UNUSED_CEPHFS_DATA_DOMAIN_PATHS = get_list(
    PARAMETERS,  'extra_cephfs_data_domain_path'
)
UNUSED_CEPHFS_DATA_DOMAIN_ADDRESSES = get_list(
    PARAMETERS,  'extra_ceph_data_domain_address'
)


UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES = get_list(
    PARAMETERS, 'gluster_extra_data_domain_address'
)
UNUSED_GLUSTER_DATA_DOMAIN_PATHS = get_list(
    PARAMETERS,  'gluster_extra_data_domain_path'
)
logger.info(
    "Free Gluster shares: %s %s",
    UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES, UNUSED_GLUSTER_DATA_DOMAIN_PATHS
)

if PPC_ARCH:
    # Currently we don't have gluster domains in our PPC envs
    # TODO: Add this to the PPC jenkins patch
    UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES = [None, None, None]
    UNUSED_GLUSTER_DATA_DOMAIN_PATHS = [None, None, None]
UNUSED_LUNS = get_list(PARAMETERS, 'extra_lun')
UNUSED_LUN_ADDRESSES = get_list(PARAMETERS, 'extra_lun_address')
UNUSED_LUN_TARGETS = get_list(PARAMETERS, 'extra_lun_target')
logger.info(
    "Free iscsi LUNs: %s %s %s",
    UNUSED_LUNS, UNUSED_LUN_ADDRESSES, UNUSED_LUN_TARGETS
)
UNUSED_FC_LUNS = get_list(PARAMETERS, 'extra_fc_lun')
logger.info("Free fibre channel LUNs: %s", UNUSED_FC_LUNS)

LUN_PORT = 3260

HOSTS_USER = 'root'

UNCOMP_DC_NAME = PARAMETERS.get("dc_name", "%s_DC30" % TEST_NAME)
UNCOMP_CL_NAME = ["".join([CLUSTER_NAME[0], "CL3", str(i)]) for i in range(2)]

VERSION = ["3.0", "3.1", "3.2", "3.3", "3.4", "3.5"]
COMP_VERSION_4_0 = ["3.6", "4.0"]

SAMPLER_SLEEP = 10
SAMPLER_TIMEOUT = 210
CONNECT_TIMEOUT = 60
ENGINE_RESTART_TIMEOUT = 120  # seconds
FENCE_TIMEOUT = 200
VM_IP_TIMEOUT = 300

MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')

NIC_NAME = [
    "nic1", "nic2", "nic3", "nic4", "nic5", "nic6", "nic7", "nic8", "nic9"
]

DISPLAY_TYPE = ENUMS['display_type_spice']
if PPC_ARCH:
    DISPLAY_TYPE = ENUMS['display_type_vnc']
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
INTERFACE_SPAPR_VSCSI = ENUMS['interface_spapr_vscsi']
DISK_INTERFACE = INTERFACE_VIRTIO

# Disk formats
DISK_FORMAT_COW = ENUMS['format_cow']
DISK_FORMAT_RAW = ENUMS['format_raw']

# Disk types
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_TYPE_DATA = ENUMS['disk_type_data']
DISK_TYPE_LUN = ENUMS['disk_type_lun']
DISK_LOCKED = ENUMS['disk_state_locked']


# Disk sizes
MB = 1024 ** 2
GB = 1024 ** 3
DISK_SIZE = 5 * GB

# Storage Domain states     DISK_INTERFACE = ENUMS['interface_virtio']
SD_ACTIVE = ENUMS['storage_domain_state_active']
SD_MAINTENANCE = ENUMS['storage_domain_state_maintenance']
SD_INACTIVE = ENUMS['storage_domain_state_inactive']
SD_UNATTACHED = ENUMS['storage_domain_state_unattached']

# DC states
DATA_CENTER_PROBLEMATIC = ENUMS['data_center_state_problematic']
DATA_CENTER_UP = ENUMS['data_center_state_up']

# VM states
VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['placement_host_any_host_in_cluster']
VM_MIGRATABLE = ENUMS['vm_affinity_migratable']
VM_USER_MIGRATABLE = ENUMS['vm_affinity_user_migratable']
VM_UP = ENUMS['vm_state_up']
VM_DOWN = ENUMS['vm_state_down']
VM_POWER_UP = ENUMS['vm_state_powering_up']
VM_POWER_DOWN = ENUMS['vm_state_powering_down']
VM_SUSPENDED = ENUMS['vm_state_suspended']
VM_PAUSED = ENUMS['vm_state_paused']
VM_LOCKED = ENUMS["vm_state_image_locked"]
VM_DOWN_STATE = ENUMS["vm_state_down"]
VM_RESTORING = ENUMS['vm_state_restoring_state']
VM_REBOOT = ENUMS['vm_state_reboot_in_progress']
VM_SAVING = ENUMS['vm_state_saving_state']
VM_WAIT_FOR_LAUNCH = ENUMS['vm_state_wait_for_launch']
VM_POWERING_UP = ENUMS['vm_state_powering_up']
VM_HOST_PASS_THROUGH = 'host_passthrough'

# VM types
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']
if PPC_ARCH:
    # TODO: Known issue, vms should be created as server with rest api
    # https://bugzilla.redhat.com/show_bug.cgi?id=1253261
    VM_TYPE = VM_TYPE_SERVER
else:
    VM_TYPE = VM_TYPE_DESKTOP

# Template states
TEMPLATE_ILLEGAL = ENUMS['template_state_illegal']
TEMPLATE_LOCKED = ENUMS['template_state_locked']
TEMPLATE_OK = ENUMS['template_state_ok']

# Host states
HOST_UP = ENUMS['host_state_up']
HOST_DOWN = ENUMS['host_state_down']
HOST_NONOPERATIONAL = ENUMS["host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["host_state_non_responsive"]
HOST_MAINTENANCE = ENUMS["host_state_maintenance"]

# Snapshot states
SNAPSHOT_OK = ENUMS['snapshot_state_ok']
SNAPSHOT_IN_PREVIEW = ENUMS['snapshot_state_in_preview']
STATELESS_SNAPSHOT = ENUMS['snapshot_stateless_description']

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

if PPC_ARCH:
    OS_TYPE = ENUMS['rhel7ppc64']

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

CPU_SHARE_DISABLED = 0
CPU_SHARE_LOW = 512
CPU_SHARE_MEDIUM = 1024
CPU_SHARE_HIGH = 2048

# Common related jobs
# Disk section
JOB_ADD_DISK = ENUMS['job_add_disk']
JOB_IMPORT_IMAGE = ENUMS['job_import_repo_image']
JOB_LIVE_MIGRATE_DISK = ENUMS['job_live_migrate_disk']
JOB_MOVE_COPY_DISK = ENUMS['job_move_or_copy_disk']
JOB_REGISTER_DISK = ENUMS['job_register_disk']
JOB_REMOVE_DISK = ENUMS['job_remove_disk']
# Snapshot section
JOB_CLONE_VM_FROM_SNAPSHOT = ENUMS['job_add_vm_from_snapshot']
JOB_CREATE_SNAPSHOT = ENUMS['job_create_snapshot']
JOB_PREVIEW_SNAPSHOT = ENUMS['job_preview_snapshot']
JOB_REMOVE_SNAPSHOT = ENUMS['job_remove_snapshot']
JOB_RESTORE_SNAPSHOT = ENUMS['job_restore_vm_snapshot']
JOB_REMOVE_SNAPSHOTS_DISK = ENUMS['job_remove_snapshots_disk']
# Storage Domain section
JOB_ACTIVATE_DOMAIN = ENUMS['job_activate_storage_domain']
JOB_ADD_DOMAIN = ENUMS['job_add_storage_domain']
JOB_ADD_POSIX_DOMAIN = ENUMS['job_add_posixfs_storage_domain']
JOB_ADD_NFS_DOMAIN = ENUMS['job_add_nfs_storage_domain']
JOB_ADD_SAN_DOMAIN = ENUMS['job_add_san_storage_domain']
JOB_ADD_GLUSTERFS_DOMAIN = ENUMS['job_add_glusterfs_storage_domain']
JOB_ADD_STORAGE_DOMAIN = ENUMS['job_add_storage_domain']
JOB_DETACH_DOMAIN = ENUMS['job_detach_storage_domain']
JOB_REMOVE_DOMAIN = ENUMS['job_remove_storage_domain']
# Template section
JOB_ADD_TEMPLATE = ENUMS['job_add_template']
JOB_ADD_VM_FROM_TEMPLATE = ENUMS['job_add_vm_from_template']
JOB_IMPORT_TEMPLATE = ENUMS['job_import_vm_template']
JOB_REMOVE_TEMPLATE = ENUMS['job_remove_vm_template']
# VM section
JOB_ADD_VM = ENUMS['job_add_vm']
JOB_EXPORT_VM = ENUMS['job_export_vm']
JOB_IMPORT_VM = ENUMS['job_import_vm']
JOB_MIGRATE_VM = ENUMS['job_migrate_vm']
JOB_REMOVE_VM = ENUMS['job_remove_vm']
JOB_STOP_VM = ENUMS['job_stop_vm']

# agent URL for guest tools testing
AGENT_URL = 'http://10.34.63.72/cirunner/ci.php?action={action}&hostID={vm_id}'

SKIP_MSG_PREFIX = "Hosts in env doesn't have %s"
NOT_4_NICS_HOSTS = PARAMETERS.as_bool('not_4_nics_hosts')
NOT_4_NICS_HOST_SKIP_MSG = SKIP_MSG_PREFIX % "4 nics"
NOT_6_NICS_HOSTS = PARAMETERS.as_bool('not_6_nics_hosts')
NOT_6_NICS_HOST_SKIP_MSG = SKIP_MSG_PREFIX % "6 nics"
NO_FULL_SRIOV_SUPPORT = PARAMETERS.as_bool('no_full_sriov_support')
NO_FULL_SRIOV_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % "full SRIOV support"
NO_SEMI_SRIOV_SUPPORT = PARAMETERS.as_bool('no_semi_sriov_support')
NO_SEMI_SRIOV_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % "semi SRIOV support"
NO_JUMBO_FRAME_SUPPORT = PARAMETERS.as_bool('no_jumbo_frame_support')
NO_JUMBO_FRAME_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % "jumbo frame support"
NO_EXTRA_BOND_MODE_SUPPORT = PARAMETERS.as_bool('no_extra_bond_mode_support')
NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % (
    "extra bond mode support"
)

# used for tests that are not adjusted to GE or tests that we don't want to run
DO_NOT_RUN = 17

# WGT
WIN2008R2_64B = opts['elements_conf']['Win2008R2_64b']
WIN2012R2_64B = opts['elements_conf']['Win2012R2_64b']
WIN2012_64B = opts['elements_conf']['Win2012_64b']
WIN7_32B = opts['elements_conf']['Win7_32b']
WIN7_64B = opts['elements_conf']['Win7_64b']
WIN8_1_32B = opts['elements_conf']['Win8_1_32b']
WIN8_1_64B = opts['elements_conf']['Win8_1_64b']
WIN8_32B = opts['elements_conf']['Win8_32b']
WIN8_64B = opts['elements_conf']['Win8_64b']
WIN10_64B = opts['elements_conf']['Win10_64b']
