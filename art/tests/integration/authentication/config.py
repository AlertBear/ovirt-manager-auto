""" Test configuration - login data to the servers and test setup options.  """

__test__ = False

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
PARAMETERS = ART_CONFIG['PARAMETERS']
IPA = ART_CONFIG['IPA']
ACTIVE_DIRECTORY = ART_CONFIG['ACTIVE_DIRECTORY']
RHDS = ART_CONFIG['RHDS']
OpenLDAP = ART_CONFIG['OpenLDAP']


def getUserWithDomain(user_name, user_domain):
    return '%s@%s' % (user_name, user_domain)

USER_PASSWORD = '123456'

# TLV domain
AD2_DOMAIN = ACTIVE_DIRECTORY.get('ad2_domain', None)
AD2_USER = ACTIVE_DIRECTORY.get('ad2_user', None)
AD2_USER_NAME = ACTIVE_DIRECTORY.get('ad2_user_name', None)

# IPA
IPA_DOMAIN = str(IPA.get('ipa_domain', None))
IPA_PASSWORD = str(IPA.get('ipa_password', None))

# TODO ADD expired_acc_name if none skip?
IPA_WITH_MANY_GROUPS_NAME = IPA.get('ipa_with_many_groups_name', None)
IPA_EXPIRED_PSW_NAME = IPA.get('ipa_expired_psw_name', None)
IPA_DISABLED_NAME = IPA.get('ipa_disabled_name', None)
IPA_REGULAR_NAME = IPA.get('ipa_regular_name', None)
IPA_GROUP = IPA.get('ipa_group', None)
IPA_WITH_GROUP_NAME = IPA.get('ipa_with_group_name', None)
IPA_TESTING_USER_NAME = IPA.get('ipa_testing_user_name', None)

IPA_WITH_MANY_GROUPS = IPA.get('ipa_with_many_groups', None)
IPA_EXPIRED_PSW = IPA.get('ipa_expired_psw', None)
IPA_DISABLED = IPA.get('ipa_disabled', None)
IPA_REGULAR = IPA.get('ipa_regular', None)
IPA_WITH_GROUP = IPA.get('ipa_with_group', None)
IPA_TESTING_USER = IPA.get('ipa_testing_user', None)

REGULAR_FORMAT1 = "%s@%s".lower() % (IPA_REGULAR_NAME, IPA_DOMAIN)
REGULAR_FORMAT2 = "%s\%s".lower() % (IPA_DOMAIN, IPA_REGULAR_NAME)

# OpenLDAP
LDAP_DOMAIN = str(OpenLDAP.get('ldap_domain', None))
LDAP_PASSWORD = str(OpenLDAP.get('ldap_password', None))

LDAP_WITH_MANY_GROUPS_NAME = OpenLDAP.get('ldap_with_many_groups_name', None)
LDAP_EXPIRED_PSW_NAME = OpenLDAP.get('ldap_expired_psw_name', None)
LDAP_EXPIRED_ACC_NAME = OpenLDAP.get('ldap_expired_acc_name', None)
LDAP_REGULAR_NAME = OpenLDAP.get('ldap_regular_name', None)
LDAP_GROUP = OpenLDAP.get('ldap_group', None)
LDAP_GROUP2 = OpenLDAP.get('ldap_group2', None)
LDAP_USER_FROM_GROUP = OpenLDAP.get('ldap_user_from_group', None)
LDAP_TESTING_USER_NAME = OpenLDAP.get('ldap_testing_user_name', None)

# RHDS
RHDS_DOMAIN = str(RHDS.get('rhds_domain', None))

# W2K8R2
W2K8R2_DOMAIN = str(ACTIVE_DIRECTORY.get('w2k8r2_domain', None))
W2K8R2_PASSWORD = str(ACTIVE_DIRECTORY.get('w2k8r2_password', 'Heslo123'))

# W2K12R2
W2K12R2_DOMAIN = str(ACTIVE_DIRECTORY.get('w2k12rw_domain', None))
W2K12R2_PASSWORD = str(ACTIVE_DIRECTORY.get('w2k12rw_password', 'Heslo123'))

# Common
DOMAINS = {
    RHDS_DOMAIN: [RHDS, 'rhds'],
    IPA_DOMAIN: [IPA, 'ipa'],
    AD2_DOMAIN: [ACTIVE_DIRECTORY, 'ad2'],
    W2K8R2_DOMAIN: [ACTIVE_DIRECTORY, 'w2k8r2'],
    W2K12R2_DOMAIN: [ACTIVE_DIRECTORY, 'w2k12r2'],
}


def getParamFromDomain(param, domain_name):
    try:
        return DOMAINS[domain_name][0].get(
            '%s_%s' % (DOMAINS[domain_name][1], param)
        )
    except KeyError:
        raise KeyError("%s domain is not configured, please configure it"
                       % domain_name)


def GROUP(domain):
    return getParamFromDomain('group', domain)


def REGULAR_NAME(domain):
    return getParamFromDomain('regular_name', domain)


def USER_FROM_GROUP(domain):
    return getParamFromDomain('user_from_group', domain)


def EXPIRED_ACC_NAME(domain):
    return getParamFromDomain('expired_acc_name', domain)


def EXPIRED_PSW_NAME(domain):
    return getParamFromDomain('expired_psw_name', domain)


def DISABLED_ACC(domain):
    return getParamFromDomain('disabled', domain)


def WITH_MANY_GROUPS_NAME(domain):
    return getParamFromDomain('with_many_groups_name', domain)


def NORMAL_USER(domain):
    return getParamFromDomain('normal_user', domain)


def TEST_USER(domain):
    return getParamFromDomain('user', domain)


def TEST_USER_DIFFERENT_AD(domain):
    domains = {
        AD2_DOMAIN: {
            'domain': W2K12R2_DOMAIN,
            'password': W2K12R2_PASSWORD
        },
        W2K12R2_DOMAIN: {
            'domain': W2K8R2_DOMAIN,
            'password': W2K8R2_PASSWORD,
        },
        W2K8R2_DOMAIN: {
            'domain': AD2_DOMAIN,
            'password': USER_PASSWORD,
        },
    }
    return getParamFromDomain(
        'user', domains[domain]['domain']
    ), domains[domain]['password']


MAIN_CLUSTER_NAME = 'Default'

VDC_ADMIN_USER = 'admin'
VDC_ADMIN_DOMAIN = 'internal'

VDC_HOST = REST_CONNECTION['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
VDC_ROOT_USER = "root"
HOSTS_USER = 'root'
VDC_PASSWORD = REST_CONNECTION['password']
VDC_PORT = REST_CONNECTION['port']
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']
ENGINE_URL = '%s://%s:%s/%s' % (
    REST_CONNECTION.get('scheme'),
    VDC_HOST,
    VDC_PORT,
    ENGINE_ENTRY_POINT
)
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)
ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        VDC_ADMIN_USER,
        VDC_PASSWORD,
        resources.Domain(VDC_ADMIN_DOMAIN),
    ),
    schema=REST_CONNECTION.get('schema'),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT,
)
