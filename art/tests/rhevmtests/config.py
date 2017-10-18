"""
Consolidated config module
"""

import logging
import os

from art.rhevm_api import resources
from art.rhevm_api.utils import test_utils
from art.test_handler.settings import ART_CONFIG, GE


logger = logging.getLogger(__name__)

__test__ = False


GOLDEN_ENV = True

# RHEVM related constants
ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
PERMITS = ART_CONFIG['elements_conf']['RHEVM Permits']
RHEVM_UTILS_ENUMS = ART_CONFIG['elements_conf']['RHEVM Utilities']
NOT_APPLICABLE = 'N/A'

PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']

PRODUCT_NAME = PARAMETERS['product_name']
PRODUCT_BUILD = ART_CONFIG['DEFAULT'].get('RHEVM_BUILD', None)

# ENGINE SECTION
VDC_HOST = GE['engine_fqdn']

VDC_ROOT_PASSWORD = GE['root_passwd']
VDC_ROOT_USER = "root"
VDC_PASSWORD = GE['password']

VDC_ADMIN_USER = REST_CONNECTION['user']
VDC_ADMIN_DOMAIN = REST_CONNECTION['user_domain']
VDC_ADMIN_JDBC_LOGIN = "{user}@internal".format(user=VDC_ADMIN_USER)
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']
ENGINE_URL = GE['api_url']

ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
ENGINE_EXTENSIONS_DIR = '/etc/ovirt-engine/extensions.d'

# FOREMAN DETAILS
FOREMAN_URL = PARAMETERS.get('foreman_url')
FOREMAN_USER = PARAMETERS.get('foreman_user')
FOREMAN_PASSWD = PARAMETERS.get('foreman_password')

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

# Shorter storage types
NFS = STORAGE_TYPE_NFS
ISCSI = STORAGE_TYPE_ISCSI
FCP = STORAGE_TYPE_FCP
CEPH = STORAGE_TYPE_CEPH
GLUSTER = STORAGE_TYPE_GLUSTER
POSIX = STORAGE_TYPE_POSIX
GLANCE = STORAGE_TYPE_GLANCE
CINDER = STORAGE_TYPE_CINDER
LOCAL = STORAGE_TYPE_LOCAL


STORAGE_SERVER_XTREMIO = 'xtremio'
STORAGE_SERVER_NETAPP = 'netapp'

CPU_NAME = GE['cpu_type']

IBM_POWER_8 = 'IBM POWER8'
IBM_POWER_8E = 'IBM POWER8E'
PPC_CPUS = [IBM_POWER_8, IBM_POWER_8E]
PPC_ARCH = True if CPU_NAME in PPC_CPUS else False
PPC_SKIP_MESSAGE = 'Test not supported under PPC64 architecture'
PPC_TWO_HOSTS = "Test requires three hosts, when PPC GE has only two"

HOSTS = []
HOSTS_IP = []
HOSTS_PW = PARAMETERS.get('vds_password')[0]
VDS_HOSTS = []

# list of Host object. one only for rhel and the second only for rhev-h
HOSTS_RHEL = []
HOSTS_RHEVH = []

CEPH_SERVER_SECRET = PARAMETERS.get('ceph_server_secret', None)
CEPH_MOUNT_OPTIONS = "name=admin,secret={0}".format(CEPH_SERVER_SECRET)

SD_LIST = []
ISCSI_STORAGE_MANAGER = (
    GE['extra_configuration_options'].get('storage_managers', {}).get('iscsi')
)
FCP_STORAGE_MANAGER = (
    GE['extra_configuration_options'].get('storage_managers', {}).get('fcp')
)

# Hosted engine constants
HE_VM = "HostedEngine"
HE_STORAGE_DOMAIN = "hosted_storage"

VMS_LINUX_USER = VDC_ROOT_USER
VMS_LINUX_PW = VDC_ROOT_PASSWORD
###############################################################################
# GE entities
# Datacenters and compatibility_version
DC_NAME = []
DC_COMP_VERSIONS = []

DC_NAME.append(GE['data_center_name'])
DC_COMP_VERSIONS.append(GE['compatibility_version'])

