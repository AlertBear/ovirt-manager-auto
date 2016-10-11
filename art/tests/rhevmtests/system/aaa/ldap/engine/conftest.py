import logging
import os
import pytest

from art.unittest_lib import testflow

from rhevmtests.system.aaa.ldap import config, common


logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def setup_session(request):
    def finalize():
        testflow.teardown("Tearing down module %s", __name__)

        testflow.teardown("Removing trust store")
        common.removeTrustStore(config.TRUSTSTORE)

        testflow.teardown(
            "Cleaning %s directory", config.ENGINE_EXTENSIONS_DIR
        )
        common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)

        testflow.teardown("Cleaning %s directory", config.AAA_DIR)
        common.cleanExtDirectory(config.AAA_DIR)

        testflow.teardown("Restarting engine")
        common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)
    test_dir = os.path.dirname(os.path.abspath(__file__))
    tests = set([
        f[:f.rfind('.')] for f in os.listdir(test_dir) if f.startswith('test_')
    ])
    for name in tests:
        common.prepareExtensions(
            name,
            config.ENGINE_EXTENSIONS_DIR,
            config.EXTENSIONS,
            chown='ovirt',
            clean=False,
            enable=False,
        )
    common.import_certificate_to_truststore(
        host=config.ENGINE_HOST,
        cert_path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../fixtures/certs',
            config.CERT_NAME,
        ),
        truststore=config.TRUSTSTORE,
        password=config.TRUSTSTORE_PASSWORD,
    )
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)
    common.loginAsAdmin()
