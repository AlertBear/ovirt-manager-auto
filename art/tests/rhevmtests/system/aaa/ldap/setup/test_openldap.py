from art.test_handler.tools import polarion, bz

from rhevmtests.system.aaa.ldap.setup import base


class OpenLdapAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13036')
    def test_install(self):
        pass


class OpenLdapUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    __test__ = True
    domain = 'openldap'

    @bz({'1313516': {}})
    @polarion('RHEVM3-13057')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class OpenLdapExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    __test__ = True
    domain = 'openldap'

    @bz({'1313516': {}})
    @polarion('RHEVM3-13047')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class OpenLdapDisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    __test__ = True
    domain = 'openldap'

    @bz({'1313516': {}})
    @polarion('RHEVM3-13056')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()
