"""
Config module for storage sanity tests
"""
__test__ = False

from art.test_handler.settings import opts
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

PARAMETERS = ART_CONFIG['PARAMETERS']

STORAGE = ART_CONFIG['STORAGE']

DATA_CENTER_TYPE = (PARAMETERS['data_center_type']).split("_")[0]
if DATA_CENTER_TYPE == ENUMS['storage_type_posixfs']:
    VFS_TYPE = (PARAMETERS['data_center_type']).split("_")[1]
    PARAMETERS['vfs_type'] = VFS_TYPE

EXTEND_LUN = PARAMETERS.get('extend_lun', None)

FIRST_HOST = PARAMETERS.as_list('vds')[0]

BASENAME = "%sTestStorage" % DATA_CENTER_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
VDS_PASSWORD = PARAMETERS.get('vds_password', None)

HOSTS = PARAMETERS.as_list('vds')

HOST_NONOPERATIONAL = ENUMS["search_host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]