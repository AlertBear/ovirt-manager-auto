"""
Config module for manage storage connections tests
"""

__test__ = False

import copy
from rhevmtests.storage.config import * # flake8: noqa


# Name of the test
TESTNAME = "manage_storage_conn"

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])

if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    CONNECTIONS = []
    CONNECTIONS.append({
        'lun_address': PARAMETERS.as_list('lun_address')[0],
        'lun_target': PARAMETERS.as_list('lun_target')[0],
        'lun_port': int(PARAMETERS.get('lun_port', 3260)),
        'luns': PARAMETERS.as_list('lun')})
    CONNECTIONS.append({
        'lun_address': PARAMETERS.as_list('another_lun_address')[0],
        'lun_target': PARAMETERS.as_list('another_lun_target')[0],
        'lun_port': int(PARAMETERS.get('another_lun_port', 3260)),
        'luns': PARAMETERS.as_list('another_lun')})

    PARAMETERS['lun'] = []
    PARAMETERS['lun_address'] = []
    PARAMETERS['lun_target'] = []
    PARAMETERS['lun_port'] = []

if STORAGE_TYPE == 'nfs' or STORAGE_TYPE.startswith('posixfs'):
    DOMAIN_ADDRESSES = PARAMETERS.as_list('data_domain_address')[1:]
    DOMAIN_PATHS = PARAMETERS.as_list('data_domain_path')[1:]
    PARAMETERS['data_domain_address'] = PARAMETERS.as_list(
        'data_domain_address')[0]
    PARAMETERS['data_domain_path'] = PARAMETERS.as_list('data_domain_path')[0]
    HOST_FOR_MNT = HOSTS[1]
    PASSWD_FOR_MNT = HOSTS_PW
