"""
Test possible configuration option of properties file.
"""

import logging
import pytest

from art.rhevm_api.tests_lib.low_level import mla
from art.test_handler.tools import polarion
from art.unittest_lib import attr, CoreSystemTest as TestCase, testflow

from rhevmtests.system.aaa.ldap import common, config

__test__ = True

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
    __test__ = False

    def _isExtensionAvailable(self, extName):
        testflow.step("Checking for existence of %s.", extName)
        return extName in DOMAIN_NAMES


@attr(tier=2)
class WrongConfiguration(Configuration):
    """
    Test if wrong configuration is ignored.
    """
    __test__ = True
    conf = config.WRONG_EXTENSION

    @polarion('RHEVM3-12860')
    @common.check(config.EXTENSIONS)
    def test_wrongConfiguration(self):
        """ wrong configuration """
        testflow.step(
            "Checking if extension %s is available", self.conf['authz_name']
        )
        assert not self._isExtensionAvailable(self.conf['authz_name'])


@attr(tier=2)
class DisabledConfiguration(Configuration):
    """
    Test if disabled configuration is ignored.
    """
    __test__ = True
    conf = config.DISABLED_EXTENSION

    @polarion('RHEVM3-12859')
    @common.check(config.EXTENSIONS)
    def test_disabledConfiguration(self):
        """ disabled configuration """
        testflow.step(
            "Checking if extension %s is available", self.conf['authz_name']
        )
        assert not self._isExtensionAvailable(self.conf['authz_name'])
