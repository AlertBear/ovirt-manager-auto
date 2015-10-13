"""
Consolidated config module
"""

__test__ = False

import logging
import copy

from art.test_handler.settings import ART_CONFIG, opts
from art.rhevm_api.utils import test_utils
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
from art.rhevm_api import resources

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

TEST_NAME = "Global"

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

CPU_NAME = PARAMETERS['cpu_name']

HOSTS = []
HOSTS_IP = []
HOST_OBJS = []


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

    # list of Host object one only for rhel and the second only for rhev-h
    HOSTS_RHEL = []
    HOSTS_RHEVH = []

    for cluster in CLUSTERS:
        for host in cluster['hosts']:
            HOST_OBJS.append(ll_hosts.get_host_object(host['name']))
            HOSTS_PW = host['passwd']

    # sort the HOST_OBJS by rhevh_first if reverse else rhel_first
    reverse = (
        'host_order' in PARAMETERS and
        PARAMETERS['host_order'] == 'rhevh_first'
    )
    HOST_OBJS.sort(key=lambda host: host.get_type(), reverse=reverse)

    # change the name of all hosts to be able to rename it to new order later
    for host_obj in HOST_OBJS:
        host_name = host_obj.name
        new_name = "temp_%s" % host_name
        if ll_hosts.updateHost(True, host_name, name=new_name):
            host_obj.name = new_name
        HOSTS_IP.append(host_obj.address)

    # run on GE yaml structure to rename the hosts and move it to
    # different cluster if necessary
    i = 0
    for dc in dcs:
        for cluster in dc['clusters']:
            for host in cluster['hosts']:
                host_obj = HOST_OBJS[i]
                new_name = host['name']
                if ll_hosts.updateHost(True, host_obj.name, name=new_name):
                    host_obj.name = new_name

                if cluster['name'] != ll_hosts.getHostCluster(new_name):
                    hl_hosts.move_host_to_another_cluster(
                        new_name, cluster['name']
                    )
                HOSTS.append(new_name)
                i += 1
    HOSTS_RHEL = [host for host in HOST_OBJS if host.get_type() == 'rhel']
    HOSTS_RHEVH = [host for host in HOST_OBJS if host.get_type() == 'rhev-h']
    hosts_type = [host.get_type() for host in HOST_OBJS]
    logger.info("The host order is: %s", zip(HOSTS, HOSTS_IP, hosts_type))

    VMS = []
    for cluster in CLUSTERS:
        for vm in cluster['vms']:
            if 'number_of_vms' in vm:
                num_of_vms = repr(vm['number_of_vms'])
                suffix_n = 0
                vm_name = vm['name']
                while suffix_n < int(num_of_vms):
                    another_vm = copy.deepcopy(vm)
                    another_vm['name'] = vm_name + str(suffix_n)
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
    EXPORT_STORAGE_NAME = export_sds[0]['name']

    iso_sds = GOLDEN_ENV['iso_domains']
    ISO_DOMAIN_NAME = iso_sds[0]['name']
    ISO_DOMAIN_ADDRESS = get_list(PARAMETERS, "tests_iso_domain_address")[0]
    ISO_DOMAIN_ADDRESS = get_list(PARAMETERS, "tests_iso_domain_address")[0]
    ISO_DOMAIN_PATH = get_list(PARAMETERS, "tests_iso_domain_path")[0]

    CPU_CORES = 1
    CPU_SOCKET = 1

    # External Provider types
    GLANCE = 'OpenStackImageProvider'

    EXTERNAL_PROVIDERS = {}

    EPS = ART_CONFIG['EPS']

    eps_to_add = EPS.as_list('ep_to_add')
    for ep_to_add in eps_to_add:
        if EPS[ep_to_add]['type'] == GLANCE:
            provider_type = GLANCE
            EXTERNAL_PROVIDERS[provider_type] = EPS[ep_to_add]['name']

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

    LUNS = get_list(PARAMETERS, 'lun')
    LUN_ADDRESSES = get_list(PARAMETERS, 'lun_address')
    LUN_TARGETS = get_list(PARAMETERS, 'lun_target')
    logger.info(
        "iscsi luns for building GE: %s %s %s",
        LUNS, LUN_ADDRESSES, LUN_TARGETS
    )

    UNUSED_DATA_DOMAIN_ADDRESSES = get_list(
        PARAMETERS, 'extra_data_domain_address'
    )
    UNUSED_DATA_DOMAIN_PATHS = get_list(PARAMETERS, 'extra_data_domain_path')
    logger.info(
        "Free nfs shares: %s %s",
        UNUSED_DATA_DOMAIN_ADDRESSES, UNUSED_DATA_DOMAIN_PATHS
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

    UNUSED_LUNS = get_list(PARAMETERS, 'extra_lun')
    UNUSED_LUN_ADDRESSES = get_list(PARAMETERS, 'extra_lun_address')
    UNUSED_LUN_TARGETS = get_list(PARAMETERS, 'extra_lun_target')
    logger.info(
        "Free iscsi shares: %s %s %s",
        UNUSED_LUNS, UNUSED_LUN_ADDRESSES, UNUSED_LUN_TARGETS
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
    HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
    HOST_NICS = PARAMETERS.as_list('host_nics')

    HOST_OS = PARAMETERS.get('host_os')

    VMS_LINUX_USER = PARAMETERS.as_list('vm_linux_user')[0]
    VMS_LINUX_PW = PARAMETERS.as_list('vm_linux_password')[0]
    VM_NAME = ["_".join([TEST_NAME, 'vm', str(num)]) for num in xrange(1, 6)]
    TEMPLATE_NAME = [
        "".join([TEST_NAME, "_Template", str(i)]) for i in range(2)]

    EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
    EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]
    EXPORT_STORAGE_NAME = "Export"

    CPU_CORES = PARAMETERS.get('cpu_cores')
    CPU_SOCKET = PARAMETERS.get('cpu_socket')

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
    elif STORAGE_TYPE == STORAGE_TYPE_GLUSTER:
        GLUSTER_ADDRESS = PARAMETERS.as_list('gluster_data_domain_address')
        GLUSTER_PATH = PARAMETERS.as_list('gluster_data_domain_path')
        VFS_TYPE = ENUMS['vfs_type_glusterfs']
    elif STORAGE_TYPE == ENUMS['storage_type_posixfs']:
        VFS_TYPE = (PARAMETERS['storage_type']).split("_")[1]
        if VFS_TYPE == "pnfs":
            VFS_TYPE = STORAGE_TYPE_NFS
            PARAMETERS['data_domain_mount_options'] = "vers=4.1"
            ADDRESS = PARAMETERS.as_list('data_domain_address')
            PATH = PARAMETERS.as_list('data_domain_path')

        PARAMETERS['vfs_type'] = VFS_TYPE

LUN_PORT = 3260

HOSTS_USER = 'root'

UNCOMP_DC_NAME = PARAMETERS.get("dc_name", "%s_DC30" % TEST_NAME)
UNCOMP_CL_NAME = ["".join([CLUSTER_NAME[0], "CL3", str(i)]) for i in range(2)]

VERSION = ["3.0", "3.1", "3.2", "3.3", "3.4", "3.5"]

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
DISK_TYPE_DATA = ENUMS['disk_type_data']
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
VM_SAVING = ENUMS['vm_state_saving_state']
VM_WAIT_FOR_LAUNCH = ENUMS['vm_state_wait_for_launch']
VM_POWERING_UP = ENUMS['vm_state_powering_up']

# VM types
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']

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
    ) for h in HOSTS_IP
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

IBM_POWER_8 = 'IBM POWER 8'
PPC_ARCH = True if CPU_NAME == IBM_POWER_8 else False
PPC_SKIP_MESSAGE = 'Test not supported under PPC64 architecture'