logger.info("DATACENTERS in golden environment: %s", DC_NAME)

COMP_VERSION = DC_COMP_VERSIONS[0]

###############################################################################
# Clusters
CLUSTER_NAME = [cl['name'] for cl in GE['clusters']]
logger.info("CLUSTERS in golden environment: %s", CLUSTER_NAME)
###############################################################################
# storages
NFS_STORAGE = []
DATA_DOMAIN_ADDRESSES = []
DATA_DOMAIN_PATHS = []

ISCSI_STORAGE = []
LUN_TARGETS = []
LUN_ADDRESSES = []
LUNS = []

GLUSTERFS_STORAGE = []
GLUSTER_DATA_DOMAIN_ADDRESSES = []
GLUSTER_DATA_DOMAIN_PATHS = []

FCP_STORAGE = []
FC_LUNS = []

for sd_name, sd_info in GE.get('storages').items():
    if 'domain_function' in sd_info:
        if sd_info.get('domain_function') == 'export':
            EXPORT_DOMAIN_NAME = sd_name
        elif sd_info.get('domain_function') == 'iso':
            ISO_DOMAIN_NAME = sd_name
            if 'nfs' in sd_info:
                ISO_DOMAIN_ADDRESS = sd_info.get('nfs').get('address')
                ISO_DOMAIN_PATH = sd_info.get('nfs').get('path')
            elif 'glusterfs' in sd_info:
                ISO_DOMAIN_ADDRESS = sd_info.get('glusterfs').get('address')
                ISO_DOMAIN_PATH = sd_info.get('glusterfs').get('path')
    elif 'nfs' in sd_info:
        NFS_STORAGE.append(sd_name)
        DATA_DOMAIN_ADDRESSES.append(sd_info.get('nfs').get('address'))
        DATA_DOMAIN_PATHS.append(sd_info.get('nfs').get('path'))
    elif 'iscsi' in sd_info:
        ISCSI_STORAGE.append(sd_name)
        LUN_TARGETS.append(sd_info.get('iscsi').get('target'))
        LUN_ADDRESSES.append(sd_info.get('iscsi').get('address'))
        LUNS.append(sd_info.get('iscsi').get('lun_id'))
    elif 'glusterfs' in sd_info:
        GLUSTERFS_STORAGE.append(sd_name)
        GLUSTER_DATA_DOMAIN_ADDRESSES.append(
            sd_info.get('glusterfs').get('address')
        )
        GLUSTER_DATA_DOMAIN_PATHS.append(sd_info.get('glusterfs').get('path'))
    elif 'fcp' in sd_info:
        FCP_STORAGE.append(sd_name)
        FC_LUNS.append(sd_info.get('fcp').get('lun_id'))

STORAGE_NAME = NFS_STORAGE + ISCSI_STORAGE + GLUSTERFS_STORAGE + FCP_STORAGE

logger.info("STORAGES in golden environment: %s", STORAGE_NAME)
logger.info(
    "NFS storage for building GE: %s",
    zip(DATA_DOMAIN_ADDRESSES, DATA_DOMAIN_PATHS)
)
logger.info(
    "GLUSTERFS storage for building GE: %s",
    zip(GLUSTER_DATA_DOMAIN_ADDRESSES, GLUSTER_DATA_DOMAIN_PATHS)
)
logger.info(
    "ISCSI luns for building GE: %s", zip(LUNS, LUN_ADDRESSES, LUN_TARGETS)
)
logger.info("Fibre channel LUNs for building GE: %s", FC_LUNS)
logger.info("EXPORT domain for building GE: %s", EXPORT_DOMAIN_NAME)
logger.info("ISO domain for building GE: %s", ISO_DOMAIN_NAME)

###############################################################################
# extra storages


def get_storages_data(ge_storages, key):

    if ge_storages is None:
        return []

    return [sd[key] for sd in ge_storages]


