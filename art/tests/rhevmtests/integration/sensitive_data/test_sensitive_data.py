"""
Testing for sensitive data leakage
"""

from art.unittest_lib import tier1, testflow
from art.unittest_lib import CoreSystemTest as TestCase
from os import path

import config
import logging
import pytest

logger = logging.getLogger(__name__)

PASSWORDS = {}
PRIVATE_KEYS = {}


@pytest.fixture(scope="module", autouse=True)
def setup_module():
    testflow.setup("Collecting known passwords from config files")
    for _file, field in config.CONFS.iteritems():
        _config = path.join(config.CONF_DIR, _file)

        cfg = config.ENGINE._read_config(_config)
        PASSWORDS[field] = cfg[field]

    testflow.setup("Collecting private keys from cert files")
    _files = config.ENGINE_HOST.fs.listdir(config.PKI_PATH)
    for _file in _files:
        stream = config.ENGINE_HOST.fs.read_file(
                    path.join(config.PKI_PATH, _file)
                )
        lines = stream.split('\n')
        if config.PRIVATE_KEY_HEADER in lines:
            start = lines.index(config.PRIVATE_KEY_HEADER)
            PRIVATE_KEYS[_file] = lines[start + 1]


class TestSensitiveDataLeak(TestCase):
    """Look for possibly leaked passwords as plain text"""

    def does_it_leak(self, keys):
        """
        Look for plain text keys on log files
        Args:
            keys (dict): dictionary of key name/file and it's secret

        Returns:
            bool: True if an occurrence of the key is found inside the logs
        """

        leaking = False
        with config.ENGINE_HOST.executor().session() as session:
            for _key, _secret in keys.iteritems():
                testflow.step("Looking for occurrences of %s", _key)
                _cmd = ['grep', '-irn', _secret, config.LOGS_PATH]
                rc, out, err = session.run_cmd(_cmd)
                if not rc:
                    logger.error("Found plain text occurrence of %s", _key)
                    leaking = leaking or True

        return leaking

    @tier1
    def test_sensitive_data_leak_passwords(self):
        """
        Test for plain text passwords on log files
        """
        assert not self.does_it_leak(PASSWORDS)

    @tier1
    def test_sensitive_data_leak_private_keys(self):
        """
        Test for plain text private keys on log files
        """
        assert not self.does_it_leak(PRIVATE_KEYS)
