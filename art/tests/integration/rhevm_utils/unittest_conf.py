
import logging

from configobj import ConfigObj

from art.test_handler.settings import ART_CONFIG, opts
from art.rhevm_api import resources

__test__ = False

logger = logging.getLogger(__name__)


def get_list(params, key):
    """
    Get element from configuration section as list

    :param params: configuration section
    :type params: ConfigObj section
    :param key: element to get
    :type key: str
    :return: return element of configuration section as list
    :rtype: list
    """
    return params.as_list(key) if key in params else []


global config
config = ConfigObj(raise_errors=True)

# RHEVM related constants
ENUMS = opts['elements_conf']['RHEVM Enums']
PERMITS = opts['elements_conf']['RHEVM Permits']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']

TEST_NAME = "Global"

PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
ISO_UP_CONF = PARAMETERS.get('iso_up_conf_file',
                             '/etc/ovirt-engine/isouploader.conf')
LOG_COL_CONF = PARAMETERS.get('log_col_conf_file',
                              '/etc/ovirt-engine/logcollector.conf')
IMAGE_UP_CONF = PARAMETERS.get('image_up_conf_file',
                               '/etc/ovirt-engine/imageuploader.conf')

NEW_CLUSTER_NAME = PARAMETERS.get('new_cluster_name',
                                  'golden_setup_new_cluster')
NEW_DC_NAME = PARAMETERS.get('new_datacenter_name', 'golden_setup_new_dc')
VM_NAME = ''.join([PARAMETERS.get('basename', TEST_NAME), 'Vm'])

ISO_DOMAIN_NAME = 'iso_domain'
LOCAL_ISO_DOMAIN_NAME = 'ISO_DOMAIN'
EXPORT_DOMAIN_NAME = 'export_domain'

LOGDIR = 'logdir'
OUTPUT_DIR = opts.get(LOGDIR, None)

CONFIG_ELEMENTS = 'elements_conf'
CONFIG_SECTION = 'RHEVM Utilities'
VARS = opts[CONFIG_ELEMENTS][CONFIG_SECTION]

HOSTS = PARAMETERS.as_list('vds')
HOSTS_IP = list(HOSTS)
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
VDS_HOSTS = [
    resources.VDS(
        h, HOSTS_PW,
    ) for h in HOSTS_IP
]

GOLDEN_ENV = ART_CONFIG.get('prepared_env', False)
CPU_NAME = PARAMETERS['cpu_name']
DC_NAME = PARAMETERS.get('dc_name', 'Global_DC_1')
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'Global_Cluster_1')
COMP_VERSION = PARAMETERS.get('compatibility_version')

