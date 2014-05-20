""" Test configuration - login data to the servers and test setup options.  """

__test__ = False

from . import ART_CONFIG


def getUserWithDomain(user_name, user_domain):
    return '%s@%s' % (user_name, user_domain)


PARAMETERS = ART_CONFIG['PARAMETERS']
REST = ART_CONFIG['REST_CONNECTION']

OVIRT_ROOT = 'root'
OVIRT_ADDRESS = REST.get('host', None)
OVIRT_ROOT_PASSWORD = PARAMETERS.get('vdc_password', None)
OVIRT_USERNAME = REST.get('user', None)
OVIRT_DOMAIN = REST.get('user_domain', None)
OVIRT_PASSWORD = REST.get('password', None)
USER_PASSWORD = PARAMETERS.get('user_password', None)

AD1_DOMAIN = PARAMETERS.get('ad1_domain', None)
AD2_DOMAIN = PARAMETERS.get('ad2_domain', None)

AD2_USER = PARAMETERS.get('ad2_user', None)
AD2_USER_NAME = PARAMETERS.get('ad2_user_name', None)

# IPA
IPA_DOMAIN = str(PARAMETERS.get('ipa_domain', None))
IPA_PASSWORD = '123456'

# TODO ADD expired_acc_name if none skip?
IPA_WITH_MANY_GROUPS_NAME = PARAMETERS.get('ipa_with_many_groups_name', None)
IPA_EXPIRED_PSW_NAME = PARAMETERS.get('ipa_expired_psw_name', None)
IPA_DISABLED_NAME = PARAMETERS.get('ipa_disabled_name', None)
IPA_REGULAR_NAME = PARAMETERS.get('ipa_regular_name', None)
IPA_GROUP = PARAMETERS.get('ipa_group', None)
IPA_WITH_GROUP_NAME = PARAMETERS.get('ipa_with_group_name', None)
IPA_TESTING_USER_NAME = PARAMETERS.get('ipa_testing_user_name', None)

IPA_WITH_MANY_GROUPS = PARAMETERS.get('ipa_with_many_groups', None)
IPA_EXPIRED_PSW = PARAMETERS.get('ipa_expired_psw', None)
IPA_DISABLED = PARAMETERS.get('ipa_disabled', None)
IPA_REGULAR = PARAMETERS.get('ipa_regular', None)
IPA_WITH_GROUP = PARAMETERS.get('ipa_with_group', None)
IPA_TESTING_USER = PARAMETERS.get('ipa_testing_user', None)

REGULAR_FORMAT1 = "%s@%s".lower() % (IPA_REGULAR_NAME, IPA_DOMAIN)
REGULAR_FORMAT2 = "%s\%s".lower() % (IPA_DOMAIN, IPA_REGULAR_NAME)

# OpenLDAP
LDAP_DOMAIN = str(PARAMETERS.get('ldap_domain', None))
LDAP_PASSWORD = str(PARAMETERS.get('ldap_password', None))

LDAP_WITH_MANY_GROUPS_NAME = PARAMETERS.get('ldap_with_many_groups_name', None)
LDAP_EXPIRED_PSW_NAME = PARAMETERS.get('ldap_expired_psw_name', None)
LDAP_EXPIRED_ACC_NAME = PARAMETERS.get('ldap_expired_acc_name', None)
LDAP_REGULAR_NAME = PARAMETERS.get('ldap_regular_name', None)
LDAP_GROUP = PARAMETERS.get('ldap_group', None)
LDAP_GROUP2 = PARAMETERS.get('ldap_group2', None)
LDAP_USER_FROM_GROUP = PARAMETERS.get('ldap_user_from_group', None)
LDAP_TESTING_USER_NAME = PARAMETERS.get('ldap_testing_user_name', None)

# RHDS
RHDS_DOMAIN = str(PARAMETERS.get('rhds_domain', None))
W2K8R2_DOMAIN = str(PARAMETERS.get('w2k8r2_domain', None))
W2K8R2_PASSWORD = str(PARAMETERS.get('w2k8r2_password', 'Heslo123'))
W2K12R2_DOMAIN = str(PARAMETERS.get('w2k12rw_domain', None))
W2K12R2_PASSWORD = str(PARAMETERS.get('w2k12rw_password', 'Heslo123'))

# Common
DOMAINS = {RHDS_DOMAIN: 'rhds', IPA_DOMAIN: 'ipa', AD1_DOMAIN: 'ad1',
           W2K8R2_DOMAIN: 'w2k8r2', W2K12R2_DOMAIN: 'w2k12r2'}


def getParamFromDomain(param, domain_name):
    try:
        return PARAMETERS.get('%s_%s' % (DOMAINS[domain_name], param))
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

MAIN_CLUSTER_NAME = PARAMETERS.get('cluster_name', None)
AD_TCMS_PLAN_ID = 2112
IPA_TCMS_PLAN_ID = 3999
RHDS_TCMS_PLAN_ID = 5859
LDAP_TCMS_PLAN_ID = 9906