# nfs extra storages
UNUSED_DATA_DOMAIN_ADDRESSES = get_storages_data(
    GE.get('extra_nfs_storage_domains'), 'address'
)
UNUSED_DATA_DOMAIN_PATHS = get_storages_data(
    GE.get('extra_nfs_storage_domains'), 'path'
)
logger.info(
    "Free nfs shares: %s %s",
    UNUSED_DATA_DOMAIN_ADDRESSES, UNUSED_DATA_DOMAIN_PATHS
)
# END nfs extra storages

# glusterfs extra storages
UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES = get_storages_data(
    GE.get('extra_glusterfs_storage_domains'), 'address'
)
UNUSED_GLUSTER_DATA_DOMAIN_PATHS = get_storages_data(
    GE.get('extra_glusterfs_storage_domains'), 'path'
)
logger.info(
    "Free Gluster shares: %s %s",
    UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES, UNUSED_GLUSTER_DATA_DOMAIN_PATHS
)
# END glusterfs extra storages
# iscsi extra storages
UNUSED_LUNS = get_storages_data(
    GE.get('extra_iscsi_storage_domains'), 'lun_id'
)
UNUSED_LUN_ADDRESSES = get_storages_data(
    GE.get('extra_iscsi_storage_domains'), 'address'
)
UNUSED_LUN_TARGETS = get_storages_data(
    GE.get('extra_iscsi_storage_domains'), 'target'
)
logger.info(
    "Free iscsi LUNs: %s %s %s",
    UNUSED_LUNS, UNUSED_LUN_ADDRESSES, UNUSED_LUN_TARGETS
)
# END iscsi extra storages
# FCP extra storages
UNUSED_FC_LUNS = get_storages_data(GE.get('extra_fcp_storage_domains'), 'lun')
logger.info("Free fibre channel LUNs: %s", UNUSED_FC_LUNS)
# END FCP extra storages
###############################################################################
# windows data sd
WINDOWS_DATASD = GE.get('immutable_windows_nfs_storage_domains', {})
if WINDOWS_DATASD:
    WINDOWS_DATASD_NAME = WINDOWS_DATASD.get("name")
    WINDOWS_DATASD_ADDR = WINDOWS_DATASD.get("address")
    WINDOWS_DATASD_PATH = WINDOWS_DATASD.get("path")
    WINDOWS_DATASD_HOST = WINDOWS_DATASD.get("host")
    WINDOWS_DATASD_DC = WINDOWS_DATASD.get("data_center")
    logger.info(
        "Windows data SD info: NAME: %s, HOST: %s, DC: %s, ADDR: %s, PATH: %s",
        WINDOWS_DATASD_NAME, WINDOWS_DATASD_HOST, WINDOWS_DATASD_DC,
        WINDOWS_DATASD_ADDR, WINDOWS_DATASD_PATH
    )

###############################################################################
# external providers
EXTERNAL_PROVIDERS = {}
provider_type = None
GLANCE_URL = ''

ge_external_providers = GE.get('external_providers', [])

for ep in ge_external_providers:
    SD_LIST.append(ep['name'])
    if ep['type'] == 'os_image':
        provider_type = 'os_image'
        GLANCE_DOMAIN = ep['name']
        GLANCE_URL = ep['url']
    if not EXTERNAL_PROVIDERS.get(provider_type):
        EXTERNAL_PROVIDERS[provider_type] = list()
    EXTERNAL_PROVIDERS[provider_type].append(ep['name'])

###############################################################################

GE_VMS = {
    'nfs': [],
    'iscsi': [],
    'gluster': [],
    'fc': [],
}
for vm in GE.get('vms'):
    profile = vm.get('profile')
    for storage_type in ['nfs', 'iscsi', 'gluster', 'fc']:
        if storage_type in profile:
            GE_VMS[storage_type].append(vm.get('name'))
            break

NFS_VMS = GE_VMS.get('nfs')
ISCSI_VMS = GE_VMS.get('iscsi')
GLUSTER_VMS = GE_VMS.get('gluster')
FCP_VMS = GE_VMS.get('fc')
VM_NAME = NFS_VMS + ISCSI_VMS + GLUSTER_VMS + FCP_VMS

logger.info("VMS in golden environment: %s", VM_NAME)

