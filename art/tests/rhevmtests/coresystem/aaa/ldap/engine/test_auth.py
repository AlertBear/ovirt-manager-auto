"""
Test possible configuration option of properties file.
"""

import os
import logging
import pytest

from art.rhevm_api.tests_lib.low_level import users, mla
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow

from rhevmtests.coresystem.aaa.ldap import config, common

logger = logging.getLogger(__name__)
CONF_NAME = '99-krb_ipa.conf'
KRB_CONF = 'krb_ipa.conf'


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Tearing down module %s", __name__)
        conf = os.path.join('%s/%s' % (config.PROPERTIES_DIRECTORY, CONF_NAME))
        common.removeFile(conf)

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)
    krb_conf_path = os.path.join(config.ENGINE_EXTENSIONS_DIR, KRB_CONF)
    krbjava = '%s=%s' % (config.KRB_JAVA, krb_conf_path)
    common.changeEngineProperties(CONF_NAME, config.ENGINE_PROPERTIES, krbjava)
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)


@tier2
class DirectLogin(TestCase):
    """
    TestCase to add user, assign him permissions and try to login.
    """
    conf = None
    FILTER = True
    USER = None
    PASSWORD = None
    DOMAIN = None
    NAMESPACE = None

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)

            testflow.teardown("Login as admin user")
            common.loginAsAdmin()

            user = cls.USER
            if cls.DOMAIN:
                user = '%s@%s' % (cls.USER, cls.DOMAIN)
            testflow.teardown("Removing user %s", cls.USER)
            assert users.removeUser(True, user, cls.conf['authz_name'])

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)

        user_upn = user = cls.USER
        if cls.DOMAIN:
            user_upn = '%s@%s' % (cls.USER, cls.DOMAIN)

        testflow.setup("Adding user %s", user)
        assert users.addExternalUser(
            True,
            user_name=user,
            domain=cls.conf['authz_name'],
            namespace=cls.NAMESPACE,
        )

        testflow.setup("Adding cluster permission to user %s", cls.USER)
        assert mla.addClusterPermissionsToUser(
            True,
            user_upn,
            config.CLUSTER_NAME[0],
            config.USERROLE,
            cls.conf['authz_name'],
        )

    def login(self):
        """ login as user """
        testflow.step("Login as user %s", self.USER)
        users.loginAsUser(
            self.USER,
            self.conf['authn_name'],
            self.PASSWORD,
            self.FILTER,
        )

        testflow.step("Testing connection with user %s", self.USER)
        assert common.connectionTest(), "User %s can't login." % self.USER


class TestADDigestMD5(DirectLogin):
    """
    Test digest md5 auth in AD.
    """
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


class TestIPAGSSAPI(DirectLogin):
    """
    Test gssapi auth in IPA.
    """
    conf = config.IPAGSSAPI_EXTENSION
    USER = config.IPAGSSAPI_USER
    PASSWORD = config.IPAGSSAPI_PASSWORD

    @polarion('RHEVM3-8230')
    @common.check(config.EXTENSIONS)
    def test_ipa_gssapi(self):
        """ IPA gssapi authentication """
        self.login()
