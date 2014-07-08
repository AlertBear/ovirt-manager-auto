"""
Config module for storage sanity tests
"""
__test__ = False

from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

STORAGE = ART_CONFIG['STORAGE']

if STORAGE_TYPE.split("_")[0] == ENUMS['storage_type_posixfs']:
    STORAGE_TYPE, VFS_TYPE = (PARAMETERS['storage_type']).split("_")
    PARAMETERS['vfs_type'] = VFS_TYPE

if PARAMETERS.get('extend_lun', None):
    EXTEND_LUN = {
        "lun_targets": PARAMETERS.as_list("extend_lun_target"),
        "lun_addresses": PARAMETERS.as_list("extend_lun_address"),
        "lun_list": PARAMETERS.as_list("extend_lun"),
    }
else:
    EXTEND_LUN = None

FIRST_HOST = PARAMETERS.as_list('vds')[0]

BASENAME = "%sTestStorage" % STORAGE_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
CLUSTER_NAME = 'cluster_%s' % BASENAME

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
VDS_PASSWORD = PARAMETERS.get('vds_password', None)

HOSTS = PARAMETERS.as_list('vds')

HOST_NONOPERATIONAL = ENUMS["search_host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']

LOCAL = True if STORAGE_TYPE == ENUMS['storage_type_local'] else False
