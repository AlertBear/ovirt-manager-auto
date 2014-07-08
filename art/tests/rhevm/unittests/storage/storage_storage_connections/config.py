"""
Config module for manage storage connections tests
"""

__test__ = False

import copy

from art.rhevm_api.utils import test_utils
from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG


# Name of the test
TESTNAME = "manage_storage_conn"

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

BASENAME = PARAMETERS.get('basename', 'storageConn')
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', "cluster_%s" % BASENAME)

ENUMS = opts['elements_conf']['RHEVM Enums']

HOSTS = PARAMETERS.as_list('vds')

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])

PASSWORDS = PARAMETERS.as_list('vds_password')

if STORAGE_TYPE == 'iscsi':
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
    PASSWD_FOR_MNT = PASSWORDS[1]

MAX_WORKERS = PARAMETERS.get('max_workers', 10)
HOST_NICS = PARAMETERS.as_list('host_nics')
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']

COBBLER_PROFILE = PARAMETERS['cobbler_profile']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
INTERFACE_VIRTIO = ENUMS['interface_virtio']

VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
DISK_SIZE = int(PARAMETERS.setdefault('disk_size', 10737418240))

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

CPU_SOCKET = PARAMETERS.get('cpu_socket', 2)
CPU_CORES = PARAMETERS.get('cpu_cores', 2)
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

STORAGE_TYPE = (PARAMETERS['storage_type']).split("_")[0]
if STORAGE_TYPE == ENUMS['storage_type_posixfs']:
    VFS_TYPE = (PARAMETERS['data_center_type']).split("_")[1]
    PARAMETERS['vfs_type'] = VFS_TYPE
