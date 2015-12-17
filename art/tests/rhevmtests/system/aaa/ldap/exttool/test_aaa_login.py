"""
This module test 'Extension tester tool'(ovirt-engine-extensions-tool) and
it's aaa module with login action.

polarion:
    RHEVM3/wiki/System/Extension tester tool
"""
import logging
import os

from art.rhevm_api.utils.enginecli import EngineCLI
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, CoreSystemTest as TestCase

from rhevmtests.system.aaa.ldap import config, common

logger = logging.getLogger(__name__)
CERT_BASE = '/tmp/my_crt'
TEST_USER = 'user1'
TEST_USER_PASSWORD = 'pass:123456'


def setup_module():
    dir_name = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '../answerfiles',
    )
    for answerfile in os.listdir(dir_name):
        assert common.setup_ldap(
            host=config.ENGINE_HOST,
            conf_file=os.path.join(dir_name, answerfile),
        )


def teardown_module():
    common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)
    common.cleanExtDirectory(config.AAA_DIR)


@attr(tier=1)
class ExttoolAAALogin(TestCase):
    """ Test login action with generic provider """
    __test__ = False
    profile = None
    extended_properties = {}

    @classmethod
    def setup_class(cls):
        cls.executor = config.ENGINE_HOST.executor()
        authz = '/etc/ovirt-engine/extensions.d/%s-authz.properties' % (
            cls.profile
        )
        authn = '/etc/ovirt-engine/extensions.d/%s-authn.properties' % (
            cls.profile
        )
        cls.cli = EngineCLI(
            config.TOOL,
            cls.executor.session(),
            '--log-level=WARNING',
            '--extension-file=%s' % authn,
            '--extension-file=%s' % authz,
        ).setup_module(
            module='aaa',
        )

        cls.ext_file = '/etc/ovirt-engine/aaa/%s.properties' % cls.profile
        with cls.executor.session() as ss:
            with ss.open_file(cls.ext_file, 'r') as f:
                for line in f:
                    if line.find('=') > 0:
                        key, val = line.split('=', 1)
                    else:
                        key = line
                        val = ''
                    cls.extended_properties[key.strip()] = val.strip()

            assert not ss.run_cmd(
                ['mv', cls.ext_file, '%s.tmp' % cls.ext_file]
            )[0], "Failed to backup '%s'" % cls.ext_file

            if cls.cert_url:
                assert not ss.run_cmd(
                    ['wget', cls.cert_url, '-O', '%s.pem' % CERT_BASE]
                )[0], "Failed to download cert '%s'" % cls.cert_url
                assert not common.importCertificateToTrustStore(
                    session=ss,
                    filename='%s.pem' % CERT_BASE,
                    truststore='%s.jks' % CERT_BASE,
                    password='changeit',
                )[0], "Failed to create trustore '%s.jks'" % CERT_BASE

    @classmethod
    def teardown_class(cls):
        with cls.executor.session() as ss:
            ss.run_cmd(['mv', '%s.tmp' % cls.ext_file, cls.ext_file])
            ss.run_cmd(['rm', '-f', '%s.jks' % CERT_BASE])
            ss.run_cmd(['rm', '-f', '%s.pem' % CERT_BASE])

    def login(self, user_name=TEST_USER, password=TEST_USER_PASSWORD):
        self.assertTrue(
            self.cli.run(
                'login-user',
                user_name=user_name,
                profile=self.profile,
                password=password,
            )[0],
            "Failed to run login-user action"
        )


class ExttoolAAALoginAD(ExttoolAAALogin):
    """ Test login action with Active Directory """
    __test__ = True
    profile = 'ad-w2k12r2'
    cert_url = 'http://ad-w2k12r2.rhev.lab.eng.brq.redhat.com/w2k12r2.cer'

    @polarion('RHEVM3-14526')
    @common.extend(
        properties={
            'pool.default.ssl.startTLS': 'true',
            'pool.default.ssl.truststore.file': '%s.jks' % CERT_BASE
        }
    )
    def test_login_startTLS(self):
        """ test login """
        self.login(password='pass:Heslo123')

    @polarion('RHEVM3-14527')
    @common.extend(
        properties={
            'pool.default.ssl.startTLS': 'true',
            'pool.default.ssl.insecure': 'true',
        }
    )
    def test_login_startTLS_insecure(self):
        """ test login startl insecure """
        self.login(password='pass:Heslo123')


class ExttoolAAALoginOpenLDAP(ExttoolAAALogin):
    """ Test login action with OpenLDAP """
    __test__ = True
    profile = 'openldap'
    cert_url = 'http://brq-openldap.rhev.lab.eng.brq.redhat.com/cacert.pem'

    @polarion('RHEVM3-14525')
    @common.extend(
        properties={
            'pool.default.ssl.startTLS': 'true',
            'pool.default.ssl.truststore.file': '%s.jks' % CERT_BASE
        }
    )
    def test_login_startTLS(self):
        """ test login startl """
        self.login()

    @polarion('RHEVM3-14528')
    @common.extend(
        properties={
            'pool.default.ssl.startTLS': 'true',
            'pool.default.ssl.insecure': 'true',
        }
    )
    def test_login_startTLS_insecure(self):
        """ test login startl insecure """
        self.login()
