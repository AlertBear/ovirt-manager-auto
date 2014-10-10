import logging
from rhevmtests.system.generic_ldap import config


LOGGER = logging.getLogger(__name__)


def setup_module():
    with config.ENGINE_HOST.executor().session() as ss:
        ss.run_cmd(['yum', 'install', '-y', config.EXTENSIONS_PKG])
        LOGGER.info("Package %s was successfully installed.",
                    config.EXTENSIONS_PKG)


def teardown_module():
    with config.ENGINE_HOST.executor().session() as ss:
        ss.run_cmd(['yum', 'remove', '-y', config.EXTENSIONS_PKG])
        LOGGER.info("Package %s was successfully removed.",
                    config.EXTENSIONS_PKG)
