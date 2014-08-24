import logging
from utilities import machine
from rhevmtests.system.generic_ldap import config


LOGGER = logging.getLogger(__name__)


def setup_module():
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    assert machineObj.yum(config.EXTENSIONS_PKG, 'install')
    LOGGER.info("Package %s was successfully installed.",
                config.EXTENSIONS_PKG)


def teardown_module():
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    assert machineObj.yum(config.EXTENSIONS_PKG, 'remove')
    LOGGER.info("Package %s was successfully removed.",
                config.EXTENSIONS_PKG)