# ENGINE SECTION
VDC_HOST = REST_CONNECTION['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
VDC_ROOT_USER = "root"
VDC_PASSWORD = REST_CONNECTION['password']
VDC_PORT = REST_CONNECTION['port']
VDC_ADMIN_USER = REST_CONNECTION['user']
VDC_ADMIN_DOMAIN = REST_CONNECTION['user_domain']
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']
ENGINE_URL = '%s://%s:%s/%s' % (
    REST_CONNECTION.get('scheme'),
    VDC_HOST,
    VDC_PORT,
    ENGINE_ENTRY_POINT
)
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
ENGINE_EXTENSIONS_DIR = '/etc/ovirt-engine/extensions.d'
VDSM_LOG = '/var/log/vdsm/vdsm.log'
PGPASS = "123456"

# STORAGE SECTION
STORAGE_TYPE = PARAMETERS.get('storage_types', 'nfs')

STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']
STORAGE_TYPE_FCP = ENUMS['storage_type_fcp']
STORAGE_TYPE_LOCAL = ENUMS['storage_type_local']
STORAGE_TYPE_POSIX = ENUMS['storage_type_posixfs']
STORAGE_TYPE_GLANCE = ENUMS['storage_type_glance']
STORAGE_TYPE_GLUSTER = ENUMS['storage_type_gluster']

if STORAGE_TYPE is None:
    LOCAL = PARAMETERS.get('local', None)
else:
    LOCAL = (STORAGE_TYPE == STORAGE_TYPE_LOCAL)

LUN_PORT = 3260

DEFAULT = {
    'def_vm_name': VM_NAME[0],  # name
    'wait_timeout': 2400,  # wait for VM state change. Total install: ~40min
    'install_timeout': 1800,  # wait for RHEVM installation
    '_password_host': "qum5net",
    '_password': VDC_PASSWORD,  # default password
    '_password_db': "123456",  # default db password
    '_organization': 'Nice Testing Org. Name',  # organization name for certs
}

SDK = {
    'address': "https://lilach-rhel.qa.lab.tlv.redhat.com:443/api",
    'user': "vdcadmin@rhev.lab.eng.brq.redhat.com",
    'password': '%(_password)s'
}

TESTING_ENV = {
    'password': '%(_password)s',
    'host_pass': '%(_password_host)s',
    'repo': '...',
    'user': 'admin',
    'db_pass': '%(_password_db)s',
    'organization': '%(_organization)s',
}

ANSWERS = {
    # KEYWORDS FOR OTOPI ANSWERFILE
    'OSETUP_RPMDISTRO/enableUpgrade': 'bool:False',
    'OVESETUP_CORE/engineStop': 'bool:True',
    'OVESETUP_DIALOG/confirmSettings': 'bool:True',
    'OVESETUP_DB/database': 'str:engine',
    'OVESETUP_DB/secured': 'bool:False',
    'OVESETUP_DB/securedHostValidation': 'bool:False',
    'OVESETUP_DB/host': 'str:localhost',
    'OVESETUP_DB/fixDbViolations': 'none:None',
    'OVESETUP_DB/user': 'str:engine',
    'OVESETUP_DB/password': 'str:123456',
    'OVESETUP_DB/port': 'int:5432',
    'OVESETUP_ENGINE_CORE/enable': 'bool:True',
    'OVESETUP_ENGINE_CONFIG/fqdn': 'str:' + VDC_HOST,
    'OVESETUP_SYSTEM/nfsConfigEnabled': 'bool:True',
    'OVESETUP_SYSTEM/memCheckEnabled': 'bool:False',
    'OVESETUP_RHEVM_SUPPORT/redhatSupportProxyEnabled': 'bool:False',
    'OVESETUP_PKI/organization': 'str:tlv.redhat.com',
    'OVESETUP_CONFIG/isoDomainName': 'str:ISO_DOMAIN',
    'OVESETUP_CONFIG/isoDomainMountPoint': 'str:/var/lib/exports/iso',
    'OVESETUP_CONFIG/sanWipeAfterDelete': 'bool:False',
    'OVESETUP_CONFIG/adminPassword': 'str:123456',
    'OVESETUP_CONFIG/applicationMode': 'str:both',
    'OVESETUP_CONFIG/firewallManager': 'str:iptables',
    'OVESETUP_CONFIG/firewallChangesReview': 'bool:False',
    'OVESETUP_CONFIG/fqdn': 'str:' + VDC_HOST,
    'OVESETUP_CONFIG/storageType': 'str:nfs',
    'OVESETUP_CONFIG/websocketProxyConfig': 'bool:False',
    'OVESETUP_VMCONSOLE_PROXY_CONFIG/vmconsoleProxyConfig': 'bool:False',
    'OVESETUP_CONFIG/updateFirewall': 'bool:True',
    'OVESETUP_PROVISIONING/postgresProvisioningEnabled': 'bool:False',
    'OVESETUP_APACHE/configureRootRedirection': 'bool:True',
    'OVESETUP_APACHE/configureSsl': 'bool:True',
    'OVESETUP_AIO/configure': 'none:None',
    'OVESETUP_AIO/storageDomainDir': 'none:None',
    'OVESETUP_CONFIG/isoDomainACL': 'str:0.0.0.0/0.0.0.0(rw)'
}

ANSWERS['__default__'] = (
    'OSETUP_RPMDISTRO/enableUpgrade',
    'OVESETUP_CORE/engineStop',
    'OVESETUP_DIALOG/confirmSettings',
    'OVESETUP_DB/database',
    'OVESETUP_DB/secured',
    'OVESETUP_DB/securedHostValidation',
    'OVESETUP_DB/host',
    'OVESETUP_DB/user',
    'OVESETUP_DB/password',
    'OVESETUP_DB/port',
    'OVESETUP_DB/fixDbViolations',
    'OVESETUP_ENGINE_CORE/enable',
    'OVESETUP_SYSTEM/nfsConfigEnabled',
    'OVESETUP_SYSTEM/memCheckEnabled',
    'OVESETUP_RHEVM_SUPPORT/redhatSupportProxyEnabled',
    'OVESETUP_PKI/organization',
    'OVESETUP_CONFIG/isoDomainName',
    'OVESETUP_CONFIG/isoDomainMountPoint',
    'OVESETUP_CONFIG/sanWipeAfterDelete',
    'OVESETUP_CONFIG/adminPassword',
    'OVESETUP_CONFIG/applicationMode',
    'OVESETUP_CONFIG/firewallManager',
    'OVESETUP_CONFIG/firewallChangesReview',
    'OVESETUP_ENGINE_CONFIG/fqdn',
    'OVESETUP_CONFIG/fqdn',
    'OVESETUP_CONFIG/storageType',
    'OVESETUP_CONFIG/websocketProxyConfig',
    'OVESETUP_VMCONSOLE_PROXY_CONFIG/vmconsoleProxyConfig',
    'OVESETUP_CONFIG/updateFirewall',
    'OVESETUP_PROVISIONING/postgresProvisioningEnabled',
    'OVESETUP_APACHE/configureRootRedirection',
    'OVESETUP_APACHE/configureSsl',
    'OVESETUP_AIO/configure',
    'OVESETUP_AIO/storageDomainDir',
    'OVESETUP_CONFIG/isoDomainACL'
)

CLEANUP_ANSWERS = {
    # DEFAULT ANSWERS FOR ANSWERFILE - OTOPI
    'OVESETUP_CORE/engineStop': 'bool:True',
    'OVESETUP_CORE/remove': 'bool:True',
    'OVESETUP_CORE/uninstallEnabledFileGroups': 'str:exportfs,ca_pki,'
                                                'iso_domain,versionlock,'
                                                'iso_images,ca_config',
    'OVESETUP_CORE/confirmUninstallGroups': 'bool:False',
    'OVESETUP_DB/database': 'str:engine',
    'OVESETUP_DB/secured': 'bool:False',
    'OVESETUP_DB/host': 'str:localhost',
    'OVESETUP_DB/user': 'str:engine',
    'OVESETUP_DB/securedHostValidation': 'bool:False',
    'OVESETUP_DB/password': 'str:123456',
    'OVESETUP_DB/cleanupRemove': 'bool:True',
    'OVESETUP_DB/port': 'str:5432',
    'OVESETUP_ENGINE_CORE/enable': 'bool:False',
    'OVESETUP_REMOVE/removeAll': 'bool:True',
    'OVESETUP_REMOVE/confirmUninstallGroups': 'bool:True',
    'OVESETUP_REMOVE/engineDatabase': 'bool:True',
    'OVESETUP_REMOVE/removeEngine': 'bool:True',
    'OVESETUP_REMOVE/removeOptions': 'multi-str:'
}

CLEANUP_ANSWERS['__default__'] = (
    'OVESETUP_CORE/engineStop',
    'OVESETUP_CORE/remove',
    'OVESETUP_CORE/uninstallEnabledFileGroups',
    'OVESETUP_CORE/confirmUninstallGroups',
    'OVESETUP_DB/database',
    'OVESETUP_DB/secured',
    'OVESETUP_DB/host',
    'OVESETUP_DB/user',
    'OVESETUP_DB/securedHostValidation',
    'OVESETUP_DB/password',
    'OVESETUP_DB/cleanupRemove',
    'OVESETUP_DB/port',
    'OVESETUP_ENGINE_CORE/enable',
    'OVESETUP_REMOVE/removeAll',
    'OVESETUP_REMOVE/confirmUninstallGroups',
    'OVESETUP_REMOVE/engineDatabase',
    'OVESETUP_REMOVE/removeEngine',
    'OVESETUP_REMOVE/removeOptions'
)

SETUP = {
    'vm_name': '%(def_vm_name)s',
    'answer_file': '/tmp/answer_file',
    'new_ans_file': '/tmp/new_ans_file',
    'organization': '%(_organization)s',
    'db_pass': '123456',
}

CLEANUP = {
    'vm_name': '%(def_vm_name)s',
    'cleanup_answer_file': '/tmp/cleanup_answer_file',
    'new_cleanup_ans_file': '/tmp/new_cleanup_ans_file',
    'cleanup_log_file': '/tmp/cleanup_log_file.log',
}

CONFIG = {
    'vm_name': '%(def_vm_name)s',
}

MANAGE_DOMAINS = {
    'vm_name': '%(def_vm_name)s',
}

ISO_UPLOADER = {
    'vm_name': '%(def_vm_name)s',
}

LOG_COLLECTOR = {
    'vm_name': '%(def_vm_name)s',
}

IMAGE_UPLOADER = {
    'vm_name': '%(def_vm_name)s',
}
UPGRADE = {
    'vm_name': '%(def_vm_name)s',
}

config.update(DEFAULT)
config['SDK'] = SDK
config['testing_env'] = TESTING_ENV
config['ANSWERS'] = ANSWERS
config['setup'] = SETUP
config['cleanup'] = CLEANUP
config['config'] = CONFIG
config['manage_domains'] = MANAGE_DOMAINS
config['iso-uploader'] = ISO_UPLOADER
config['log_collector'] = LOG_COLLECTOR
config['image-uploader'] = IMAGE_UPLOADER
config['upgrade'] = UPGRADE
config['CLEANUP_ANSWERS'] = CLEANUP_ANSWERS
