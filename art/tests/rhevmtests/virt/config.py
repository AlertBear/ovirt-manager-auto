"""
Virt - Test configuration module
"""

__test__ = False

from rhevmtests.config import *  # flake8: noqa

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
# #################################################
# Following paramaters are virt specific paramaters
# #################################################
ADDITIONAL_DC_NAME = 'virt_additional_dc'
ADDITIONAL_CL_NAME = 'virt_additional_cl'
# Vm names
VM_RUN_ONCE = "vm_run_once"
VM_DESCRIPTION = PARAMETERS.get('vm_description', '%s_test' % TEST_NAME)

USERNAME = VDC_ADMIN_USER

VM_OS_TYPE = ENUMS[RHEL7PPC64] if PPC_ARCH else ENUMS['rhel6x64']
VM_DISPLAY_TYPE = ENUMS[
    'display_type_vnc'
] if PPC_ARCH else ENUMS['display_type_spice']
VM_TYPE = VM_TYPE_SERVER if PPC_ARCH else VM_TYPE_DESKTOP
RHEL_OS_TYPE_FOR_MIGRATION = "rhel"

# glance
RHEL_IMAGE_GLANCE_IMAGE = 'latest-rhel-guest-image-7.2'

# migration
MIGRATION_VM = VM_NAME[0] if PPC_ARCH else "migration_vm"
CONNECTIVITY_CHECK = False if PPC_ARCH else True
MIGRATION_IMAGE_VM = "vm_with_loadTool"
OS_RHEL_7 = ENUMS['rhel7x64']

# reg_vms
SPICE = ENUMS['display_type_spice']
VNC = ENUMS['display_type_vnc']

# cpu_hotplug
CPU_HOTPLUG_VM = "cpu_hotplug_vm"
VCPU_PINNING_3 = ([{str(i): str(i)} for i in range(3)])
CPU_TOPOLOGY = []
CPU_HOTPLUG_VM_PARAMS = {
    "cpu_cores": 1,
    "cpu_socket": 1,
    "placement_affinity": VM_MIGRATABLE,
    "placement_host": VM_ANY_HOST,
    "vcpu_pinning": [],
}
MIGRATING_STATUSES = [
    ENUMS["vm_state_migrating"], ENUMS["vm_state_migrating_to"],
    ENUMS["vm_state_migrating_from"]
]

FILE_NAME = 'test_file'
TEMP_PATH = '/var/tmp/'
ACTION_TIMEOUT = 30

# memory hot plug
MB_SIZE_256 = 256 * MB
MB_SIZE_400 = 400 * MB
MEMORY_HOTPLUG_VM = "memory_hotplug_test"
