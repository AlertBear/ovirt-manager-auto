from . import ART_CONFIG
from art.test_handler.settings import opts

__test__ = False

GB = 1024 ** 3

PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

TESTNAME = PARAMETERS.get('basename', None)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

BASENAME = PARAMETERS.get('basename', None)
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)

HOSTS = PARAMETERS.as_list('vds')
HOST_USER = PARAMETERS.get('vds_user', 'root')
HOST_PASSWORD = PARAMETERS['vds_password']
HOST_NONOPERATIONAL = ENUMS['search_host_state_non_operational']
DATA_CENTER_PROBLEMATIC = ENUMS['data_center_state_problematic']

DEFAULT_SPM_PRIORITY = '5'
LOW_SPM_PRIORITY = '1'

# move all storage details to same keys from separated keys created by
# auto_devices, so all domains will be created by build_setup
## ISCSI
if STORAGE_TYPE == ENUMS['storage_type_iscsi']:
    PARAMETERS['lun'] = [PARAMETERS['lun'], PARAMETERS['another_lun']]
    PARAMETERS['lun_address'] = [PARAMETERS['lun_address'],
                                 PARAMETERS['another_lun_address']]
    PARAMETERS['lun_target'] = [PARAMETERS['lun_target'],
                                PARAMETERS['another_lun_target']]
## NFS
elif STORAGE_TYPE == ENUMS['storage_type_nfs']:
    PARAMETERS['data_domain_path'] = [PARAMETERS['data_domain_path'],
                                      PARAMETERS['another_data_domain_path']]
    PARAMETERS['data_domain_address'] = [PARAMETERS['data_domain_address'],
                                         PARAMETERS[
                                             'another_data_domain_address']]
