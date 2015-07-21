"""
Virt - Test configuration module
"""

__test__ = False

from rhevmtests.config import *  # flake8: noqa

# #######################################################################
# Following parameters should move to consolidated config, once possible
# #######################################################################

# ISO storage domain
SHARED_ISO_DOMAIN_ADDRESS = ISO_DOMAIN_ADDRESS
SHARED_ISO_DOMAIN_PATH = ISO_DOMAIN_PATH
SHARED_ISO_DOMAIN_NAME = ISO_DOMAIN_NAME
# Run once parameters
CDROM_IMAGE_1 = 'en_windows_7_enterprise_x86_dvd_x15-70745.iso'
CDROM_IMAGE_2 = 'en_windows_7_enterprise_x64.iso'
FLOPPY_IMAGE = 'win2k3.vfd'

# Storage names
storage_name = PARAMETERS.get('storage_name', '%s_%d' % (STORAGE_TYPE, 0))
nfs_storage_0 = PARAMETERS.get('storage_name_0', '%s_0' % STORAGE_TYPE)
nfs_storage_1 = PARAMETERS.get('storage_name_1', '%s_1' % STORAGE_TYPE)
export_storage = PARAMETERS.get('export_storage', EXPORT_STORAGE_NAME)
# #################################################
# Following paramaters are virt specific paramaters
# #################################################
ADDITIONAL_DC_NAME = 'virt_additional_dc'
ADDITIONAL_CL_NAME = 'virt_additional_cl'
# Vm names
VM_RUN_ONCE ="run_once"
VM_NAME_BASIC = 'golden_env_mixed_virtio'
VM_DESCRIPTION = PARAMETERS.get('vm_description', '%s_test' % TEST_NAME)

USERNAME = VDC_ADMIN_USER

MIGRATION_TEMPLATE_NAME = "vm_migration_template"
MIGRATION_BASE_VM = "base_vm_migration_test"
RHEL_IMAGE = "rhel6.5-agent3.5"
