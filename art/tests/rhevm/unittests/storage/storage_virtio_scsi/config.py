
"""
Config module for virtio-scsi tests
"""

__test__ = False

import copy
from art.test_handler.settings import opts
from . import ART_CONFIG

GB = 1024 ** 3

# Name of the test
TESTNAME = "virtio_scsi"

ENGINE = ART_CONFIG['RUN']['engine'].lower()

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])
STORAGE['data_domain_path'] = [PARAMETERS.as_list('data_domain_path')[0]]
STORAGE['data_domain_address'] = [PARAMETERS.as_list('data_domain_address')[0]]

# Enums
ENUMS = opts['elements_conf']['RHEVM Enums']

VIRTIO_SCSI = ENUMS['interface_virtio_scsi']
VIRTIO_BLK = ENUMS['interface_virtio']

BASENAME = PARAMETERS.get('basename', '')

DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)

ADDITIONAL_PATH = PARAMETERS.as_list('data_domain_path')[1:]

ADDITIONAL_ADDRESS = PARAMETERS.as_list('data_domain_address')[1:]

HOSTS = PARAMETERS.as_list('vds')

PASSWORDS = PARAMETERS.as_list('vds_password')

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']

CPU_NAME = PARAMETERS['cpu_name']

DISK_SIZE = PARAMETERS.as_int('disk_size') * GB

CLUSTER_NAME = PARAMETERS['cluster_name']

VDC = PARAMETERS.get('host', None)

VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

VM_NAMES = PARAMETERS.as_list('vm_names')

VM_USER = PARAMETERS.get('vm_user', 'root')

VM_PASSWORD = PARAMETERS.get('vm_linux_password')

TEMPLATE_NAME = PARAMETERS.get('template', 'virtio_scsi_template')

SNAPSHOT_NAME = PARAMETERS.get('snapshot_name', 'virtio_scsi_snapshot')

MAX_WORKERS = PARAMETERS.get('max_workers', 10)

# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']
