"""
Virt - Reg vms
"""
import copy
from rhevmtests.compute.virt.config import *  # flake8: noqa
import rhevmtests.helpers as global_helper

KVM_PROVIDER = 'kvm'
VMWARE_PROVIDER_V6 = 'vmware_v6'        # vmware vsphere 6
VMWARE_PROVIDERS = [VMWARE_PROVIDER_V6]
TWO_GB = global_helper.get_gb(2)
FOUR_GB = global_helper.get_gb(4)
NIC_NAME = 'v2v_nic'
TIMEOUT_IMPORT_START = 120
NUMBER_OF_DISKS = 20

# VM names in RHEVM
V2V_RHEL_7_2_NAME = 'test_v2v_rhel_7_2'
V2V_WIN_10_NAME = 'test_v2v_windows_10'
V2V_WIN_7_NAME = 'test_v2v_windows_7'
V2V_WIN_2012_NAME = 'test_v2v_windows_2012'


# VMWare details
# VMS name
VM_WARE_RHEL_7_2 = 'test_v2v_rhel_7_2_automation_vmware'
VM_WARE_WINDOWS_7 = 'test_v2v_windows_7_automation_vmware'
VM_WARE_WINDOWS_10 = 'test_v2v_windows_10_automation_vmware'
VM_WARE_WINDOWS_12 = 'test_v2v_windows_2012_automation_vmware'
VM_WARE_SPECIAL_CHARS = 'vm_!@#$%_$_special_chars'
VM_WARE_WITH_20_DISKS = 'test_vm_with_20_disks_automation_vmware'
VM_WARE_WITH_35_DEVICES = 'test_v2v_with_35_devices_automation_vmware'
VM_WARE_WITH_LARGE_DISK = 'test_v2v_with_large_disk_automation_vmware'
VM_WARE_WITH_ISCSI_DISK = 'test_v2v_with_iscsi_automation_vmware'
VM_WARE_WITH_MIX_DEVICES = 'test_v2v_with_mix_device_automation_vmware'
VM_WARE_WITH_NAME_64_CHARS = (
    'test_vm_long_name64aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
)
VM_WITH_LONG_NAME = 'test_vm_long_name64'
VM_WARE_WITH_NAME_MORE_THEN_64_CHARS = (
    'test_vm_long_name_67aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
)
VM_WARE_WITH_SNAPSHOT = 'test_v2v_with_snapshot_automation_vmware'
VM_WARE_SMALL_DISK = 'test_v2v_small_disk_automation_vmware'


# connection info
VM_WARE_USERNAME = "administrator"
VM_WARE_PASSWORD = 'Heslo123_'
VM_WARE_PROVIDER = 'vmware'
VM_WARE_URL = (
        "vpx://{user}@{vcenter}/{esxi_host}?no_verify=1".format(
            vcenter='compute-vmware-env.scl.lab.tlv.redhat.com/Datacenter',
            esxi_host='cougar02.scl.lab.tlv.redhat.com',
            user=VM_WARE_USERNAME
        )
    )
# KVM details
KVM_RHEL_7 = 'test_v2v_rhel_7_2_automation_kvm'
KVM_USERNAME = VDC_ROOT_USER
KVM_PASSWORD = VDC_ROOT_PASSWORD
KVM_URL = "qemu+tcp://root@compute-kvm-env.scl.lab.tlv.redhat.com/system"

# windows iso driver
VIRTIO_WIN_DRIVER = 'virtio-win-1.9.1.iso'

# Configuration for VMs imported from the external provider
# user_name, password, provider, url - credentials to access external provider
# name - VM name on the external provider
# vm_name, cluster, storage_domain - VM parameters for RHEV
EXTERNAL_PROVIDER_INFO = {
    VMWARE_PROVIDER_V6: {
        "user_name": VM_WARE_USERNAME,
        "password": VM_WARE_PASSWORD,
        "provider": VM_WARE_PROVIDER,
        "url": VM_WARE_URL,
    },
    KVM_PROVIDER: {
        "user_name": KVM_USERNAME,
        "password": KVM_PASSWORD,
        "provider": KVM_PROVIDER,
        "url": KVM_URL,
    },
}

IMPORT_TO_CLUSTER = CLUSTER_NAME[0]
IMPORT_TO_STORAGE = STORAGE_NAME[0]
DISK_IMAGE_SPARSE = False

