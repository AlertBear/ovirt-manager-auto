"""
Virt - serial console config
"""

import uuid

import pytest
from rhevmtests.compute.virt.config import *  # flake8: noqa
from art.test_handler.tools import polarion, bz
from rhevmtests import helpers
from rhevmtests.networking import config as net_conf

VIRT_CONSOLE_VM_SANITY = "virt_console_VM_sanity"
VIRT_CONSOLE_VM_ADV = "virt_console_vm_adv"
VIRT_CONSOLE_VM_SYSTEM = "virt_console_vm"
VIRT_CONSOLE_CLONE_VM_NAME = "virt_console_vm_clone"
VIRT_CONSOLE_VM_IMPORT_NEW = "virt_console_vm_imported"

VIRT_CONSOLE_TEMPLATE_IMPORT_NEW = "virt_console_template_imported"
VIRT_CONSOLE_TEMPLATE = "virt_console_template"
VIRT_GLANCE_IMAGE = "rhv40_el73_ge_Disk1"
VIRT_CONSOLE_VM_INSTANCE_TYPE = "virt_console_instance_type"

VIRT_NEW_DISK_ALIAS = "GlanceDisk-{rand_ind}".format(
    rand_ind=uuid.uuid4().fields[0]
)

VIRT_CONSOLE_VM_NIC = net_conf.VM_NICS[-1]

VIRSH_DUMP_CMD_RAM = 'virsh -r dumpxml {vm_id} | grep ram'
VIRSH_DUMP_CMD_GC = "virsh -r dumpxml {vm_id} | grep 'graphics type'"
KVM_PROCESS_INFO_CMD = 'ps -fade | grep kvm'

VIRT_CONSOLE_VM_DICT_SANITY = {}
VIRT_CONSOLE_VM_DICT_ADV = {}

VIRSH_CONF_FILE = '/etc/libvirt/qemu.conf'
VIRSH_CONF_SEARCH_PARAMS = [
    'remote_display_port_min=5900',
    'remote_display_port_max=6923'
]

IMPORT_EXPORT_HEADLESS_ARGS = "obj_type", "obj_name"
IMPORT_EXPORT_HEADLESS_VAL = [
    polarion("RHEVM-19527")(
        [
            "template",
            VIRT_CONSOLE_TEMPLATE
        ]
    ),
    polarion("RHEVM-19409")(
        [
            "vm",
            VIRT_CONSOLE_VM_SYSTEM
        ]
    )
]

HEADLESS_STATE_ARGS = "console_protocol,  obj_name, obj_type"
HEADLESS_STATE_PARAMS = [
    polarion("RHEVM-19537")(
        pytest.mark.skipif(PPC_ARCH, reason=PPC_SKIP_MESSAGE)(  # noqa: F405
            [
                "spice",
                VIRT_CONSOLE_VM_SYSTEM,
                "vm"
            ]
        )),
    polarion("RHEVM-19538")(
        [
            "vnc",
            VIRT_CONSOLE_VM_SYSTEM,
            "vm"
        ]
    ),
    polarion("RHEVM-19539")(
        pytest.mark.skipif(PPC_ARCH, reason=PPC_SKIP_MESSAGE)(  # noqa: F405
            [
                "spice_plus_vnc",
                VIRT_CONSOLE_VM_SYSTEM,
                "vm"
            ]
        )),
    polarion("RHEVM-19540")(
        pytest.mark.skipif(PPC_ARCH, reason=PPC_SKIP_MESSAGE)(  # noqa: F405
            [
                "spice",
                VIRT_CONSOLE_TEMPLATE,
                "template"
            ]
        )),
    polarion("RHEVM-19541")(
        [
            "vnc",
            VIRT_CONSOLE_TEMPLATE,
            "template"
        ]
    ),
    polarion("RHEVM-19542")(
        pytest.mark.skipif(PPC_ARCH, reason=PPC_SKIP_MESSAGE)(  # noqa: F405
            [
                "spice_plus_vnc",
                VIRT_CONSOLE_TEMPLATE,
                "template"
            ]
        )),
    polarion("RHEVM-19543")(
        [
            "spice",
            VIRT_CONSOLE_VM_INSTANCE_TYPE,
            "instance_type"
        ]
    ),
    polarion("RHEVM-19544")(
        [
            "vnc",
            VIRT_CONSOLE_VM_INSTANCE_TYPE,
            "instance_type"
        ]
    ),
    polarion("RHEVM-19545")(
        [
            "spice_plus_vnc",
            VIRT_CONSOLE_VM_INSTANCE_TYPE,
            "instance_type"
        ]
    )
]

VV_FILE_ARGS = "console_protocol"
VV_FILE_VALUES_PARAMS = [
    polarion("RHEVM-19534")(
        pytest.mark.skipif(PPC_ARCH, reason=PPC_SKIP_MESSAGE)  # noqa: F405
        ("spice")
    ),
    polarion("RHEVM-19535")("vnc"),
    polarion("RHEVM-19536")(
        pytest.mark.skipif(PPC_ARCH, reason=PPC_SKIP_MESSAGE)  # noqa: F405
        ("spice_plus_vnc")
    ),
]

VV_FILE_FIELDS_PARAMS = [
    polarion("RHEVM-19531")(bz({"1429482": {}})("spice")),
    polarion("RHEVM-19532")("vnc"),
    polarion("RHEVM-19533")(bz({"1429482": {}})("spice_plus_vnc"))
]
GB = helpers.get_gb(1)

INSTANCE_TYPE_PARAMS = {
    'description': 'test_instance_type',
    'memory': 2 * GB,
    'cpu_sockets': 1,
    'cpu_threads': 1,
    'cpu_cores': 1,
    'virtio_scsi': True,
    'display_type': 'spice',
    'monitors': 1,
    'disconnect_action': 'NONE',
    'smartcard_enabled': False,
    'single_qxl_pci': False,
    'serial_console': True,
    'migration_downtime': 100,
    'auto_converge': 'true',
    'compressed': 'false',
    'migration_policy': '00000000-0000-0000-0000-000000000000',
    'boot': 'hd',
    'soundcard_enabled': False,
    'io_threads': 2,
    'memory_guaranteed': 2 * GB,
    'highly_available': False,
    'availablity_priority': 2,
    'max_memory': 4 * GB
}

VV_FILE_FIELDS = {
    'spice':
        {
            '[virt-viewer]': [
                'type',
                'host',
                'port',
                'password',
                'delete-this-file',
                'fullscreen',
                'title',
                'toggle-fullscreen',
                'release-cursor',
                'secure-attention',
                'tls-port',
                'enable-smartcard',
                'enable-usb-autoshare',
                'usb-filter',
                'tls-ciphers',
                'host-subject',
                'ca',
                'secure-channels',
                'versions',
                'newer-version-url'
            ],
            '[ovirt]': [
                'host',
                'vm-guid',
                'sso-token',
                'admin',
                'ca'
            ]
        },
    'vnc':
        {
            '[virt-viewer]': [
                'type',
                'host',
                'port',
                'password',
                'delete-this-file',
                'fullscreen',
                'toggle-fullscreen',
                'release-cursor',
                'secure-attention',
                'versions',
                'newer-version-url',
            ],
            '[ovirt]': [
                'host',
                'vm-guid',
                'sso-token',
                'admin',
                'ca'
            ]
        }
}
