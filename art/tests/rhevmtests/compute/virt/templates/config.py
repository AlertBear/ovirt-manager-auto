import copy
from rhevmtests.compute.virt.config import *  # flake8: noqa
import rhevmtests.compute.virt.config as virt_conf

TEMPLATE_VALIDATOR_IGNORE_LIST = copy.deepcopy(virt_conf.VALIDATOR_IGNORE_LIST)
TEMPLATE_VALIDATOR_IGNORE_LIST += ['has_illegal_images']

MEMORY_SIZE_1 = GB
MEMORY_SIZE_2 = GB/2
BASE_VM_1 = 'template_base_vm_1'
BASE_VM_2 = 'template_base_vm_2'
VM_NO_DISK_1 = 'vm_no_disk_1'
VM_NO_DISK_2 = 'vm_no_disk_2'
# NO_DISK_VMS = [VM_NO_DISK_1, VM_NO_DISK_2]
TEMPLATE_NAMES = {
    'test_template_1_base': [1, 2],
    'test_template_2_dummy': [1],
}
DUMMY_DC = 'test_template_dummy_dc'
DUMMY_CLUSTER = 'test_template_dummy_cluster'
NON_MASTER_DOMAIN = None
TEMPLATE_LIST = None
TEMPLATE_NIC = 'template_nic'
UPDATED_NIC = 'template_update_nic'

BLANK = 'Blank'
UNASSIGNED = ENUMS['unassigned']
RHEL6 = ENUMS['rhel6']
WINDOWS7 = ENUMS['windows7']
PPC_RHEL7 = ENUMS['rhel7ppc64']
PPC_RHEL6 = ENUMS['rhel6ppc64']
STATLESS_VM = True
START_IN_PAUSE = True
DELETE_PROTECTED = True
SPICE = ENUMS['display_type_spice']
VNC = ENUMS['display_type_vnc']
DISPLAY_MONITOR_1 = 2
DISPLAY_MONITOR_2 = 1
SERIAL_NUMBER = 4
USB_TYPE_1 = 'native'
VM_1_SOCKETS = 4
VM_1_CORES = 1
VM_1_THREADS = 2
VM_2_SOCKETS = 2
VM_2_CORES = 2
VM_2_THREADS = 1
CUSTOM_EMULATED_MACHINE = 'pc'
PPC_EMULATED_MACHINE = 'pseries'
CUSTOM_CPU_MODEL = 'Penryn'
PPC_CPU_MODEL = 'POWER8'
TIMEZONE_MOSCOW_LINUX = 'Europe/Moscow'
TIMEZONE_TOKYO_WINDOWS = 'Tokyo Standard Time'
DISCONNECT_ACTION_1 = 'LOGOUT'
DISCONNECT_ACTION_2 = 'REBOOT'
SOUND_CARD_ENABLED = True
VIRTIO_SCSI = True
MEMORY_BALOONING = True
HA = True
FILE_TRANSFER_OFF = False
MEDIUM_HA = 50
MIGRATION_DOWN_TIME = 1000
IO_THREADS = 2
BOOT_SEQUENCE_1 = 'network hd'
BOOT_SEQUENCE_2 = 'cdrom'
BOOT_MENU = True
DOMAIN_NAME = 'foo.bar'
USER_DOMAIN = "internal-authz"
USER = 'user1'
USER_ROLE = ENUMS['role_name_user_role']
TEMPLATE_ROLE = ENUMS['role_name_template_admin']
GROUP_EVERYONE = 'Everyone'
# cloud init stuff - blocked by bz# 1253710 solved only in 4.0

BASE_VM_1_PARAMETERS = {
    'cluster': CLUSTER_NAME[0],
    'type': VM_TYPE_DESKTOP,
    'memory': MEMORY_SIZE_1,
    'stateless': STATLESS_VM,
    'protected': DELETE_PROTECTED,
    'start_paused': START_IN_PAUSE,
    'display_type': SPICE if not PPC_ARCH else VNC,
    'monitors': DISPLAY_MONITOR_1 if not PPC_ARCH else None,
    'os_type': RHEL6 if not PPC_ARCH else PPC_RHEL6,
    'serial_number': SERIAL_NUMBER,
    # 'usb_type': USB_TYPE_1,  # BZ#1327278
    'cpu_cores': VM_1_CORES,
    'cpu_sockets': VM_1_SOCKETS,
    'cpu_threads': VM_1_THREADS,
    'custom_emulated_machine': (
        CUSTOM_EMULATED_MACHINE if not PPC_ARCH else PPC_EMULATED_MACHINE
    ),
    'custom_cpu_model': CUSTOM_CPU_MODEL if not PPC_ARCH else PPC_CPU_MODEL,
    'time_zone': TIMEZONE_MOSCOW_LINUX,
    'disconnect_action': DISCONNECT_ACTION_1,
    'migration_downtime': MIGRATION_DOWN_TIME,
    'cpu_shares': CPU_SHARE_MEDIUM,
    'memory_guaranteed': MEMORY_SIZE_1,
    'ballooning': MEMORY_BALOONING,
    'io_threads': IO_THREADS,
    'boot': BOOT_SEQUENCE_1,
    # 'boot_menu': BOOT_MENU,  # BZ#1328093
}

BASE_VM_2_PARAMETERS = {
    'cluster': CLUSTER_NAME[0],
    'type': VM_TYPE_SERVER,
    'memory': MEMORY_SIZE_2,
    'display_type': VNC,
    'monitors': DISPLAY_MONITOR_2,
    'os_type': WINDOWS7 if not PPC_ARCH else PPC_RHEL7,
    'domainName': DOMAIN_NAME if not PPC_ARCH else None,
    'cpu_cores': VM_2_CORES,
    'cpu_sockets': VM_2_SOCKETS,
    'cpu_threads': VM_2_THREADS,
    'time_zone': TIMEZONE_TOKYO_WINDOWS if not PPC_ARCH else None,
    'disconnect_action': DISCONNECT_ACTION_1,
    'highly_available': HA,
    'availablity_priority': MEDIUM_HA,
    'cpu_shares': CPU_SHARE_LOW,
    'memory_guaranteed': MEMORY_SIZE_2,
    'boot': BOOT_SEQUENCE_2,
    'file_transfer_enabled': FILE_TRANSFER_OFF if not PPC_ARCH else None,
}

BASE_VM_MAP = {
    BASE_VM_1: BASE_VM_1_PARAMETERS,
    BASE_VM_2: BASE_VM_2_PARAMETERS,
}
BASE_VM_LIST = BASE_VM_MAP.keys()
BASE_VM_LIST.sort()
