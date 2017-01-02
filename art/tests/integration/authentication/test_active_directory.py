'''
Testing authentication of users from active directory.
Nothing is created using default DC and default cluster.
Authentication of users expiredPw/expiredAcc/disabled is tested.
Testing authentication user from groups and users from 2 AD.
'''


import time
import logging
from authentication import config
from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import mla, users
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import polarion
from test_base import connectionTest
from art.core_api.apis_utils import TimeoutingSampler
from config import non_ge

__test__ = True

logger = logging.getLogger(__name__)
MB = 1024 * 1024
AUTH = 'auth'
AUTH_CONF = 'auth-conf'
OUT = '> /dev/null 2>&1 &'
TCP_DUMP = 'nohup tcpdump -l -s 65535 -A -vv port 389 -w /tmp/tmp.cap %s' % OUT
CHECK_DUMP = 'tcpdump -A -r /tmp/tmp.cap 2>/dev/null | grep %s'
CLEAN = 'rm -f /tmp/tmp.cap && kill -9 `pgrep tcpdump`'


def set_sasl_qop(level):
    config.ENGINE_HOST.executor().run_cmd(
        ['engine-config', '-s', 'SASL_QOP=%s' % level]
    )
    config.ENGINE.restart()
    for status in TimeoutingSampler(
        timeout=70,
        sleep=5,
        func=lambda: config.ENGINE.health_page_status,
    ):
        if status:
            break


def teardown_module():
    set_sasl_qop(AUTH)


def addUserWithClusterPermissions(user_name):
    name, domain = user_name.split('@')
    assert users.addUser(True, user_name=name, domain=domain)
    assert mla.addClusterPermissionsToUser(
        True, name, config.MAIN_CLUSTER_NAME,
        role='UserVmManager', domain=domain
    )


@non_ge
@attr(tier=2)
class ActiveDirectory(TestCase):
    __test__ = False

    PASSWORD = None
    domain = None

    def _loginAsUser(self, user_name, filter=True):
        name, domain = user_name.split('@')
        users.loginAsUser(name, domain, self.PASSWORD, filter)

    @classmethod
    def setup_class(cls):
        for user in [
            config.AD2_USER,
            config.TEST_USER(cls.domain),
            config.EXPIRED_PSW_NAME(cls.domain),
            config.DISABLED_ACC(cls.domain),
            config.EXPIRED_ACC_NAME(cls.domain),
            config.NORMAL_USER(cls.domain),
            config.TEST_USER_DIFFERENT_AD(cls.domain)[0],
        ]:
            addUserWithClusterPermissions(user)
        assert users.addGroup(True, config.GROUP(cls.domain))
        assert mla.addClusterPermissionsToGroup(
            True, config.GROUP(cls.domain),
            config.MAIN_CLUSTER_NAME
        )

    @classmethod
    def teardown_class(cls):
        users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                          config.USER_PASSWORD, False)
        for username in [
            config.TEST_USER(cls.domain),
            config.EXPIRED_PSW_NAME(cls.domain),
            config.DISABLED_ACC(cls.domain),
            config.EXPIRED_ACC_NAME(cls.domain),
            config.NORMAL_USER(cls.domain),
            config.USER_FROM_GROUP(cls.domain),
            config.TEST_USER_DIFFERENT_AD(cls.domain)[0],
        ]:
            user, domain = username.split('@')
            assert users.removeUser(True, user, domain)
        assert users.deleteGroup(True, config.GROUP(cls.domain))

    def setUp(self):
        users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                          config.USER_PASSWORD, False)

    @polarion("RHEVM3-7354")
    @attr(tier=1)
    def disabledAccount(self):
        """ Disabled account """
        self._loginAsUser(config.DISABLED_ACC(self.domain))
        assert not connectionTest(), "User with disabled acc can login."
        logger.info("User with disabled acc can't login.")

    @polarion("RHEVM3-7353")
    @attr(tier=1)
    def expiredPassword(self):
        """ Expired password """
        self._loginAsUser(config.EXPIRED_PSW_NAME(self.domain))
        assert not connectionTest(), "User with expired psw can login."
        logger.info("User with expired password can't login.")

    @polarion("RHEVM3-7355")
    @attr(tier=1)
    def expiredUser(self):
        """ Expired user """
        self._loginAsUser(config.EXPIRED_ACC_NAME(self.domain))
        assert not connectionTest(), "Expired user can login."
        logger.info("Expired user can't login.")

    @polarion("RHEVM3-7349")
    @attr(tier=1)
    def userFromGroup(self):
        """ Test if user from group can login """
        user_name = config.USER_FROM_GROUP(self.domain)
        self._loginAsUser(user_name, filter=False)
        assert connectionTest()
        logger.info("User from group can login")

    def _checkEnc(self, auth, result):
        user, domain = config.NORMAL_USER(self.domain).split('@')

        set_sasl_qop(auth)

        assert runMachineCommand(
            True, ip=config.VDC_HOST, cmd=TCP_DUMP, user=config.HOSTS_USER,
            password=config.VDC_PASSWORD
        )[0], "Run cmd %s failed." % TCP_DUMP

        users.loginAsUser(user, domain, self.PASSWORD, True)
        assert connectionTest()
        time.sleep(20)

        status = runMachineCommand(True, ip=config.VDC_HOST,
                                   cmd=CHECK_DUMP % user,
                                   user=config.HOSTS_USER,
                                   password=config.VDC_PASSWORD)
        assert status[0] == result, "Run cmd %s failed." % CHECK_DUMP

        assert runMachineCommand(
            True, ip=config.VDC_HOST, cmd=CLEAN, user=config.HOSTS_USER,
            password=config.VDC_PASSWORD
        )[0], "Run cmd %s failed." % CLEAN
        logger.info("Authentication passed.")

    @polarion("RHEVM3-7348")
    def ldapEncryption(self):
        """ LDAP encryption """
        self._checkEnc(AUTH, True)
        self._checkEnc(AUTH_CONF, False)

    @polarion("RHEVM3-7362")
    def multipleDomains(self):
        """ Multiple domains: Two ADs, using FQDN names """
        self._loginAsUser(config.TEST_USER(self.domain))
        assert connectionTest()
        user_name, password = config.TEST_USER_DIFFERENT_AD(self.domain)
        name, domain = user_name.split('@')
        users.loginAsUser(name, domain, password, True)
        assert connectionTest()
        logger.info("User with same name from different domains can login.")


class AD(ActiveDirectory):
    """ AD 2003 """
    __test__ = True
    domain = config.AD2_DOMAIN
    PASSWORD = config.USER_PASSWORD


class AD_W2K12_R2(ActiveDirectory):
    """ AD 2012 """
    __test__ = True
    domain = config.W2K12R2_DOMAIN
    PASSWORD = config.W2K12R2_PASSWORD


class AD_W2K8_R2(ActiveDirectory):
    """ AD 2008 """
    __test__ = True
    domain = config.W2K8R2_DOMAIN
    PASSWORD = config.W2K8R2_PASSWORD
