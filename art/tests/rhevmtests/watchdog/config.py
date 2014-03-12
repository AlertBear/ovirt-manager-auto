"""
SLA test config module
"""
from art.test_handler.settings import ART_CONFIG

TEST_NAME = "Watchdog"
PARAMETERS = ART_CONFIG['PARAMETERS']
COBBLER = ART_CONFIG['PROVISIONING_TOOLS']['COBBLER']
PROVISIONING_PROFILE = ART_CONFIG['PROVISIONING_PROFILES']['rhel6.4-agent3.3']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

ENGINE = PARAMETERS.get('engine')
ENGINE_USER = PARAMETERS.get('engine_user', 'root')
ENGINE_PASSWD = PARAMETERS.get('engine_passwd', '123456')
BASENAME = PARAMETERS.get('test_name', TEST_NAME)
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)
CPU_NAME = PARAMETERS['cpu_name']
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')
VDS_ADMIN = PARAMETERS.as_list('vds_admin')
NIC = PARAMETERS.get('nic', 'nic1')

ACTIVATION_KEY = PARAMETERS.get('activation_key')
REGISTER_URL = PARAMETERS.get('server_url')
VM_USER = PARAMETERS.get('vm_user', 'root')
VM_PASSWD = PARAMETERS.get('vm_passwd', '123456')

VM_NAME = PARAMETERS.get('vm_wd_name', 'watchdog_vm')
WATCHDOG_MODEL = PARAMETERS.get('watchdog_model')

COBBLER_ADDRESS = COBBLER.get('api')
COBBLER_PROFILE = PROVISIONING_PROFILE['COBBLER'].get('profile')
COBBLER_PASSWDd = COBBLER.get('password')
COBBLER_USER = COBBLER.get('user')
