__test__ = False

from rhevmtests.system.config import *  # flake8: noqa
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']

# Common properties
FIXTURES = 'fixtures'
EXTENSIONS_DIRECTORY = '/etc/ovirt-engine/extensions.d'
EXTENSIONS_PKG = 'ovirt-engine-extension-aaa-*'
DEFAULT_CLUSTER_NAME = 'Default'
USERROLE = ENUMS['role_name_user_role']

# Extensions properties
WRONG_EXTENSION = {
    'authz_file': 'ldap-authz-test_configurations_wrong.properties',
    'authz_name': 'ldap-authz-test_configurations_wrong',
}

DISABLED_EXTENSION = {
    'authz_file': 'ldap-authz-test_configurations_disabled.properties',
    'authz_name': 'ldap-authz-test_configurations_disabled',
}

ADSSL_EXTENSION = {
    'authz_file': 'ldap-authz-test_ssl_ssl.properties',
    'authz_name': 'ldap-authz-test_ssl',
    'authn_name': 'ldap-authn-test_ssl',
}

ADTLS_EXTENSION = {
    'authz_file': 'ldap-authz-test_ssl_tls.properties',
    'authz_name': 'ldap-authz-test_tls',
    'authn_name': 'ldap-authn-test_tls',
}

# ADW2K12 properties
ADW2K12_DOMAINS = ['ad-w2k12r2.rhev.lab.eng.brq.redhat.com',
                   'ad-w2k12r2p.rhev.lab.eng.brq.redhat.com',
                   'ad-w2k12r2pc.ad-w2k12r2p.rhev.lab.eng.brq.redhat.com',
                   'ad-w2k12r2lc.ad-w2k12r2.rhev.lab.eng.brq.redhat.com']
ADW2k12_USER_PASSWORD = 'Heslo123'
ADW2k12_USER1 = 'user1'
