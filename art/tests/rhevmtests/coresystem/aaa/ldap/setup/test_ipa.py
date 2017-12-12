from art.test_handler.tools import polarion

from rhevmtests.coresystem.aaa.ldap.setup import base


class IPAAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13038')
    def test_install(self):
        pass


class TestIPAUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    domain = 'ipa'

    @polarion('RHEVM3-13060')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class TestIPAExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    domain = 'ipa'

    @polarion('RHEVM3-13048')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class TestIPADisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    domain = 'ipa'

    @polarion('RHEVM3-13055')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()
