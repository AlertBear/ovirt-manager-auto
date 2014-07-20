"""
Virt - Test configuration module
"""

__test__ = False

from rhevmtests.config import *  # flake8: noqa

# #######################################################################
# Following parameters should move to consolidated config, once possible
# #######################################################################

# ISO storage domain
SHARED_ISO_DOMAIN_ADDRESS = PARAMETERS.get('shared_iso_domain_address')
SHARED_ISO_DOMAIN_PATH = PARAMETERS.get('shared_iso_domain_path')
SHARED_ISO_DOMAIN_NAME = PARAMETERS.get('shared_iso_domain_name')
# Run once parameters
CDROM_IMAGE_1 = PARAMETERS.get('cdrom_image_1')
CDROM_IMAGE_2 = PARAMETERS.get('cdrom_image_2')
FLOPPY_IMAGE = PARAMETERS.get('floppy_image')

# Datacenter names
dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % TEST_NAME)
second_dc_name = PARAMETERS.get('second_dc_name', 'second_datacenter_%s'
                                                  % TEST_NAME)
# Cluster names
cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % TEST_NAME)
additional_cluster_names = ['%s_%d' %
                            (cluster_name, i) for i in range(2)]
# Storage names
storage_name = PARAMETERS.get('storage_name', '%s_%d' % (STORAGE_TYPE, 0))
nfs_storage_0 = PARAMETERS.get('storage_name_0', '%s_0' % STORAGE_TYPE)
nfs_storage_1 = PARAMETERS.get('storage_name_1', '%s_1' % STORAGE_TYPE)
export_storage = PARAMETERS.get('export_storage', 'export_domain')
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
STORAGE_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
                range(len(DATA_PATHS))]

# #################################################
# Following paramaters are virt specific paramaters
# #################################################


# Vm names
VM_NAME_BASIC = '%s_vm' % (TEST_NAME)
VM_NAMES = ['%s-%d' % (VM_NAME_BASIC, i) for i in range(15)]
VM_DESCRIPTION = PARAMETERS.get('vm_description', '%s_test' % TEST_NAME)

USERNAME = PARAMETERS.get('username')
