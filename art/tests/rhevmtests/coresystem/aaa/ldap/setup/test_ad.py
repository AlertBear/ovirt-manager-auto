from art.test_handler.tools import bz, polarion

from rhevmtests.coresystem.aaa.ldap.setup import base


NAMESPACE = 'DC=ad-w2k12r2,DC=rhev,DC=lab,DC=eng,DC=brq,DC=redhat,DC=com'
PASSWORD = 'Heslo123'
DOMAIN = 'ad-w2k12r2'


class ADAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13035')
    def test_install(self):
        pass


@bz({'1446525': {}})
class TestADUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13058')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class TestADExpiredAccount(base.BaseExpiredAccount):
    """ Login as user with expired account """
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13052')
    def test_expired_account(self):
        """ Login as user with expired account """
        self.expired_account()


class TestADExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13049')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class TestADDisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13053')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()


class TestADDifferentUPN(base.AuthBaseCase):
    """ Login as user with different UPN """
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE
    user = 'automation_upn'

    @polarion('RHEVM3-14484')
    def test_different_upn(self):
        """ Login as user with disabled account """
        assert self.login(user='automation_upn@w2k12r2-t1.com')
