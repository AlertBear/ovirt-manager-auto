"""
This module replaces auto_devices plugin from ART.

Simply it implements hooks pytest_art_ensure_resources &
pytest_art_release_resources.
"""
import re
import os
import logging
import art.test_handler.settings as settings
from _pytest_art import storagewrapper


CONF_SECTION = "RUN"
ENABLED = "auto_devices"
CLEANUP = "auto_devices_cleanup"


logger = logging.getLogger("pytest.art.autodevices")

__all__ = [
    'pytest_artconf_ready',
]


class AutoDevices(object):
    """
    Create / destroy storages for tests and update config file.
    """
    def __init__(self):
        super(AutoDevices, self).__init__()
        self.su = storagewrapper.StorageUtils(
            settings.ART_CONFIG,
            os.getenv('STORAGE_CONF_FILE'),
        )
        self.passed = True

    @property
    def cleanup(self):
        clean = settings.ART_CONFIG.get(CONF_SECTION).get(CLEANUP)
        if re.match('all|yes', clean):
            return True
        elif clean == 'no':
            return False
        else:
            return clean == str(self.passed).lower()

    def pytest_art_ensure_resources(self, config):
        try:
            # Setup storages
            self.su.storageSetup()
        except Exception as ex:
            logger.error(str(ex), exc_info=True)
            raise
        # Fill up config file with storages
        self.su.updateConfFile()

    def pytest_art_release_resources(self, config):
        if self.cleanup:
            logger.info("Cleaning storages.")
            self.su.storageCleanup()

    def pytest_collectreport(self, report):
        self.passed &= report.passed


def pytest_artconf_ready(config):
    """
    Register AutoDevices plugin.
    """
    if settings.ART_CONFIG.get(CONF_SECTION).get(ENABLED):
        config.pluginmanager.register(AutoDevices())
