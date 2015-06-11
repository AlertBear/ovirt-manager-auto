from art.rhevm_api.tests_lib.low_level import users
from rhevmtests.system.user_roles_tests import config


def addUser(positive, user_name, domain):
    return users.addExternalUser(
        positive=positive,
        user_name='%s@%s' % (user_name, config.PROFILE),
        principal='%s@%s' % (user_name, config.PROFILE),
        domain=domain,
    )


def removeUser(positive, user_name):
    return users.removeUser(
        positive,
        '%s@%s' % (user_name, config.PROFILE),
        config.USER_DOMAIN,
    )
