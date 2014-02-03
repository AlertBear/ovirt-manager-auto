"""
MOM test config module
"""
from . import ART_CONFIG

TEST_NAME = "MOM"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

BASENAME = PARAMETERS.get('test_name', TEST_NAME)
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]

DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')
VDS_ADMIN = PARAMETERS.as_list('vds_admin')

VM_USER = PARAMETERS.get('vm_user', 'root')
VM_PASSWD = PARAMETERS.get('vm_passwd', '123456')

NIC = PARAMETERS.get('nic', 'nic1')

EXPORT_DOMAIN = PARAMETERS.get('export_domain', None)
EXPORT_ADDRESS = PARAMETERS.get('export_address', None)
EXPORT_PATH = PARAMETERS.get('export_path', None)

KSM_VM_NUM = PARAMETERS.get('ksm_vm_num', 8)
BALLOON_VM_NUM = PARAMETERS.get('balloon_vm_num', 8)

RHEL = PARAMETERS.get('rhel', None)
W7 = PARAMETERS.get('w7', None)
W2K = PARAMETERS.get('w2k', None)
