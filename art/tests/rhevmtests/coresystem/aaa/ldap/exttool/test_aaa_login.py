"""
This module test 'Extension tester tool'(ovirt-engine-extensions-tool) and
it's aaa module with login action.

polarion:
    RHEVM3/wiki/System/Extension tester tool
"""
import logging
import pytest
from os import path, listdir

from rhevmtests.coresystem.helpers import EngineCLI
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow

from rhevmtests.coresystem.aaa.ldap import config, common

CERT_BASE = '/tmp/my_crt'
TEST_USER = 'user1'
TEST_USER_PASSWORD = 'pass:123456'

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Cleaning extension directories")
        common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)
        common.cleanExtDirectory(config.AAA_DIR)

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)
    dir_name = path.join(
        path.dirname(path.abspath(__file__)),
        '../answerfiles',
    )
    testflow.setup("Setting up LDAP")
    for answerfile in listdir(dir_name):
        assert common.setup_ldap(
            host=config.ENGINE_HOST,
            conf_file=path.join(dir_name, answerfile),
        )


@tier1
class ExttoolAAALogin(TestCase):
    """ Test login action with generic provider """
    profile = None
    extended_properties = {}

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)
            with cls.executor.session() as ss:
                ss.run_cmd(['mv', '%s.tmp' % cls.ext_file, cls.ext_file])
                ss.run_cmd(['rm', '-f', '%s.jks' % CERT_BASE])
                ss.run_cmd(['rm', '-f', '%s.pem' % CERT_BASE])

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)
        cls.executor = config.ENGINE_HOST.executor()
        authz = '/etc/ovirt-engine/extensions.d/%s-authz.properties' % (
            cls.profile
        )
        authn = '/etc/ovirt-engine/extensions.d/%s-authn.properties' % (
            cls.profile
        )
        testflow.setup("Setting up AAA module")
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
            testflow.setup(
                "Getting properties from extension file %s", cls.ext_file
            )
            with ss.open_file(cls.ext_file, 'r') as f:
                for line in f:
                    if line.find('=') > 0:
                        key, val = line.split('=', 1)
                    else:
                        key = line
                        val = ''
                    cls.extended_properties[key.strip()] = val.strip()

            testflow.setup("Backing up")
            assert not ss.run_cmd(
                ['mv', cls.ext_file, '%s.tmp' % cls.ext_file]
            )[0], "Failed to backup '%s'" % cls.ext_file

            testflow.setup("Downloading cert files")
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

    def login(self, user_name=TEST_USER, password=TEST_USER_PASSWORD):
        testflow.step("Login as user %s", user_name)
        assert self.cli.run(
            'login-user',
            user_name=user_name,
            profile=self.profile,
            password=password,
        )[0], "Failed to run login-user action"


class TestExttoolAAALoginAD(ExttoolAAALogin):
    """ Test login action with Active Directory """
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
        testflow.step("Login with startTLS")
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
        testflow.step("Login with startTLS insecure")
        self.login(password='pass:Heslo123')


class TestExttoolAAALoginOpenLDAP(ExttoolAAALogin):
    """ Test login action with OpenLDAP """
    profile = 'openldap'
    cert_url = 'http://brq-openldap.rhev.lab.eng.brq.redhat.com/cacert.pem'
    bz = {'1313516': {}}

    @polarion('RHEVM3-14525')
    @common.extend(
        properties={
            'pool.default.ssl.startTLS': 'true',
            'pool.default.ssl.truststore.file': '%s.jks' % CERT_BASE
        }
    )
    def test_login_startTLS(self):
        """ test login startl """
        testflow.step("Login with startTLS")
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
        testflow.step("Login with startTLS insecure")
        self.login()
