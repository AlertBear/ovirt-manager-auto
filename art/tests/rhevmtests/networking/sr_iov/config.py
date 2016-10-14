#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature config
"""
import rhevmtests.helpers as global_helper

GENERAL_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=5, prefix="general_sriov_vnic"
)
VM_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=5, prefix="vm_sriov_vnic"
)
TEMPLATE_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=5, prefix="template_sriov_vnic"
)

HOST_O_SRIOV_NICS_OBJ = None  # Filled in setup_package
HOST_1_SRIOV_NICS_OBJ = None  # Filled in setup_package
HOST_0_PF_LIST = list()  # Filled in setup_package
HOST_1_PF_LIST = list()  # Filled in setup_package
HOST_0_PF_NAMES = list()  # Filled in setup_package
HOST_1_PF_NAMES = list()  # Filled in setup_package
HOST_0_PF_OBJECT = None  # Filled in setup_package
HOST_0_VFS_LIST = None  # Filled in setup_package

HOSTS_PARAM_DICT = None

VM_DISK_SIZE = 1024
NUM_VF_PATH = "/sys/class/net/%s/device/sriov_numvfs"
MAC_ADDR_FILE = "/sys/class/net/%s/address"
BW_VALUE = 10
BURST_VALUE = 100
VLAN_IDS = [str(i) for i in xrange(2, 60)]
NETWORK_QOS = "network_qos"
LABELS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=2, prefix="label"
)
GENERAL_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="gen"
)
VM_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="vm"
)
IMPORT_EXPORT_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="IE"
)
GENERAL_DICT = {
    GENERAL_NETS[4][0]: {
        "required": "false"
    },
    GENERAL_NETS[5][0]: {
        "required": "false"
    }
}

VM_DICT = {
    VM_NETS[1][0]: {
        "required": "false"
    },
    VM_NETS[1][1]: {
        "required": "false"
    },
    VM_NETS[2][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[2]
    },
    VM_NETS[3][0]: {
        "required": "false"
    },
    VM_NETS[3][1]: {
        "required": "false"
    },
    VM_NETS[3][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[3]
    },
    VM_NETS[3][3]: {
        "required": "false"
    },
    VM_NETS[4][0]: {
        "required": "false",
    },
    VM_NETS[4][1]: {
        "required": "false",
    },
    VM_NETS[4][2]: {
        "required": "false",
    },
    VM_NETS[4][3]: {
        "required": "false",
    },
}

IMPORT_EXPORT_DICT = {
    IMPORT_EXPORT_NETS[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[4],
    },
    IMPORT_EXPORT_NETS[1][1]: {
        "required": "false"
    },
}
