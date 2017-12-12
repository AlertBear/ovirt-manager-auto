from art.test_handler.tools import polarion

from rhevmtests.coresystem.aaa.ldap.setup import base


class RHDSAutoSetup(base.TestCase):
    """ Case always pass - there is assert for it in __init__ """

    @polarion('RHEVM3-13037')
    def test_install(self):
        pass


class TestRHDSUserFromGroup(base.BaseUserFromGroup):
    """ Login as user from group. """
    domain = 'rhds'

    @polarion('RHEVM3-13059')
    def test_user_from_group(self):
        """ Authenticate as user from group """
        self.user_from_group()


class TestRHDSExpiredAccount(base.BaseExpiredAccount):
    """ Login as user with expired account """
    domain = 'rhds'

    @polarion('RHEVM3-13051')
    def test_expired_account(self):
        """ Login as user with expired account """
        self.expired_account()


class TestRHDSExpiredPassword(base.BaseExpiredPassword):
    """ Login as user with expired password """
    domain = 'rhds'

    @polarion('RHEVM3-13050')
    def test_expired_password(self):
        """ Login as user with expired password """
        self.expired_password()


class TestRHDSDisabledAccount(base.BaseDisabledAccount):
    """ Login as disabled user """
    domain = 'rhds'

    @polarion('RHEVM3-13054')
    def test_disabled_account(self):
        """ Login as user with disabled account """
        self.disabled_account()


class RHDSSpecialCharsSearch(base.BaseSpecialCharsSearch):
    """ Search special characters in RHDS """
    # https://bugzilla.redhat.com/show_bug.cgi?id=1186039
    # They've decided to not fix, but I will let the case here for time
    # being as if some customer insist they will have to fix it.
    domain = 'rhds-authz'

    @polarion('RHEVM3-14523')
    def test_special_characters(self):
        """ Test search special characters in RHDS """
        self.search()

    @polarion('RHEVM3-14524')
    def test_special_characters_non_working(self):
        """ Test search special characters in RHDS """
        self.search(
            special_characters=(
                '!', '^', '&', ')', '=', "'", '"', '<', '>', ' s',
            )
        )
