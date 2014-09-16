__test__ = False

import logging

from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG

LOGGER = logging.getLogger(__name__)


TEST_NAME = "UpgradeSanity"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
VARS = opts['elements_conf']['RHEVM Utilities']
STORAGE_TYPE = PARAMETERS['storage_type']

basename = 'upgradeTest'
DC_NAME = 'datacenter_upgradeTest'
CLUSTER_NAME = 'cluster_name_upgradeTest'
CPU_NAME = PARAMETERS['cpu_name']
DATA_NAME = PARAMETERS.get('data_domain_name', '%s_storage' % basename)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
PGPASS = '123456'
NIC_NAME = 'nic0'
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
TIMEOUT = 7200
SD_SUFFIX = '_sd'
SETUP_PACKAGE = 'rhevm-setup'
STORAGE_NAME = DC_NAME + SD_SUFFIX + "0"
VM_NAME = ''.join([PARAMETERS.get('basename', ''), 'Vm'])


REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
RHEVM_NAME = REST_CONNECTION['host']
MB = 1024 * 1024
GB = 1024 * MB
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

VM_LINUX_USER = PARAMETERS.get('vm_linux_user', 'root')
VM_LINUX_PASSWORD = PARAMETERS.get('vm_linux_password', 'qum5net')


ANSWERS = {
    # KEYWORDS FOR OTOPI ANSWERFILE
    'OSETUP_RPMDISTRO/enableUpgrade': 'bool:True',
    'OSETUP_RPMDISTRO/requireRollback': 'bool:False',
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
    'OVESETUP_SYSTEM/nfsConfigEnabled': 'bool:True',
    'OVESETUP_SYSTEM/memCheckEnabled': 'bool:False',
    'OVESETUP_RHEVM_SUPPORT/redhatSupportProxyEnabled': 'bool:False',
    'OVESETUP_PKI/organization': 'str:tlv.redhat.com',
    'OVESETUP_CONFIG/isoDomainName': 'str:ISO_DOMAIN',
    'OVESETUP_CONFIG/isoDomainMountPoint': 'str:/var/lib/exports/iso',
    'OVESETUP_CONFIG/adminPassword': 'str:123456',
    'OVESETUP_CONFIG/applicationMode': 'str:both',
    'OVESETUP_CONFIG/firewallManager': 'str:iptables',
    'OVESETUP_CONFIG/fqdn': 'str:' + VDC,
    'OVESETUP_CONFIG/storageType': 'str:nfs',
    'OVESETUP_CONFIG/websocketProxyConfig': 'bool:True',
    'OVESETUP_CONFIG/updateFirewall': 'bool:True',
    'OVESETUP_PROVISIONING/postgresProvisioningEnabled': 'bool:False',
    'OVESETUP_APACHE/configureRootRedirection': 'bool:True',
    'OVESETUP_APACHE/configureSsl': 'bool:True',
    'OVESETUP_AIO/configure': 'none:None',
    'OVESETUP_AIO/storageDomainDir': 'none:None',
    'OVESETUP_CONFIG/isoDomainACL': 'str:0.0.0.0/0.0.0.0(rw)',
    'OVESETUP_DIALOG/confirmSettings': 'bool:True',
    'OVESETUP_RHEVM_DIALOG/confirmUpgrade': 'bool:False'
}

ANSWERS['__default__'] = (
    'OSETUP_RPMDISTRO/enableUpgrade',
    'OSETUP_RPMDISTRO/requireRollback',
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
    'OVESETUP_CONFIG/isoDomainACL',
    'OVESETUP_DIALOG/confirmSettings',
    'OVESETUP_RHEVM_DIALOG/confirmUpgrade'
)
