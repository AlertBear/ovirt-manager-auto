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

# AD
AD1_DOMAIN = PARAMETERS.get('ad1_domain', None)
AD2_DOMAIN = PARAMETERS.get('ad2_domain', None)

AD1_USER_WITH_GROUP = PARAMETERS.get('ad1_user_with_group_name', None)
AD1_NORMAL = PARAMETERS.get('ad1_normal_user_name', None)
AD1_USER_NAME = PARAMETERS.get('ad1_user_name', None)
AD2_USER_NAME = AD1_USER_NAME
AD1_EXPIRED_PSW = PARAMETERS.get('ad1_expired_psw_name', None)
AD1_EXPIRED_USER = PARAMETERS.get('ad1_expired_user_name', None)
AD1_DISABLED = PARAMETERS.get('ad1_disabled_name', None)

AD1_NORMAL_USER = PARAMETERS.get('ad1_normal_user', None)
AD1_USER = PARAMETERS.get('ad1_user', None)
USER_WITH_GROUP = PARAMETERS.get('ad1_user_with_group', None)
AD2_USER = PARAMETERS.get('ad2_user', None)
USER_EXPIRED_PSW = PARAMETERS.get('ad1_expired_psw', None)
USER_EXPIRED_USER = PARAMETERS.get('ad1_expired_user', None)
USER_DISABLED = PARAMETERS.get('ad1_disabled', None)

# IPA
IPA_DOMAIN = str(PARAMETERS.get('ipa_domain', None)).upper()
IPA_PASSWORD = '123456'

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

MAIN_CLUSTER_NAME = PARAMETERS.get('cluster_name', None)

AD_TCMS_PLAN_ID = 2112
IPA_TCMS_PLAN_ID = 3999
