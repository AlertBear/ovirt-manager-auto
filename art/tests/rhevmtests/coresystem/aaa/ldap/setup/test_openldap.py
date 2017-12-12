from art.test_handler.tools import polarion

from rhevmtests.coresystem.aaa.ldap.setup import base


class OpenLdapAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13036')
    def test_install(self):
        pass


class TestOpenLdapUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    domain = 'openldap'

    @polarion('RHEVM3-13057')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class TestOpenLdapExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    domain = 'openldap'

    @polarion('RHEVM3-13047')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class TestOpenLdapDisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    domain = 'openldap'

    @polarion('RHEVM3-13056')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()