# Default info to import VM
IMPORT_DATA = {
    "cluster": CLUSTER_NAME[0],
    "storage_domain": STORAGE_NAME[0],
    "engine_url": ENGINE_URL,
    "sparse": False
}
# Configuration to compare imported VM to
# nic_mac_address is taken from the environment during test execution
BASE_CONFIG = {
    "memory": TWO_GB,
    "sockets": 2,
    "cores": 1,
    "threads": 1,
    "disk_size": global_helper.get_gb(8),
    'nic_mac_address': {
        'start': '',
        'end': ''
    }
}
KVM_RHEL_7_CONFIG = {}
KVM_RHEL_7_CONFIG.update(BASE_CONFIG)
KVM_RHEL_7_CONFIG['sockets'] = 2


V2V_RHEL_7_2_CONFIG = {}
V2V_RHEL_7_2_CONFIG.update(BASE_CONFIG)
V2V_RHEL_7_2_CONFIG['sockets'] = 2

VM_WARE_WITH_20_DISKS_CONFIG = {}
VM_WARE_WITH_20_DISKS_CONFIG.update(BASE_CONFIG)
VM_WARE_WITH_20_DISKS_CONFIG['sockets'] = 1
VM_WARE_WITH_20_DISKS_CONFIG['cores'] = 1
VM_WARE_WITH_20_DISKS_CONFIG['disk_size'] = global_helper.get_gb(10)


VM_WARE_WITH_LARGE_DISK_CONFIG = {}
VM_WARE_WITH_LARGE_DISK_CONFIG.update(BASE_CONFIG)
VM_WARE_WITH_LARGE_DISK_CONFIG['disk_size'] = global_helper.get_gb(40)

V2V_COMMON_CONFIG = {}
V2V_COMMON_CONFIG.update(BASE_CONFIG)

V2V_WINDOWS_CONFIG = {}
V2V_WINDOWS_CONFIG.update(BASE_CONFIG)
V2V_WINDOWS_CONFIG['disk_size'] = global_helper.get_gb(25)
V2V_WINDOWS_CONFIG['sockets'] = 1
V2V_WINDOWS_CONFIG['cores'] = 1
V2V_WINDOWS_CONFIG['memory'] = FOUR_GB

EXTERNAL_VM_CONFIGURATIONS = {
    V2V_RHEL_7_2_NAME: V2V_RHEL_7_2_CONFIG,
    VM_WITH_LONG_NAME: V2V_COMMON_CONFIG,
    VM_WARE_WITH_NAME_MORE_THEN_64_CHARS: V2V_COMMON_CONFIG,
    VM_WARE_WITH_SNAPSHOT: V2V_COMMON_CONFIG,
    VM_WARE_SPECIAL_CHARS: V2V_COMMON_CONFIG,
    VM_WARE_WITH_LARGE_DISK: VM_WARE_WITH_LARGE_DISK_CONFIG,
    V2V_WIN_7_NAME: V2V_WINDOWS_CONFIG,
    V2V_WIN_10_NAME: V2V_WINDOWS_CONFIG,
    V2V_WIN_2012_NAME: V2V_WINDOWS_CONFIG,
    VM_WARE_SMALL_DISK: V2V_COMMON_CONFIG,
    VM_WARE_WITH_20_DISKS: VM_WARE_WITH_20_DISKS_CONFIG,
    KVM_RHEL_7: KVM_RHEL_7_CONFIG
}
# list of all the VM that test is created
ALL_V2V_VMS = [
    KVM_RHEL_7, V2V_RHEL_7_2_NAME, V2V_WIN_10_NAME, V2V_WIN_7_NAME,
    V2V_WIN_2012_NAME, VM_WARE_SMALL_DISK, VM_WARE_SPECIAL_CHARS,
    VM_WARE_WITH_20_DISKS, VM_WARE_WITH_35_DEVICES, VM_WARE_WITH_ISCSI_DISK,
    VM_WITH_LONG_NAME, VM_WARE_RHEL_7_2
]
# List of values to compare or imported VM
V2V_VALUES_TO_COMPARE = [
    'memory',
    'sockets',
    'cores',
    'threads',
    'nic_mac_address'
]

# maps vm name on provider to vm name on rhevm
# (vm_name_on_provider, vm_name_on_rhevm, virtio_win_driver)
VMS_TO_IMPORT = [
    (VM_WARE_RHEL_7_2, V2V_RHEL_7_2_NAME, None),
    (VM_WARE_WINDOWS_7, V2V_WIN_7_NAME, VIRTIO_WIN_DRIVER),
    (VM_WARE_WINDOWS_10, V2V_WIN_10_NAME, VIRTIO_WIN_DRIVER),
    (VM_WARE_WINDOWS_12, V2V_WIN_2012_NAME, VIRTIO_WIN_DRIVER),
    (VM_WARE_WITH_NAME_64_CHARS, VM_WITH_LONG_NAME, None),
    (VM_WARE_WITH_20_DISKS, VM_WARE_WITH_20_DISKS, None)
]
