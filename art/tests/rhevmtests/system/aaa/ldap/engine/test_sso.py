"""
Test rhevm restapi sso.
"""

import os
import logging
import pytest

from art.rhevm_api.tests_lib.low_level import users, mla
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, CoreSystemTest as TestCase, testflow

from rhevmtests.system.aaa.ldap import config, common

logger = logging.getLogger(__name__)
APACHE_EXTENSIONS = {}
KRB5_CONF = 'krb5.conf'
KEYTAB = '/etc/http.keytab'
APACHE_FIXTURES = 'apache'
APACHE_CONF = 'z-ovirt-sso.conf'


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Tearing down module %s", __name__)

        fqdn = config.ENGINE_HOST.fqdn
        delete_principal = 'delete_principal -force HTTP/%s' % fqdn

        testflow.teardown("Deleting principal %s", fqdn)
        config.OPENLDAP_HOST.executor().run_cmd(
            ['kadmin.local', '-q', delete_principal])

        testflow.teardown("Removing Kerberos")
        with config.ENGINE_HOST.executor().session() as ss:
            ss.run_cmd([
                'yum', 'remove', '-y', config.KRB_MODULE, config.MISC_PKG
            ])
            ss.run_cmd(['rm', '-f', KEYTAB])

        testflow.teardown("Cleaning extensions directory")
        common.cleanExtDirectory(config.APACHE_EXTENSIONS, [APACHE_CONF])

        testflow.teardown("Restarting Apache")
        config.ENGINE_HOST.service(config.APACHE_SERVICE).restart()

        testflow.teardown("Login as user admin")
        common.loginAsAdmin()

        testflow.teardown("Removing user %s", config.SSO_USER)
        assert users.removeUser(
            True,
            config.SSO_USER,
            config.OPENLDAP_SSO['authz_name'],
        )

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)

    fqdn = config.ENGINE_HOST.fqdn
    add_principal = 'add_principal -randkey HTTP/%s' % fqdn
    add_keytab = 'ktadd -keytab %s HTTP/%s' % (KEYTAB, fqdn)

    testflow.setup("Installing and configuring Kerberos")
    with config.ENGINE_HOST.executor().session() as engine:
        engine.run_cmd([
            'yum', 'install', '-y',
            config.GSSAPI_MODULE,
            config.SESSION_MODULE,
            config.MISC_PKG
        ])
        with config.OPENLDAP_HOST.executor().session() as openldap:
            openldap.run_cmd(['kadmin.local', '-q', add_principal])
            openldap.run_cmd(['kadmin.local', '-q', add_keytab])
            with openldap.open_file(KEYTAB, 'rb') as ldap_kt:
                with engine.open_file(KEYTAB, 'wb') as engine_kt:
                    engine_kt.write(ldap_kt.read())
                    logger.info('%s was created.' % KEYTAB)
            openldap.run_cmd(['rm', '-f', KEYTAB])

    testflow.setup("Adding user %s", config.SSO_USER)
    assert users.addExternalUser(
        True,
        user_name=config.SSO_USER,
        domain=config.OPENLDAP_SSO['authz_name'],
    )

    testflow.setup("Adding cluster permission to user %s", config.SSO_USER)
    assert mla.addClusterPermissionsToUser(
        True,
        config.SSO_USER,
        config.CLUSTER_NAME[0],
        domain=config.OPENLDAP_SSO['authz_name'],
    )

    testflow.setup("Preparing extensions")
    common.prepareExtensions(APACHE_FIXTURES, config.APACHE_EXTENSIONS,
                             APACHE_EXTENSIONS, clean=False,
                             service=config.APACHE_SERVICE)


@attr(tier=2)
@bz({'1399479': {}})
class SSOLogin(TestCase):
    """
    Test sso login.
    """
    __test__ = True

    conf = config.OPENLDAP_SSO
    COOKIE_FILE = '/tmp/cookiejar.txt'
    USER = config.SSO_USER
    PASSWORD = config.SSO_PASSWORD
    executor = config.ENGINE_HOST.executor()

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)

            testflow.teardown("Destroying kerberos ticket")
            with cls.executor.session() as ss:
                ss.run_cmd(['kdestroy'])
                ss.run_cmd(['rm', '-f', cls.COOKIE_FILE])

        request.addfinalizer(finalize)

    @polarion('RHEVM3-6757')
    @common.check(config.EXTENSIONS)
    def test_sso_login(self):
        """  Test sso login to REST API """

        testflow.step("Initializing kerberos ticket")
        krb_conf = os.path.join(config.ENGINE_EXTENSIONS_DIR, KRB5_CONF)
        # Note that I can't separate this to more commands as it's forbidden
        login = [
            'export', 'KRB5_CONFIG=%s' % krb_conf,
            '&&',
            'echo', config.SSO_PASSWORD,
            '|',
            'kinit', self.USER,
            '&&',
            'curl',
            '-v', '-k', '--negotiate',
            '-u', ':',
            '-b', self.COOKIE_FILE,
            '-c', self.COOKIE_FILE,
            config.ENGINE_URL
        ]

        login_ret = self.executor.run_cmd(login)
        assert not login_ret[0], login_ret[1]
        logger.info(login_ret[2])
