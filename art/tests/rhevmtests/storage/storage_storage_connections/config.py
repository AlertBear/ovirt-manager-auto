"""
Config module for manage storage connections tests
"""

__test__ = False

import copy
from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "manage_storage_conn"

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])

CONNECTIONS = []
if GOLDEN_ENV:
    CONNECTIONS.append({
        'lun_address': '',
        'lun_target':  '',
        'lun_port': LUN_PORT,
        'luns': UNUSED_LUNS,
    })
    CONNECTIONS.append({
        'lun_address': '',
        'lun_target':  '',
        'lun_port': LUN_PORT,
        'luns': UNUSED_LUNS,
    })
    # After each test, we logout from all the targets by looping through
    # CONNECTIONS. Add the default target/ip so the host will also logout
    # from it
    CONNECTIONS.append({
        'lun_address': UNUSED_LUN_ADDRESSES[0],
        'lun_target':  UNUSED_LUN_TARGETS[0],
    })

    DOMAIN_ADDRESSES = UNUSED_DATA_DOMAIN_ADDRESSES[0:1]
    DOMAIN_PATHS = UNUSED_DATA_DOMAIN_PATHS[0:1]
    EXTRA_DOMAIN_ADDRESSES = UNUSED_DATA_DOMAIN_ADDRESSES[1:]
    EXTRA_DOMAIN_PATHS = UNUSED_DATA_DOMAIN_PATHS[1:]
else:
    if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
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

    if STORAGE_TYPE == STORAGE_TYPE_NFS or STORAGE_TYPE.startswith('posixfs'):
        DOMAIN_ADDRESSES = PARAMETERS.as_list('data_domain_address')[1:]
        DOMAIN_PATHS = PARAMETERS.as_list('data_domain_path')[1:]
        PARAMETERS['data_domain_address'] = PARAMETERS.as_list(
            'data_domain_address')[0]
        PARAMETERS['data_domain_path'] = PARAMETERS.as_list(
            'data_domain_path')[0]
        EXTRA_DOMAIN_ADDRESSES = PARAMETERS.as_list('another_address')
        EXTRA_DOMAIN_PATHS = PARAMETERS.as_list('another_path')

# A host will be use to copy data between domains and clean them
# afterwards. This hosts needs to be removed from the data center
HOST_FOR_MOUNT = None  # Filled in setup_package
HOST_FOR_MOUNT_IP = None  # Filled in setup_package
HOSTS_FOR_TEST = None  # Filled in setup_package

DATACENTER_ISCSI_CONNECTIONS = "dc_iscsi_{0}".format(TESTNAME)
CLUSTER_ISCSI_CONNECTIONS = "cl_iscsi_{0}".format(TESTNAME)
