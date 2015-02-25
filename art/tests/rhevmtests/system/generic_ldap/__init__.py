import logging
import os

from rhevmtests.system.generic_ldap import config, common


LOGGER = logging.getLogger(__name__)


def setup_module():
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
    common.createTrustStore(
        config.ADW2K12_DOMAINS, config.TRUSTSTORE, config.TRUSTSTORE_PASSWORD
    )
    common.enableExtensions(config.OVIRT_SERVICE, config.ENGINE_HOST)


def teardown_module():
    common.removeTrustStore(config.TRUSTSTORE)
    common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)
