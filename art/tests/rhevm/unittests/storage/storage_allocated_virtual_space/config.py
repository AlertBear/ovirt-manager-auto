from . import ART_CONFIG
from art.test_handler.settings import opts

__test__ = False

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Name of the test
BASENAME = PARAMETERS['basename']

ENUMS = opts['elements_conf']['RHEVM Enums']

VIRTIO_DISK = ENUMS['interface_virtio']
COW_DISK = ENUMS['format_cow']
RAW_DISK = ENUMS['format_raw']
SNAPSHOT_OK = ENUMS['snapshot_state_ok']
ISCSI_DOMAIN = ENUMS['storage_type_iscsi']
SD_ACTIVE = ENUMS['storage_domain_state_active']
DISK_LOCKED = ENUMS['disk_state_locked']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
VDS_PASSWORDS = PARAMETERS.as_list('vds_password')

DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)

HOSTS = PARAMETERS.as_list('vds')

VM_DISK_SIZE = int(PARAMETERS['vm_disk_size'])

STORAGE_SECTION = ART_CONFIG['STORAGE']
if STORAGE_TYPE == ISCSI_DOMAIN:
    EXTEND_LUN = STORAGE_SECTION['PARAMETERS.extend_lun']

    # Size of device (in GB)
    EXTEND_SIZE = int(EXTEND_LUN['devices_capacity'])
