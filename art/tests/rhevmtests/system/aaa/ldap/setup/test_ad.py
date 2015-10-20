from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.aaa.ldap.setup import base


NAMESPACE = 'DC=ad-w2k12r2,DC=rhev,DC=lab,DC=eng,DC=brq,DC=redhat,DC=com'
PASSWORD = 'Heslo123'
DOMAIN = 'ad-w2k12r2'


class ADAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13035')
    def test_install(self):
        pass


class ADUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    __test__ = True
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13058')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class ADExpiredAccount(base.BaseExpiredAccount):
    """ Login as user with expired account """
    __test__ = True
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13052')
    def test_expired_account(self):
        """ Login as user with expired account """
        self.expired_account()


class ADExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    __test__ = True
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13049')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class ADDisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    __test__ = True
    domain = DOMAIN
    password = PASSWORD
    namespace = NAMESPACE

    @polarion('RHEVM3-13053')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()
