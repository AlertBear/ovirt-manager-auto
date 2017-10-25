"""
Virt - Reg vms
"""
import copy
import rhevmtests.helpers as global_helper
from rhevmtests.virt.config import *  # flake8: noqa

TWO_GB = global_helper.get_gb(2)
NIC_NAME = 'v2v_nic'
WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
RHEL_TZ = ENUMS['timezone_rhel_etc_gmt']
# Timeout for VM creation in Vmpool
VMPOOL_TIMEOUT = 30
RHEL6_64 = ENUMS['rhel6x64']
WIN_2008 = ENUMS['windows2008r2x64']
WIN_7 = ENUMS['windows7']

ticket_expire_time = 120
template_name = TEMPLATE_NAME[0]

# VM name for RHEL in RHEVM
V2V_RHEL_7_2_NAME = 'test_v2v_rhel_7_2'
# VMWare details
VM_WARE_RHEL_7_2 = 'test_v2v_rhel_7_2_automation_vmware'
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
KVM_PROVIDER = 'kvm'
KVM_URL = "qemu+tcp://root@compute-kvm-env.scl.lab.tlv.redhat.com/system"
VIRTIO_WIN_DRIVER = 'virtio-win-1.8.0.iso'

# Configuration for VMs imported from the external provider
# user_name, password, provider, url - credentials to access external provider
# name - VM name on the external provider
# vm_name, cluster, storage_domain - VM parameters for RHEV
EXTERNAL_VM_IMPORTS = {
    'vmware': {
        "name": VM_WARE_RHEL_7_2,
        "vm": V2V_RHEL_7_2_NAME,
        "cluster": CLUSTER_NAME[0],
        "storage_domain": STORAGE_NAME[0],
        "user_name": VM_WARE_USERNAME,
        "password": VM_WARE_PASSWORD,
        "provider": VM_WARE_PROVIDER,
        "url": VM_WARE_URL,
        "engine_url": ENGINE_URL,
        "sparse": False,
    },
    'kvm': {
        "name": KVM_RHEL_7,
        "vm": V2V_RHEL_7_2_NAME,
        "cluster": CLUSTER_NAME[0],
        "storage_domain": STORAGE_NAME[0],
        "user_name": KVM_USERNAME,
        "password": KVM_PASSWORD,
        "provider": KVM_PROVIDER,
        "url": KVM_URL,
        "engine_url": ENGINE_URL,
        "sparse": False,
    },
}
# Configuration to compare imported VM to
# nic_mac_address is taken from the environment during test execution
EXTERNAL_VM_CONFIGURATIONS = {
    'rhel72': {
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
}
V2V_VALIDATOR_IGNORE_LIST = copy.deepcopy(VALIDATOR_IGNORE_LIST)
V2V_VALIDATOR_IGNORE_LIST += ['cluster']
V2V_VMS = [V2V_RHEL_7_2_NAME]
# List of values to compare or imported VM
V2V_VALUES_TO_COMPARE = [
    'memory',
    'sockets',
    'cores',
    'threads',
    'disk_size',
    'nic_mac_address'
]
