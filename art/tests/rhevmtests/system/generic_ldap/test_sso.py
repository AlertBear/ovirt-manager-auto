"""
Test rhevm restapi sso.
"""
__test__ = True

import os
import logging

from rhevmtests.system.generic_ldap import config, common
from art.rhevm_api.tests_lib.low_level import users, mla
from art.unittest_lib import attr, CoreSystemTest as TestCase
from nose.tools import istest


LOGGER = logging.getLogger(__name__)
EXTENSIONS = {}
APACHE_EXTENSIONS = {}
NAME = __name__
NAME = NAME[NAME.rfind('.') + 1:]
KRB5_CONF = 'krb5.conf'
KEYTAB = '/etc/http.keytab'
APACHE_FIXTURES = 'apache'
APACHE_CONF = 'z-ovirt-sso.conf'


def setup_module():
    fqdn = config.ENGINE_HOST.fqdn
    add_principal = 'add_principal -randkey HTTP/%s' % fqdn
    add_keytab = 'ktadd -keytab %s HTTP/%s' % (KEYTAB, fqdn)

    with config.ENGINE_HOST.executor().session() as engine:
        engine.run_cmd(['yum', 'install', '-y', config.KRB_MODULE])
        with config.OPENLDAP_HOST.executor().session() as openldap:
            openldap.run_cmd(['kadmin.local', '-q', add_principal])
            openldap.run_cmd(['kadmin.local', '-q', add_keytab])
            with openldap.open_file(KEYTAB, 'rb') as ldap_kt:
                with engine.open_file(KEYTAB, 'wb') as engine_kt:
                    engine_kt.write(ldap_kt.read())
                    LOGGER.info('%s was created.' % KEYTAB)
            openldap.run_cmd(['rm', '-f', KEYTAB])

    common.prepareExtensions(NAME, config.ENGINE_EXTENSIONS_DIR, EXTENSIONS,
                             chown='ovirt', clean=False)
    users.addUser(True, user_name=config.SSO_USER,
                  domain=config.OPENLDAP_SSO['authz_name'])
    mla.addClusterPermissionsToUser(True, config.SSO_USER,
                                    config.DEFAULT_CLUSTER_NAME,
                                    domain=config.OPENLDAP_SSO['authz_name'])
    common.prepareExtensions(APACHE_FIXTURES, config.APACHE_EXTENSIONS,
                             APACHE_EXTENSIONS, clean=False,
                             service=config.APACHE_SERVICE)


def teardown_module():
    fqdn = config.ENGINE_HOST.fqdn
    delete_principal = 'delete_principal -force HTTP/%s' % fqdn
    config.OPENLDAP_HOST.executor().run_cmd(
        ['kadmin.local', '-q', delete_principal])
    with config.ENGINE_HOST.executor().session() as ss:
        ss.run_cmd(['yum', 'remove', '-y', config.KRB_MODULE])
        ss.run_cmd(['rm', '-f', KEYTAB])
    common.cleanExtDirectory(config.APACHE_EXTENSIONS, [APACHE_CONF])
    config.ENGINE_HOST.service(config.APACHE_SERVICE).restart()
    common.loginAsAdmin()
    users.removeUser(True, config.SSO_USER, config.OPENLDAP_SSO['authz_name'])
    common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)


@attr(tier=1)
class SSOLogin(TestCase):
    """
    Test sso login.
    """
    __test__ = True

    conf = config.OPENLDAP_SSO
    cookie_file = '/tmp/cookiejar.txt'
    USER = config.SSO_USER
    PASSWORD = config.SSO_PASSWORD
    executor = config.ENGINE_HOST.executor()

    @classmethod
    def teardown_class(cls):
        with cls.executor.session() as ss:
            ss.run_cmd(['kdestroy'])
            ss.run_cmd(['rm', '-f', cls.cookie_file])

    @istest
    @common.check(EXTENSIONS)
    def sso_login(self):
        """  Test sso login to REST API """
        krb_conf = os.path.join(config.ENGINE_EXTENSIONS_DIR, KRB5_CONF)
        # Note that I can't separate this to more commands as it's forgotten
        login = ['export', 'KRB5_CONFIG=%s' % krb_conf, '&&',
                 'echo', config.SSO_PASSWORD, '|', 'kinit', self.USER, '&&',
                 'curl', '-v', '-k', '--negotiate', '-u', ':', '-b',
                 self.cookie_file, '-c', self.cookie_file, config.ENGINE_URL]

        with self.executor.session() as ss:
            login_ret = ss.run_cmd(login)
            assert not login_ret[0], login_ret[1]
            LOGGER.info(login_ret[2])
