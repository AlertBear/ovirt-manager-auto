import logging
import os

from rhevmtests.system.aaa.ldap import config, common


LOGGER = logging.getLogger(__name__)


def setup_package():
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


def teardown_package():
    common.removeTrustStore(config.TRUSTSTORE)
    common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)
    common.cleanExtDirectory(config.AAA_DIR)
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)
