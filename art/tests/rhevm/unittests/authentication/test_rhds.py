'''
Testing authentication of users from OpenLDAP.
Nothing is created using default DC and default cluster.
Authentication of expired users, users from group and correct users.
'''

__test__ = True

import config
import test_base as base


class RHDSNormalUserAndGroupUser(base.BaseNormalUserAndGroupUser):
    """ Login as normal user and user from group.  """
    __test__ = True
    domain = config.RHDS_DOMAIN


class RHDSGroupsPersistency(base.BaseGroupsPersistency):
    """ After user removal, check that his group persist """
    __test__ = True
    domain = config.RHDS_DOMAIN


class RHDSExpiredAccount(base.BaseExpiredAccount):
    """ Login as user with expired account """
    __test__ = True
    domain = config.RHDS_DOMAIN


class RHDSExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    __test__ = True
    domain = config.RHDS_DOMAIN


class RHDSUserWithManyGroups(base.BaseUserWithManyGroups):
    """  Login as user with many groups  """
    __test__ = True
    domain = config.RHDS_DOMAIN


class RHDSSearchForUsersAndGroups(base.BaseSearchForUsersAndGroups):
    """ Search within domain for users and groups """
    __test__ = True
    name = 'user0'
    last_name = 'user0'
    domain = config.RHDS_DOMAIN
