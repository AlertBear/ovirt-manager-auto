"""
Test possible configuration option of properties file.
"""
__test__ = True

import os
import logging

from rhevmtests.system.generic_ldap import config, common
from art.test_handler.tools import bz
from art.rhevm_api.tests_lib.low_level import users, mla
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.unittest_lib.common import is_bz_state
from nose.tools import istest

LOGGER = logging.getLogger(__name__)
EXTENSIONS = {}
NAME = __name__
NAME = NAME[NAME.rfind('.') + 1:]
CONF_NAME = '99-krb_ipa.conf'
KRB_CONF = 'krb_ipa.conf'
BZ1147900_FIXED = is_bz_state('1147900')


def setup_module():
    krb_conf_path = os.path.join(config.EXTENSIONS_DIRECTORY, KRB_CONF)
    krbjava = '%s=%s' % (config.KRB_JAVA, krb_conf_path)
    common.changeEngineProperties(CONF_NAME, config.ENGINE_PROPERTIES, krbjava)
    common.prepareExtensions(NAME, config.EXTENSIONS_DIRECTORY, EXTENSIONS)


def teardown_module():
    conf = os.path.join('%s/%s' % (config.PROPERTIES_DIRECTORY, CONF_NAME))
    common.removeFile(conf)
    common.cleanExtDirectory(config.EXTENSIONS_DIRECTORY)


@attr(tier=1)
class DirectLogin(TestCase):
    """
    TestCase to add user, assign him permissions and try to login.
    """
    __test__ = True
    conf = None
    FILTER = True
    USER = None
    PASSWORD = None
    DOMAIN = None

    def setUp(self):
        user_upn = user = self.USER
        if self.DOMAIN:
            user_upn = '%s@%s' % (self.USER, self.DOMAIN)
        users.addUser(True, user_name=user_upn if BZ1147900_FIXED else user,
                      domain=self.conf['authz_name'])
        mla.addClusterPermissionsToUser(True, user_upn,
                                        config.DEFAULT_CLUSTER_NAME,
                                        config.USERROLE,
                                        self.conf['authz_name'])

    @classmethod
    def teardown_class(cls):
        common.loginAsAdmin()
        user = cls.USER
        if cls.DOMAIN:
            user = '%s@%s' % (cls.USER, cls.DOMAIN)
        assert users.removeUser(True, user, cls.conf['authz_name'])

    def login(self):
        """ login as user """
        users.loginAsUser(self.USER, self.conf['authn_name'],
                          self.PASSWORD, self.FILTER)
        self.assertTrue(common.connectionTest(),
                        "User %s can't login." % self.USER)


class ADDigestMD5(DirectLogin):
    """
    Test digest md5 auth in AD.
    """
    __test__ = True
    conf = config.ADDIGEST_EXTENSION
    USER = config.ADDIGEST_USER
    PASSWORD = config.ADDIGEST_PASSWORD
    DOMAIN = config.ADDIGEST_USER_DOMAIN

    @istest
    @common.check(EXTENSIONS)
    @bz(1151127)
    def ad_digest_md5(self):
        """ active directory digest md5 authentication """
        self.login()


class IPAGSSAPI(DirectLogin):
    """
    Test gssapi auth in IPA.
    """
    __test__ = True
    conf = config.IPAGSSAPI_EXTENSION
    USER = config.IPAGSSAPI_USER
    PASSWORD = config.IPAGSSAPI_PASSWORD

    @istest
    @common.check(EXTENSIONS)
    def ipa_gssapi(self):
        """ IPA gssapi authentication """
        self.login()
