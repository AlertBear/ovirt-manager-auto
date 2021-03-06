"""
Test possible configuration option of properties file.
"""

import logging
import pytest

from art.rhevm_api.tests_lib.low_level import mla
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow

from rhevmtests.coresystem.aaa.ldap import common, config

logger = logging.getLogger(__name__)
DOMAIN_NAMES = []


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    testflow.setup("Setting up module %s", __name__)
    global DOMAIN_NAMES
    DOMAIN_NAMES = [
        domain.get_name() for domain in mla.domUtil.get(abs_link=False)
    ]
    logger.info('Enabled domains are:\n%s', '\n'.join(DOMAIN_NAMES))


class Configuration(TestCase):
    def _isExtensionAvailable(self, extName):
        testflow.step("Checking for existence of %s.", extName)
        return extName in DOMAIN_NAMES


@tier2
class TestWrongConfiguration(Configuration):
    """
    Test if wrong configuration is ignored.
    """
    conf = config.WRONG_EXTENSION

    @polarion('RHEVM3-12860')
    @common.check(config.EXTENSIONS)
    def test_wrongConfiguration(self):
        """ wrong configuration """
        testflow.step(
            "Checking if extension %s is available", self.conf['authz_name']
        )
        assert not self._isExtensionAvailable(self.conf['authz_name'])


@tier2
class TestDisabledConfiguration(Configuration):
    """
    Test if disabled configuration is ignored.
    """
    conf = config.DISABLED_EXTENSION

    @polarion('RHEVM3-12859')
    @common.check(config.EXTENSIONS)
    def test_disabledConfiguration(self):
        """ disabled configuration """
        testflow.step(
            "Checking if extension %s is available", self.conf['authz_name']
        )
        assert not self._isExtensionAvailable(self.conf['authz_name'])
