"""
Config module for storage sanity tests
"""
__test__ = False

from art.test_handler.settings import ART_CONFIG, opts

GB = 1024 ** 3

ENUMS = opts['elements_conf']['RHEVM Enums']

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

if STORAGE_TYPE == ENUMS['storage_type_posixfs']:
    VFS_TYPE = (PARAMETERS['data_center_type']).split("_")[1]
    PARAMETERS['vfs_type'] = VFS_TYPE


BASENAME = "%sTestStorage" % STORAGE_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)


DC_VERSIONS = PARAMETERS.as_list('dc_versions')
DC_TYPE = PARAMETERS['data_center_type']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
SETUP_ADDRESS = ART_CONFIG['REST_CONNECTION']['host']

HOSTS = PARAMETERS.as_list('vds')
VDS_PASSWORD = PARAMETERS.as_list('vds_password')
VDS_USER = PARAMETERS.as_list('vds_admin')
FIRST_HOST = HOSTS[0]
HOST_NONOPERATIONAL = ENUMS["host_state_non_operational"]
HOST_UP = ENUMS['search_host_state_up']

TYPE_DATA = ENUMS['storage_dom_type_data']

STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']

if STORAGE_TYPE == STORAGE_TYPE_NFS:
    ADDRESS = PARAMETERS.as_list('data_domain_address')
    PATH = PARAMETERS.as_list('data_domain_path')
elif STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    LUNS = PARAMETERS.as_list('lun')
    LUN_ADDRESS = PARAMETERS.as_list('lun_address')
    LUN_TARGET = PARAMETERS.as_list('lun_target')
    LUN_PORT = 3260
