'''
Test possible configuration option of properties file.
'''
__test__ = True

import logging

from rhevmtests.system.generic_ldap import common, config
from art.rhevm_api.tests_lib.low_level import mla
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, CoreSystemTest as TestCase


LOGGER = logging.getLogger(__name__)
DOMAIN_NAMES = []


def setup_module():
    global DOMAIN_NAMES
    DOMAIN_NAMES = [
        domain.get_name() for domain in mla.domUtil.get(absLink=False)
    ]
    LOGGER.info('Enabled domains are:\n%s', '\n'.join(DOMAIN_NAMES))


class Configuration(TestCase):
    __test__ = False

    def _isExtensionAvailable(self, extName):
        LOGGER.info('Checking for existence of %s.', extName)
        return extName in DOMAIN_NAMES


@attr(tier=1)
class WrongConfiguration(Configuration):
    '''
    Test if wrong configuration is ignored.
    '''
    __test__ = True
    conf = config.WRONG_EXTENSION

    @polarion('RHEVM3-12860')
    @common.check(config.EXTENSIONS)
    def test_wrongConfiguration(self):
        ''' wrong configuration '''
        self.assertFalse(self._isExtensionAvailable(self.conf['authz_name']))


@attr(tier=1)
class DisabledConfiguration(Configuration):
    '''
    Test if disabled configuration is ignored.
    '''
    __test__ = True
    conf = config.DISABLED_EXTENSION

    @polarion('RHEVM3-12859')
    @common.check(config.EXTENSIONS)
    def test_disabledConfiguration(self):
        ''' disabled configuration '''
        self.assertFalse(self._isExtensionAvailable(self.conf['authz_name']))