###############################################################################
# templates
TEMPLATE_NAME = [temp.get('name') for temp in GE['external_templates']]
logger.info("Templates in golden environment: %s", TEMPLATE_NAME)

GOLDEN_GLANCE_IMAGE = GE['external_templates'][0]['image_disk']
DEFAULT_ISO_DOMAIN = 'ISO_DOMAIN'
ISO_DOMAIN_NAME_LIST = [ISO_DOMAIN_NAME] if ISO_DOMAIN_NAME else []

SD_LIST += (
    STORAGE_NAME +
    [EXPORT_DOMAIN_NAME] +
    ISO_DOMAIN_NAME_LIST +
    [DEFAULT_ISO_DOMAIN] +
    ['ovirt-image-repository']
)
###############################################################################
# gluster replica
GLUSTER_REPLICA_PATH = GE.get('gluster-replica', {}).get('path')
GLUSTER_REPLICA_SERVERS = GE.get('gluster-replica', {}).get('servers')
###############################################################################
HOSTS_USER = 'root'

COMP_VERSION_4_0 = ["3.6", "4.0", "4.1", "4.2"]

SAMPLER_SLEEP = 10
SAMPLER_TIMEOUT = 210
CONNECT_TIMEOUT = 60
ENGINE_RESTART_TIMEOUT = 120  # seconds
FENCE_TIMEOUT = 200
VM_IP_TIMEOUT = 300

MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')

DISPLAY_TYPE = ENUMS['display_type_spice']
if PPC_ARCH:
    DISPLAY_TYPE = ENUMS['display_type_vnc']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
NIC_TYPE_RTL8139 = ENUMS['nic_type_rtl8139']
NIC_TYPE_E1000 = ENUMS['nic_type_e1000']

# Disk interfaces
INTERFACE_VIRTIO = ENUMS['interface_virtio']
DISK_INTERFACE = INTERFACE_VIRTIO
INTERFACE_IDE = ENUMS['interface_ide']
INTERFACE_VIRTIO_SCSI = ENUMS['interface_virtio_scsi']
INTERFACE_SPAPR_VSCSI = ENUMS['interface_spapr_vscsi']

# Disk formats
DISK_FORMAT_COW = ENUMS['format_cow']
DISK_FORMAT_RAW = ENUMS['format_raw']

# Disk qcow version
DISK_QCOW_V2 = ENUMS['qcow2_version2']
DISK_QCOW_V3 = ENUMS['qcow2_version3']

# Disk types
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_TYPE_DATA = ENUMS['disk_type_data']
DISK_TYPE_LUN = ENUMS['disk_type_lun']
DISK_LOCKED = ENUMS['disk_state_locked']
DISK_OK = ENUMS['disk_state_ok']

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
VM_NOT_RESPONDING = ENUMS['vm_state_not_responding']
VM_UNKNOWN = ENUMS['vm_state_unknown']

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
HOST_CONNECTING = ENUMS["host_state_connecting"]
HOST_REBOOTING = ENUMS["host_state_reboot"]

# Snapshot states
SNAPSHOT_OK = ENUMS['snapshot_state_ok']
SNAPSHOT_IN_PREVIEW = ENUMS['snapshot_state_in_preview']
STATELESS_SNAPSHOT = ENUMS['snapshot_stateless_description']
SNAPSHOT_LOCKED = ENUMS['snapshot_state_locked']

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
    schema=REST_CONNECTION.get('scheme'),
    port=REST_CONNECTION.get('port'),
    entry_point=ENGINE_ENTRY_POINT,
)

# Slave host
SLAVE_HOST = resources.Host("127.0.0.1")
SLAVE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)

CPU_SHARE_DISABLED = 0
CPU_SHARE_LOW = 512
CPU_SHARE_MEDIUM = 1024
CPU_SHARE_HIGH = 2048

