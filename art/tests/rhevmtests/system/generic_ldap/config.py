__test__ = False

from rhevmtests.system.config import *  # flake8: noqa
from art.test_handler.settings import opts
from art.rhevm_api import resources

ENUMS = opts['elements_conf']['RHEVM Enums']

# Common properties
FIXTURES = 'fixtures'
ENGINE_PROPERTIES = 'ENGINE_PROPERTIES'
KRB_JAVA = 'java.security.krb5.conf'
PROPERTIES_DIRECTORY = '/etc/ovirt-engine/engine.conf.d'
EXTENSIONS_DIRECTORY = '/etc/ovirt-engine/extensions.d'
APACHE_EXTENSIONS = '/etc/httpd/conf.d'
EXTENSIONS_PKG = 'ovirt-engine-extension-aaa-*'
KRB_MODULE = 'mod_auth_kerb'
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

SIMPLE_AD = {
    'authz_file': 'ldap-authz-simple_ad.properties',
    'authz_name': 'ldap-authz-simple_ad',
    'authn_name': 'ldap-authn-simple_ad',
}

AD_GROUP32 = 'group32'
AD_GROUP32_NS = 'DC=ad-w2k12r2,DC=rhev,DC=lab,DC=eng,DC=brq,DC=redhat,DC=com'
AD_GROUP_USER = 'user1@ad-w2k12r2.rhev.lab.eng.brq.redhat.com'

SIMPLE_IPA = {
    'authz_file': 'ldap-authz-simple_ipa.properties',
    'authz_name': 'ldap-authz-simple_ipa',
    'authn_name': 'ldap-authn-simple_ipa',
}

IPA_GROUP32 = 'group32'
IPA_GROUP_LOOP1 = 'grouploop1'
IPA_GROUP_LOOP2 = 'grouploop2'
IPA_GROUP_USER = 'user1'
IPA_NAMESPACE = 'dc=brq-ipa,dc=rhev,dc=lab,dc=eng,dc=brq,dc=redhat,dc=com'
IPA_PASSWORD = '123456'

ADDIGEST_EXTENSION = {
    'authz_file': 'ldap-authz-test_digest_ad.properties',
    'authz_name': 'ldap-authz-test_digest_ad',
    'authn_name': 'ldap-authn-test_digest_ad',
}

ADDIGEST_USER = 'vdcadmin'
ADDIGEST_USER_DOMAIN = 'qa.lab.tlv.redhat.com'
ADDIGEST_PASSWORD = '123456'

IPAGSSAPI_EXTENSION = {
    'authz_file': 'ldap-authz-test_gssapi_ipa.properties',
    'authz_name': 'ldap-authz-test_gssapi_ipa',
    'authn_name': 'ldap-authn-test_gssapi_ipa',
}

IPAGSSAPI_USER = 'vdcadmin'
IPAGSSAPI_PASSWORD = '123456'

OPENLDAP_SSO = {
    'authz_file': 'ldap-authz-simple_openldap.properties',
    'authz_name': 'ldap-authz-simple_openldap',
    'authn_name': 'http',
}

SSO_USER = 'user1'
SSO_PASSWORD = '123456'

# ADW2K12 properties
ADW2K12_DOMAINS = ['ad-w2k12r2.rhev.lab.eng.brq.redhat.com',
                   'ad-w2k12r2p.rhev.lab.eng.brq.redhat.com',
                   'ad-w2k12r2pc.ad-w2k12r2p.rhev.lab.eng.brq.redhat.com',
                   'ad-w2k12r2lc.ad-w2k12r2.rhev.lab.eng.brq.redhat.com']
ADW2k12_USER_PASSWORD = 'Heslo123'
ADW2k12_USER1 = 'user1'


# Openldap
OPENLDAP = 'brq-openldap.rhev.lab.eng.brq.redhat.com'
OPENLDAP_ROOT_PW = 'qum5net'

OPENLDAP_HOST = resources.Host(OPENLDAP)
OPENLDAP_HOST.users.append(
    resources.RootUser(OPENLDAP_ROOT_PW)
)

# Services
APACHE_SERVICE = 'httpd'
