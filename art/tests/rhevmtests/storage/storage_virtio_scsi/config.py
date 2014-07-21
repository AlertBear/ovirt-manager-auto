
"""
Config module for virtio-scsi tests
"""

__test__ = False

import copy
from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "virtio_scsi"

# TODO: remove
ENGINE = ART_CONFIG['RUN']['engine'].lower()

# TODO: what is this used for?
STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])
STORAGE['data_domain_path'] = [PARAMETERS.as_list('data_domain_path')[0]]
STORAGE['data_domain_address'] = [PARAMETERS.as_list('data_domain_address')[0]]

ADDITIONAL_PATH = PARAMETERS.as_list('data_domain_path')[1:]

ADDITIONAL_ADDRESS = PARAMETERS.as_list('data_domain_address')[1:]

# TODO: remove
VIRTIO_SCSI = INTERFACE_VIRTIO_SCSI
VIRTIO_BLK = INTERFACE_VIRTIO

# TODO: remove
PASSWORDS = HOSTS_PW

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

# TODO: remove
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

TEMPLATE_NAME = PARAMETERS.get('template', 'virtio_scsi_template')
SNAPSHOT_NAME = PARAMETERS.get('snapshot_name', 'virtio_scsi_snapshot')

# TODO: remove
VM_NAMES = VM_NAME