# Common related jobs
JOB_STARTED = ENUMS['job_started']
JOB_FAILED = ENUMS['job_failed']
JOB_FINISHED = ENUMS['job_finished']
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
JOB_REDUCE_DOMAIN = ENUMS['job_reduce_storage_domain']
# Template section
JOB_ADD_TEMPLATE = ENUMS['job_add_template']
JOB_ADD_VM_FROM_TEMPLATE = ENUMS['job_add_vm_from_template']
JOB_IMPORT_TEMPLATE = ENUMS['job_import_vm_template']
JOB_REMOVE_TEMPLATE = ENUMS['job_remove_vm_template']
JOB_REMOVE_TEMPLATE_FROM_EXPORT = ENUMS[
    'job_remove_vm_template_from_export_domain'
]
# VM section
JOB_ADD_VM = ENUMS['job_add_vm']
JOB_EXPORT_VM = ENUMS['job_export_vm']
JOB_IMPORT_VM = ENUMS['job_import_vm']
JOB_MIGRATE_VM = ENUMS['job_migrate_vm']
JOB_REMOVE_VM = ENUMS['job_remove_vm']
JOB_REMOVE_VM_FROM_EXPORT = ENUMS['job_remove_vm_from_export_domain']
JOB_STOP_VM = ENUMS['job_stop_vm']
JOB_UPDATE_VM = ENUMS['job_update_vm']

# agent URL for guest tools testing
AGENT_URL = 'http://10.34.63.72/cirunner/ci.php?action={action}&hostID={vm_id}'

SKIP_MSG_PREFIX = "Hosts in env doesn't have %s"
NOT_4_NICS_HOSTS = GE['extra_configuration_options'].get('not_4_nics_hosts')
NOT_4_NICS_HOST_SKIP_MSG = SKIP_MSG_PREFIX % "4 nics"
NOT_6_NICS_HOSTS = GE['extra_configuration_options'].get('not_6_nics_hosts')
NOT_6_NICS_HOST_SKIP_MSG = SKIP_MSG_PREFIX % "6 nics"
NO_FULL_SRIOV_SUPPORT = GE['extra_configuration_options'].get(
    'no_full_sriov_support'
)
NO_FULL_SRIOV_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % "full SRIOV support"
NO_SEMI_SRIOV_SUPPORT = GE['extra_configuration_options'].get(
    'no_semi_sriov_support'
)
NO_SEMI_SRIOV_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % "semi SRIOV support"
NO_JUMBO_FRAME_SUPPORT = GE['extra_configuration_options'].get(
    'no_jumbo_frame_support'
)
NO_JUMBO_FRAME_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % "jumbo frame support"
NO_EXTRA_BOND_MODE_SUPPORT = GE['extra_configuration_options'].get(
    'no_extra_bond_mode_support'
)
NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG = SKIP_MSG_PREFIX % (
    "extra bond mode support"
)
NO_HYPERCONVERGED_SUPPORT = GE['extra_configuration_options'].get(
    'not_hyperconverged', True
)
NO_HYPERCONVERGED_SUPPORT_SKIP_MSG = (
    SKIP_MSG_PREFIX % "Test does not support hyperconverged env"
)

# used for tests that are not adjusted to GE or tests that we don't want to run
DO_NOT_RUN = 17

# user info
USER_DOMAIN = "%s-authz" % VDC_ADMIN_DOMAIN
USER = 'user1'
USER_NAME = '%s@%s' % (USER, USER_DOMAIN)
ADMIN_USER_NAME = GE['username']

WORKSPACE_ENV = os.getenv('WORKSPACE', '')
WORKSPACE_PATH = 'jenkins/qe/conf/infra/storageManagerWrapper.conf'
STORAGE_CONFIG = os.path.join(WORKSPACE_ENV, WORKSPACE_PATH)
STORAGE_SERVER = {
    'xtremio-xms': 'xtremio',
    'vserver-san01-iscsi01.qa.lab.tlv.redhat.com': 'netapp'
}

DATA_CENTER_NAME = DC_NAME[0]
WAIT_FOR_SPM_TIMEOUT = 120
WAIT_FOR_SPM_INTERVAL = 10

BLANK_TEMPLATE = 'Blank'

NIC_NAME = [
    "nic1", "nic2", "nic3", "nic4", "nic5", "nic6", "nic7", "nic8", "nic9"
]
