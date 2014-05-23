from configobj import ConfigObj

global config
config = ConfigObj(raise_errors=True)

from . import ART_CONFIG

params = ART_CONFIG['PARAMETERS']
VM_NAME = params.get('vm_name')
ISO_UP_CONF = params.get('iso_up_conf_file')
LOG_COL_CONF = params.get('log_col_conf_file')
IMAGE_UP_CONF = params.get('image_up_conf_file')

rest_conn = ART_CONFIG['REST_CONNECTION']
REST_API_PASS = rest_conn.get('password')
REST_API_HOST = rest_conn.get('host')

# workaround to skip sdk for now
MAIN_SETUP = "https://lilach-rhel.qa.lab.tlv.redhat.com:443/api"
PGPASS = "123456"
HOST_PASS = "qum5net"

# image/iso uploader is using default names for iso/export domain, which are
# specified in high_level.storagedomains.create_storages
ISO_DOMAIN_NAME = 'iso_domain'
LOCAL_ISO_DOMAIN_NAME = 'ISO_DOMAIN'
EXPORT_DOMAIN_NAME = 'export_domain'
DEFAULT = {
    'def_vm_name': VM_NAME,  # name
    'wait_timeout': 2400,  # wait for VM state change. Total install: ~40min
    'install_timeout': 1800,  # wait for RHEVM installation
    '_password_host': HOST_PASS,
    '_password': REST_API_PASS,  # default password
    '_password_db': PGPASS,  # default db password
    '_organization': 'Nice Testing Org. Name',  # organization name for certs
}

SDK = {
    'address': MAIN_SETUP,
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
    'OSETUP_RPMDISTRO/enableUpgrade': 'none:None',
    'OVESETUP_CORE/engineStop': 'none:None',
    'OVESETUP_DIALOG/confirmSettings': 'bool:True',
    'OVESETUP_DB/database': 'str:engine',
    'OVESETUP_DB/secured': 'bool:False',
    'OVESETUP_DB/securedHostValidation': 'bool:False',
    'OVESETUP_DB/host': 'str:localhost',
    'OVESETUP_DB/fixDbViolations': 'none:None',
    'OVESETUP_DB/user': 'str:engine',
    'OVESETUP_DB/password': 'str:123456',
    'OVESETUP_DB/port': 'int:5432',
    'OVESETUP_SYSTEM/nfsConfigEnabled': 'bool:True',
    'OVESETUP_SYSTEM/memCheckEnabled': 'bool:False',
    'OVESETUP_RHEVM_SUPPORT/redhatSupportProxyEnabled': 'bool:False',
    'OVESETUP_PKI/organization': 'str:tlv.redhat.com',
    'OVESETUP_CONFIG/isoDomainName': 'str:ISO_DOMAIN',
    'OVESETUP_CONFIG/isoDomainMountPoint': 'str:/var/lib/exports/iso',
    'OVESETUP_CONFIG/adminPassword': 'str:123456',
    'OVESETUP_CONFIG/applicationMode': 'str:both',
    'OVESETUP_CONFIG/firewallManager': 'str:iptables',
    'OVESETUP_CONFIG/fqdn': 'str:' + REST_API_HOST,
    'OVESETUP_CONFIG/storageType': 'str:nfs',
    'OVESETUP_CONFIG/websocketProxyConfig': 'bool:True',
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
    'OVESETUP_SYSTEM/nfsConfigEnabled',
    'OVESETUP_SYSTEM/memCheckEnabled',
    'OVESETUP_RHEVM_SUPPORT/redhatSupportProxyEnabled',
    'OVESETUP_PKI/organization',
    'OVESETUP_CONFIG/isoDomainName',
    'OVESETUP_CONFIG/isoDomainMountPoint',
    'OVESETUP_CONFIG/adminPassword',
    'OVESETUP_CONFIG/applicationMode',
    'OVESETUP_CONFIG/firewallManager',
    'OVESETUP_CONFIG/fqdn',
    'OVESETUP_CONFIG/storageType',
    'OVESETUP_CONFIG/websocketProxyConfig',
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
    'OVESETUP_REMOVE/removeAll': 'bool:True',
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
    'OVESETUP_REMOVE/removeAll',
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
    'new_cleanup_ans_file': '/tmp/new_cleanup_ans_file'
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
