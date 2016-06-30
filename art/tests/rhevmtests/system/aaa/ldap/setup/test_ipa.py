from art.test_handler.tools import polarion

from rhevmtests.system.aaa.ldap.setup import base


class IPAAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13038')
    def test_install(self):
        pass


class IPAUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    __test__ = True
    domain = 'ipa'

    @polarion('RHEVM3-13060')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class IPAExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    __test__ = True
    domain = 'ipa'

    @polarion('RHEVM3-13048')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class IPADisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    __test__ = True
    domain = 'ipa'

    @polarion('RHEVM3-13055')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()
