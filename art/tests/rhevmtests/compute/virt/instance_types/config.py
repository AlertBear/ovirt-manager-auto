from rhevmtests.compute.virt.config import *  # flake8: noqa
import rhevmtests.helpers as helper

INSTANCE_TYPE_NAME = 'test_instance_type'
NAME_AFTER_UPDATE = 'test_update_instance_type'
TINY_INSTANCE_TYPE = 'Tiny'
MEDIUM_INSTANCE_TYPE = 'Medium'
SMALL_INSTANCE_TYPE = 'Small'
LARGE_INSTANCE_TYPE = 'Large'
XLARGE_INSTANCE_TYPE = 'XLarge'
INSTANCE_TYPE_OBJECT = None
INSTANCE_TYPE_VM = 'instance_type_test_vm'
TEMPLATE_VM = 'vm_for_template'
NEW_TEMPLATE_NAME = 'instance_type_test_template'
OBJ_CREATION_TIMEOUT = 5  # BZ:1450000
INSTANCE_TYPE_PARAMS = {
    'description': 'I am a test',
    'memory': MB_SIZE_256,
    'cpu_sockets': 2,
    'cpu_threads': 2,
    'cpu_cores': 2,
    # 'custom_emulated_machine': 'pc', TODO: pending bz# 1390172
    # 'custom_cpu_model': 'Conroe',  TODO: pending bz# 1390172
    'virtio_scsi': True,
    'display_type': 'spice' if not PPC_ARCH else 'vnc',
    'monitors': 4 if not PPC_ARCH else 1,
    'disconnect_action': 'NONE',
    'smartcard_enabled': not PPC_ARCH,
    'single_qxl_pci': not PPC_ARCH,
    'serial_console': True,
    'migration_downtime': 100,
    'auto_converge': 'true',
    'compressed': 'false',
    'migration_policy': '00000000-0000-0000-0000-000000000000',
    'boot': 'network hd',
    'soundcard_enabled': not PPC_ARCH,
    'io_threads': 2,
    'memory_guaranteed': MB_SIZE_256,
    'highly_available': True,
    'availablity_priority': 2,
    'max_memory': GB
}

TEMPLATE_PARAMS = {
    'memory': helper.get_gb(8),
    'cpu_sockets': 1,
    'cpu_threads': 1,
    'cpu_cores': 1,
    # 'custom_emulated_machine': 'q35',  TODO: pending bz# 1390172
    # 'custom_cpu_model': 'Penryn',  TODO: pending bz# 1390172
    'virtio_scsi': False,
    'monitors': 1,
    'disconnect_action': 'LOCK_SCREEN',
    'smartcard_enabled': False,
    'single_qxl_pci': False,
    'serial_console': False,
    'migration_downtime': -1,
    'migration_policy': '80554327-0569-496b-bdeb-fcbbf52b827b',
    'boot': 'cdrom',
    'soundcard_enabled': False,
    'io_threads': 1,
    'memory_guaranteed': helper.get_gb(8),
    'highly_available': False,
    'availablity_priority': 1,
    'max_memory': helper.get_gb(8)
}

DEFAULT_INSTANCES_PARAMS = {
    TINY_INSTANCE_TYPE: {'highly_available': False},
    MEDIUM_INSTANCE_TYPE: {
        'cpu_sockets': 2,
        'cpu_threads': 1,
        'cpu_cores': 1,
        # 'custom_emulated_machine': '',  TODO: pending bz# 1390172
        # 'custom_cpu_model': '',  TODO: pending bz# 1390172
    },
    SMALL_INSTANCE_TYPE: {
        'serial_console': False,
        'display_type': 'spice',
        'smartcard_enabled': False,
        'single_qxl_pci': False,
        'soundcard_enabled': False,
        'boot': 'hd'
    },
    LARGE_INSTANCE_TYPE: {
        'migration_downtime': -1,
        'migration_policy': '',
    },
    XLARGE_INSTANCE_TYPE: {
        'memory': 8 * GB,
        'memory_guaranteed': 8 * GB,
        'ballooning': False,
        'io_threads': 0,
        'virtio_scsi': False,
    }
}

INSTANCE_TYPE_SANITY_DICT = {'name': None, 'sockets': 2, 'io_threads': 4}
EDIT_TINY_INSTANCE_DICT = {
    'instance_type_id': None, 'memory': None, 'high_availability': True
}
EDIT_MEDIUM_INSTANCE_DICT = {
    'instance_type_id': None, 'sockets': 4, 'cores': 2, 'threads': 2
}
EDIT_SMALL_INSTANCE_DICT = {
    'instance_type_id': None,
    'serial_console': True,
    'display': 'vnc',
    'smartcards': not PPC_ARCH,
    'single_qxl_pci': not PPC_ARCH,
    'soundcard': not PPC_ARCH, 'boot_devices': ['cdrom']
}
EDIT_LARGE_INSTANCE_DICT = {
    'instance_type_id': None,
    'migration_policy': '00000000-0000-0000-0000-000000000000',
    'migration_downtime': 100
}
EDIT_XLARGE_INSTANCE_DICT = {
    'instance_type_id': None,
    'io_threads': 2,
    'memory': 2 * GB,
    'memory_guaranteed': 2 * GB,
    'balooning': True,
    'virtio_scsi': True
}
INSTANCE_TYPE_AND_TEMPLATE_DICT = {
    'io_threads': 2,
    'sockets': 2,
    'cores': 2,
    'threads': 2,
    'memory': MB_SIZE_256,
    'memory_guaranteed': MB_SIZE_256,
    'high_availability': True
}
