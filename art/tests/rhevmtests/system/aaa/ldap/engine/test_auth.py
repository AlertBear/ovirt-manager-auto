"""
Test possible configuration option of properties file.
"""
__test__ = True

import os
import logging

from rhevmtests.system.aaa.ldap import config, common
from art.rhevm_api.tests_lib.low_level import users, mla
from art.test_handler.tools import polarion
from art.unittest_lib import attr, CoreSystemTest as TestCase

logger = logging.getLogger(__name__)
CONF_NAME = '99-krb_ipa.conf'
KRB_CONF = 'krb_ipa.conf'


def setup_module():
    krb_conf_path = os.path.join(config.ENGINE_EXTENSIONS_DIR, KRB_CONF)
    krbjava = '%s=%s' % (config.KRB_JAVA, krb_conf_path)
    common.changeEngineProperties(CONF_NAME, config.ENGINE_PROPERTIES, krbjava)
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)


def teardown_module():
    conf = os.path.join('%s/%s' % (config.PROPERTIES_DIRECTORY, CONF_NAME))
    common.removeFile(conf)


@attr(tier=2)
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
    NAMESPACE = None

    def setUp(self):
        user_upn = user = self.USER
        if self.DOMAIN:
            user_upn = '%s@%s' % (self.USER, self.DOMAIN)
        users.addExternalUser(
            True,
            user_name=user,
            domain=self.conf['authz_name'],
            namespace=self.NAMESPACE,
        )
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
        assert common.connectionTest(), "User %s can't login." % self.USER


class ADDigestMD5(DirectLogin):
    """
    Test digest md5 auth in AD.
    """
    __test__ = True
    conf = config.ADDIGEST_EXTENSION
    USER = config.ADDIGEST_USER
    PASSWORD = config.ADDIGEST_PASSWORD
    DOMAIN = config.ADDIGEST_USER_DOMAIN
    NAMESPACE = config.ADDIGEST_NAMESPACE

    @polarion('RHEVM3-8229')
    @common.check(config.EXTENSIONS)
    def test_ad_digest_md5(self):
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

    @polarion('RHEVM3-8230')
    @common.check(config.EXTENSIONS)
    def test_ipa_gssapi(self):
        """ IPA gssapi authentication """
        self.login()
