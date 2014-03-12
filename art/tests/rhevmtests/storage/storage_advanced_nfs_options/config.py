"""
Config module for advanced nfs options tests
"""

__test__ = False

import copy

from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG


# Name of the test
TESTNAME = "advanced_nfs_options"

ENGINE = ART_CONFIG['RUN']['engine'].lower()

PARAMETERS = ART_CONFIG['PARAMETERS']

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])
STORAGE['data_domain_path'] = [PARAMETERS.as_list('data_domain_path')[0]]
STORAGE['data_domain_address'] = [PARAMETERS.as_list('data_domain_address')[0]]

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Enums
ENUMS = opts['elements_conf']['RHEVM Enums']

BASENAME = PARAMETERS.get('basename', 'nfsOptions')

DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)

NFS_PATH = PARAMETERS.as_list('data_domain_path')[1:]

NFS_ADDRESS = PARAMETERS.as_list('data_domain_address')[1:]

HOSTS = PARAMETERS.as_list('vds')

PASSWORDS = PARAMETERS.as_list('vds_password')

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']

CPU_NAME = PARAMETERS['cpu_name']

HOST_FOR_30_DC = HOSTS[-1]

DISK_SIZE = int(PARAMETERS['disk_size'])

CLUSTER_NAME = PARAMETERS['cluster_name']

VDC = PARAMETERS.get('host', None)

VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
