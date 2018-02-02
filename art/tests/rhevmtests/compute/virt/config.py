#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Test configuration module
"""
from rhevmtests.config import *  # flake8: noqa
from art.rhevm_api.data_struct import data_structures as data_struct
import rhevmtests.helpers as helper
import os
from art.rhevm_api.utils import cpumodel


# #######################################################################
# Following parameters should move to consolidated config, once possible
# #######################################################################
# PPC OS arch
RHEL7PPC64 = 'rhel7ppc64'
# ISO storage domain
SHARED_ISO_DOMAIN_ADDRESS = ISO_DOMAIN_ADDRESS
SHARED_ISO_DOMAIN_PATH = ISO_DOMAIN_PATH
SHARED_ISO_DOMAIN_NAME = ISO_DOMAIN_NAME
# Run once parameters
CD_PATTERN = r"ppc.*.iso" if PPC_ARCH else r"windows[-_][0-9].*.iso"
FLOPPY_PATTERN = r".*.vfd"
CDROM_IMAGE_1 = None
CDROM_IMAGE_2 = None
FLOPPY_IMAGE = None
ISO_ERROR = "couldn't find an image to use for this test on iso domain: %s"
RUN_ONCE_VM_PARAMS = {
    "stateless": False,
    "highly_available": False,
}

# Storage names
storage_name = PARAMETERS.get('storage_name', '%s_%d' % (STORAGE_TYPE, 0))
nfs_storage_0 = PARAMETERS.get('storage_name_0', '%s_0' % STORAGE_TYPE)
nfs_storage_1 = PARAMETERS.get('storage_name_1', '%s_1' % STORAGE_TYPE)
export_storage = PARAMETERS.get('export_storage', EXPORT_DOMAIN_NAME)

# disk interfaces
VIRTIO = INTERFACE_VIRTIO

# storage matrix
STORAGE_SELECTOR = ART_CONFIG['RUN']['storages']

# #################################################
# Following paramaters are virt specific paramaters
# #################################################
ADDITIONAL_DC_NAME = 'virt_additional_dc'
ADDITIONAL_CL_NAME = 'virt_additional_cl'
# Vm names
VM_RUN_ONCE = "vm_run_once"
TEST_NAME = "Global"
VM_DESCRIPTION = PARAMETERS.get('vm_description', '%s_test' % TEST_NAME)

USERNAME = VDC_ADMIN_USER
OS_RHEL_7 = ENUMS['rhel7x64']
OS_WIN_7 = ENUMS['windows7x64']

VM_OS_TYPE = ENUMS[RHEL7PPC64] if PPC_ARCH else OS_RHEL_7
VM_DISPLAY_TYPE = ENUMS[
    'display_type_vnc'
] if PPC_ARCH else ENUMS['display_type_spice']
RHEL_OS_TYPE_FOR_MIGRATION = "rhel"

# migration
CANCEL_VM_MIGRATE = False
MIGRATION_VM = VM_NAME[0]
MIGRATION_VM_LOAD = "migration_vm_test"
CONNECTIVITY_CHECK = False if PPC_ARCH else True
MIGRATION_IMAGE_VM = "vm_with_loadTool"
HOST_INDEX_MAX_MEMORY = -1
# for network migration check
NUM_PACKETS = 500


# reg_vms
SPICE = ENUMS['display_type_spice']
VNC = ENUMS['display_type_vnc']

# cpu_hotplug
CPU_HOTPLUG_VM = "cpu_hotplug_vm"
CPU_HOTPLUG_VM_LOAD = "cpu_hotplug_vm_with_load"
CPU_HOTPLUG_VMS_NAME = [CPU_HOTPLUG_VM, CPU_HOTPLUG_VM_LOAD]
VCPU_PINNING_3 = ([{str(i): str(i)} for i in range(3)])
CPU_TOPOLOGY = []
CPU_HOTPLUG_VM_PARAMS = {
    "cpu_cores": 1,
    "cpu_socket": 1,
    "placement_affinity": VM_MIGRATABLE,
    "placement_host": VM_ANY_HOST,
    "vcpu_pinning": [],
}
# hot cpu actions
HOT_PLUG_CPU = "hot plug cpu"
HOT_UNPLUG_CPU = "hot unplug cpu"

# migration
MIGRATING_STATUSES = [
    ENUMS["vm_state_migrating"], ENUMS["vm_state_migrating_to"],
    ENUMS["vm_state_migrating_from"]
]

FILE_NAME = 'test_file'
TEMP_PATH = '/var/tmp/'
FULL_PATH = os.path.join(TEMP_PATH, FILE_NAME)
ACTION_TIMEOUT = 30

# memory hot plug
MB_SIZE_256 = 256 * MB
MB_SIZE_400 = 400 * MB
MEMORY_HOTPLUG_VM = "memory_hotplug_test"

# memory hot unplug
MB_SIZE_512 = 512 * MB
MEMORY_REMOVED = 1792 * MB
MB_SIZE_3840 = 3840 * MB

# VM parameters
VM_MEMORY = "memory"
VM_MEMORY_GUARANTEED = "memory_guaranteed"
VM_PLACEMENT_AFFINITY = "placement_affinity"
VM_PLACEMENT_HOST = "placement_host"
VM_PLACEMENT_HOSTS = "placement_hosts"
VM_HIGHLY_AVAILABLE = "highly_available"
VM_CPU_PINNING = "vcpu_pinning"
VM_CPU_SOCKET = "cpu_socket"
VM_CPU_CORES = "cpu_cores"
VM_CPU_MODE = "cpu_mode"
TYPE_VM = "type"
VM_OS = "os_type"
VM_DISPLAY = "display_type"
VM_CLUSTER = "cluster"
VM_WATCHDOG_MODEL = "watchdog_model"
VM_CPU_SHARES = "cpu_shares"
MAX_MEMORY = 'max_memory'
# RNG DEVICE
RNG_DEVICE = 'rng_device'
URANDOM_RNG = 'urandom'
HW_RNG = 'hwrng'
DEST_HWRNG = "/dev/hwrng"
VERIFY_RNG_DEVICE_ACTIVE = 'dd if=/dev/hwrng of=test bs=1K count=1'

DEFAULT_VM_PARAMETERS = {
    VM_MEMORY: GB,
    VM_MEMORY_GUARANTEED: GB,
    MAX_MEMORY: helper.get_gb(4),
    VM_CPU_SOCKET: 1,
    VM_CPU_CORES: 1,
    VM_OS: VM_OS_TYPE,
    TYPE_VM: VM_TYPE_DESKTOP,
    VM_DISPLAY: VM_DISPLAY_TYPE,
    VM_PLACEMENT_AFFINITY: VM_MIGRATABLE,
    VM_PLACEMENT_HOST: VM_ANY_HOST,
    VM_CLUSTER: CLUSTER_NAME[0],
    VM_WATCHDOG_MODEL: "",
    VM_HIGHLY_AVAILABLE: False,
    VM_CPU_PINNING: [],
    VM_CPU_SHARES: 0,
    VM_CPU_MODE: "custom",  # TODO W/A for 1337181
    RNG_DEVICE: URANDOM_RNG
}

# general
FQDN_TIMEOUT = 130

VALIDATOR_IGNORE_LIST = [
    'watchdogs', 'cdroms', 'statistics', 'vm_pool', 'start_time', 'run_once',
    'guest_info', 'payloads', 'use_latest_template_version', 'name', 'disks',
    'stop_reason', 'placement_policy', 'guest_operating_system',
    'creation_time', 'snapshots', 'id', 'instance_type',  'numa_tune_mode',
    'guest_time_zone', 'stop_time', 'template', 'external_host_provider',
    'katello_errata', 'next_run_configuration_exists', 'floppies', 'tags',
    'initialization', 'quota', 'host', 'reported_devices', 'original_template',
    'vm', 'version', 'host_numa_nodes', 'sessions', 'status_detail',
    'affinity_labels', 'applications', 'fqdn', 'host_devices', 'nics',
]
VM_REMOVE_SNAPSHOT_TIMEOUT = 4000
VM_ACTION_TIMEOUT = 1000

# snapshot
SNAPSHOT_DESCRIPTION = ['snapshot_1', 'snapshot_2']

BASE_VM_VIRT = "base_vm_virt"

# Windows #
# OS types
WIN_10_OS = 'windows_10_64B'
WIN_2012_R2_64B_OS = 'windows_2012_R2_64B'
WIN_7_64B_OS = 'windows_7_64B'

DEFAULT_FILE_CONTENT = "line 1: test\n line 2: test"
DEFAULT_FILE_NAME = "test.txt"
WIN_ADMIN_USER = 'Administrator'
WIN_QE_USER = 'QE'
WIN_PASSWORD = 'Heslo123'
SYSTEM_PATH = "c:\\windows\\system32\\"
SEAL_COMMAND = (
    "{0}Sysprep\\sysprep.exe /generalize /oobe /shutdown /quiet".format(
        SYSTEM_PATH
    )
)
TMP_PATH = 'C:\\Windows\\Temp\\'
SYSTEM_INFO_NAMES = [
    "Host Name", "Product ID", "System Locale", "Input Locale", "Time Zone",
    "Domain"
]

# Sysprep files under(/usr/share/ovirt-engine/conf/sysprep) at the engine:
SYSPREP_FILE_ENG_PATH = "/usr/share/ovirt-engine/conf/sysprep"
WINDOWS_10_SYSPREP_FILE = "sysprep.w10x64"
WINDOWS_2012R2_SYSPREP_FILE = "sysprep.2k12x64"
WINDOWS_7_SYSPREP_FILE = "sysprep.w7x64"
WIN_OS_TO_SYSPREP_FILE = {
    WIN_10_OS: WINDOWS_10_SYSPREP_FILE,
    WIN_2012_R2_64B_OS: WINDOWS_2012R2_SYSPREP_FILE,
    WIN_7_64B_OS: WINDOWS_7_SYSPREP_FILE
}
CPU_MODEL_DENOM = cpumodel.CpuModelDenominator()
ENGINE_STAT_UPDATE_INTERVAL = 15
DD_CREATE_FILE_CMD = 'dd if=/dev/urandom of=%s bs=1M count=%s'
FILE_SIZE_IN_MB = 400
# Sparsify test
BAD_BLOCKS_CMD = 'badblocks -v %s1'

# Helper parameters
DEFAULT_JOB_TIMEOUT = 600
VIRSH_VM_LIST_CMD = "virsh -r list | grep "
VIRSH_VM_DUMP_XML_CMD = "virsh -r dumpxml "
VIRSH_VM_IOTHREADS_NUMBER_CMD = (
    "virsh -r dumpxml %s | grep -oP '(?<=<iothreads>).*?(?=</iothreads>)'"
)
VIRSH_VM_IOTHREADS_DRIVERS_CMD = "virsh -r dumpxml %s | grep 'iothread='"
VIRSH_VM_EMULATED_MACHINE_CMD = "virsh -r dumpxml %s | grep -o machine=\'.*\'"
VIRSH_VM_CPU_MODEL_CMD = "virsh -r dumpxml %s | grep -o '<model.*</model>'"
LSBLK_CMS = "lsblk | grep disk"
# pig command
LOAD_VM_COMMAND = (
    '/home/pig -v -p 1 -t 1 -m %s -l mem -s %s &> /tmp/OUT1 & echo $!'
)

# vm_actions
MIGRATION_ACTION = 'migration'
MEMORY_HOTPLUG_ACTION = 'memory_hotplug'
CPU_HOTPLUG_ACTION = 'cpu_hotplug'
SNAPSHOT_MEM_ACTION = 'snapshot_memory'
SNAPSHOT_NO_MEM_ACTION = 'snapshot_without_memory'
CLONE_ACTION = 'clone'
START_ACTION = 'start'
STOP_ACTION = 'stop'
SUSPEND_RESUME = 'suspend_resume'
CLOUD_INIT_CHECK = 'cloud_init_parameter_check'

CLONE_VM_NAME = "clone_vm_test_vm_actions"

# cloud init
CLOUD_INIT_IMAGE = 'cloud_init_GE_disk'
CLOUD_INIT_VM_NAME = "cloud_init_vm"
VM_IP = None
USER_PKEY = False
VM_USER_CLOUD_INIT_1 = 'cloud_user'
VM_USER_CLOUD_INIT_2 = 'cloud_user_2'
VM_USER_CLOUD_INIT = VM_USER_CLOUD_INIT_1
CLOUD_INIT_TEMPLATE = 'automation-cloud_init'
CLOUD_INIT_NIC_NAME = 'eth4'
CLOUD_INIT_HOST_NAME = 'cloud_init.testing.com'
CLOUD_INIT_VM_DISK_NAME = 'cloud_init_disk'
NEW_ZEALAND_TZ = "NZ"
NEW_ZEALAND_TZ_LIST = ["%s%s" % (NEW_ZEALAND_TZ, tz) for tz in ["DT", "ST"]]
MEXICO_TZ = "EST"
MEXICO_TZ_VALUE = "EST"
DNS_SERVER = "1.2.3.4"
DNS_SEARCH = "foo.test.com"
# cloud init check commands
CHECK_USER_IN_GUEST = 'cat /etc/passwd | grep -E %s'
CHECK_DNS_IN_GUEST = 'cat /etc/resolv.conf | grep -E %s'
CHECK_TIME_ZONE_IN_GUEST = 'date +%Z'
CHECK_HOST_NAME = 'hostname'
CHECK_FILE_CONTENT = 'cat /tmp/test.txt'
NIC_FILE_NAME = '/etc/sysconfig/network-scripts/ifcfg-eth4'
CHECK_NIC_EXIST = "grep %s %s" % (CLOUD_INIT_NIC_NAME, NIC_FILE_NAME)
PRE_CASE_CONDITIONS = {
    "set_authorized_ssh_keys": False,
    "cloud_init_user": VM_USER_CLOUD_INIT_1
}

IMPORT_V2V_TIMEOUT = 5600

# cloud-init IPv6 section
IPV6_ADDRESSES = [
        '2620:52:0:2342:21A:4AFF:FE16:8890',
        '2620:52::4aff:fe16:8890',
        '2620:0052:0000:2342:021a:4aff:fe16:8890']
IPV6_IPS = [data_struct.Ip(
    address=address,
    gateway='2620:52:0:2342::1',
    netmask='64',
    version='v6'
) for address in IPV6_ADDRESSES]
IPV4_IPS = [
    data_struct.Ip(
        address='10.0.0.1',
        gateway='10.0.0.254',
        netmask='255.255.255.0',
        version='v4'
    )
]
NETWORKING_OPTIONS = {
    'name': ['eth1'],
    'boot_protocol': ['static', 'dhcp', 'none'],
    'ipv6_boot_protocol': ['static', 'dhcp', 'none'],
    'ip': IPV4_IPS,
    'ipv6': IPV6_IPS,
}
