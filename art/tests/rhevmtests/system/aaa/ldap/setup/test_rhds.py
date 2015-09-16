from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.aaa.ldap.setup import base


class RHDSAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13037')
    def test_install(self):
        pass


class RHDSUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    __test__ = True
    domain = 'rhds'

    @polarion('RHEVM3-13059')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class RHDSExpiredAccount(base.BaseExpiredAccount):
    """ Login as user with expired account """
    __test__ = True
    domain = 'rhds'

    @polarion('RHEVM3-13051')
    def test_expired_account(self):
        """ Login as user with expired account """
        self.expired_account()


class RHDSExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    __test__ = True
    domain = 'rhds'

    @polarion('RHEVM3-13050')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class RHDSDisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    __test__ = True
    domain = 'rhds'

    @polarion('RHEVM3-13054')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()
