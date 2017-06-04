from art.test_handler.settings import ART_CONFIG, opts
ENUMS = opts['elements_conf']['RHEVM Enums']

PARAMETERS = ART_CONFIG['PARAMETERS']
DEFAULTS = ART_CONFIG['DEFAULT']
GOLDEN_ENV = ART_CONFIG['prepared_env']
ROOT_USER = PARAMETERS['vm_linux_user']
ROOT_PASSWORD = PARAMETERS['vm_linux_password']
DC = GOLDEN_ENV['dcs']
DC_NAME = DC[0]['name']
CLUSTERS = DC[0]['clusters']
CLUSTER_NAME = CLUSTERS[0]['name']
NIC_NAME = "nic1"
MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')

INITIALIZATION_PARAMS = {
    'root_password': ROOT_PASSWORD,
    'user_name': ROOT_USER
}

REPOSITORY = DEFAULTS['RHEVM_REPOSITORY']
PRODUCT = DEFAULTS['PRODUCT']

# GLANCE
GLANCE_DOMAIN = 'rhevm-qe-infra-glance'
STORAGE_TYPE = ENUMS['storage_type_nfs']
IMAGE_NAMES = DEFAULTS.as_list('GLANCE_IMAGES')
BACKUP_IMAGE = DEFAULTS.get('BACKUP_IMAGE')
GLANCE_USER = 'admin'
GLANCE_TENANT = 'admin'
GLANCE_PASSWORD = 'qum5net'
GLANCE_URL = 'http://rhevm-qe-infra-openstack.qa.lab.tlv.redhat.com:35357/v2.0'

# prefixes
TEMPLATE_PREFIX = 'updt_{0}'
DISK_PREFIX = 'updt_{0}'
VM_PREFIX = 'updt_{0}'
