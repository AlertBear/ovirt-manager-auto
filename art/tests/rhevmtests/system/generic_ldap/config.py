__test__ = False

from rhevmtests.system.config import *  # flake8: noqa

FIXTURES = 'fixtures'
EXTENSIONS_DIRECTORY = '/etc/ovirt-engine/extensions.d'
EXTENSIONS_PKG = 'ovirt-engine-extension-aaa-*'

# test_configurations module
WRONG_EXTENSION = {
    'authz_file': 'ldap-authz-test_configurations_wrong.properties',
    'authn_file': 'ldap-authn-test_configurations_wrong.properties',
    'authz_name': 'ldap-authz-test_configurations_wrong',
    'authn_name': 'ldap-authn-test_configurations_wrong',
    'auth_name': 'ldap-auth-test_configurations_wrong',
}

DISABLED_EXTENSION = {
    'authz_file': 'ldap-authz-test_configurations_disabled.properties',
    'authn_file': 'ldap-authn-test_configurations_disabled.properties',
    'authz_name': 'ldap-authz-test_configurations_disabled',
    'authn_name': 'ldap-authn-test_configurations_disabled',
    'auth_name': 'ldap-auth-test_configurations_disabled',
}
