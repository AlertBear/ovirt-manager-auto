#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature config
"""
import rhevmtests.helpers as global_helper
from rhevmtests.networking import (
    helper as network_helper,
    config as conf
)

GENERAL_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=5, prefix="general_sriov_vnic"
)
VM_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=6, num_of_objects=5, prefix="vm_sriov_vnic"
)
TEMPLATE_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=5, prefix="template_sriov_vnic"
)
MIGRATION_TEST_VNICS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=5, prefix="migration_sriov_vnic"
)

# All the following objects will be filled during runtime
HOST_O_SRIOV_NICS_OBJ = None
HOST_1_SRIOV_NICS_OBJ = None
HOST_0_PF_LIST = list()
HOST_1_PF_LIST = list()
HOST_0_PF_NAMES = list()
HOST_1_PF_NAMES = list()
HOST_0_PF_OBJECTS = None
HOST_1_PF_OBJECTS = None
# First listed SR-IOV PF NIC object of HOST-0
HOST_0_PF_OBJECT_1 = None
# Second listed SR-IOV PF NIC object of HOST-0
HOST_0_PF_OBJECT_2 = None
# First listed SR-IOV PF NIC object of HOST-1
HOST_1_PF_OBJECT_1 = None
HOST_NAME = None
PF_OBJECT = None
HOSTS_PARAM_DICT = None

SD_NAME = None

MIGRATION_TIMEOUT = 300
MIGRATION_NIC_1_MAC = None  # Filled in remove_vnic_and_save_mac fixture
SRIOV_MIGRATION_VM = "SR-IOV-migration-vm"
VM_DISK_SIZE = 1024
NUM_VF_PATH = "/sys/class/net/%s/device/sriov_numvfs"
MAC_ADDR_FILE = "/sys/class/net/%s/address"
BW_VALUE = 10
BURST_VALUE = 100
NETWORK_QOS = "network_qos"
REFRESH_CAPS_CODE = 606
LABELS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=2, prefix="sriov_label"
)
GENERAL_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="sriov_gen"
)
VM_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="sriov_vm"
)
IMPORT_EXPORT_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="sriov_IE"
)
MIGRATION_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="sriov_mig"
)

IPS = network_helper.create_random_ips(mask=24)

CASE_05_GENERAL_NETS = {
    GENERAL_NETS[5][0]: {
        "required": "false"
    }
}

CASE_01_VM_NETS = {
    VM_NETS[1][0]: {
        "required": "false"
    },
    VM_NETS[1][1]: {
        "required": "false"
    }
}

CASE_02_VM_NETS = {
    VM_NETS[2][0]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    }
}

CASE_03_VM_NETS = {
    VM_NETS[3][0]: {
        "required": "false"
    },
    VM_NETS[3][1]: {
        "required": "false"
    },
    VM_NETS[3][2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    VM_NETS[3][3]: {
        "required": "false"
    }
}

CASE_04_VM_NETS = {
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
    }
}

CASE_05_VM_NETS = {
    VM_NETS[5][0]: {
        "required": "false",
    }
}

CASE_06_VM_NETS = {
    VM_NETS[6][0]: {
        "required": "false"
    }
}

CASE_01_IMPORT_EXPORT_NETS = {
    IMPORT_EXPORT_NETS[1][0]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
    IMPORT_EXPORT_NETS[1][1]: {
        "required": "false"
    },
}

CASE_01_MIGRATION_NETS = {
    MIGRATION_NETS[1][0]: {
        "required": "false"
    },
    MIGRATION_NETS[1][1]: {
        "required": "false"
    },
    MIGRATION_NETS[1][2]: {
        "required": "false"
    }
}
