'''
Test possible configuration option of properties file.
'''
__test__ = True

import logging

from rhevmtests.system.generic_ldap import common, config
from art.rhevm_api.tests_lib.low_level import mla
from art.unittest_lib import attr, CoreSystemTest as TestCase
from nose.tools import istest


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

    @istest
    @common.check(config.EXTENSIONS)
    def wrongConfiguration(self):
        ''' wrong configuration '''
        self.assertFalse(self._isExtensionAvailable(self.conf['authz_name']))


@attr(tier=1)
class DisabledConfiguration(Configuration):
    '''
    Test if disabled configuration is ignored.
    '''
    __test__ = True
    conf = config.DISABLED_EXTENSION

    @istest
    @common.check(config.EXTENSIONS)
    def disabledConfiguration(self):
        ''' disabled configuration '''
        self.assertFalse(self._isExtensionAvailable(self.conf['authz_name']))
