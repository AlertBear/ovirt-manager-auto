'''
Test possible configuration option of properties file.
'''


__test__ = True

import logging

from rhevmtests.system.generic_ldap import config, common
from art.rhevm_api.tests_lib.low_level import mla
from art.unittest_lib import CoreSystemTest as TestCase
from nose.tools import istest
from art.unittest_lib import attr

LOGGER = logging.getLogger(__name__)
EXTENSIONS = {}
NAME = __name__
NAME = NAME[NAME.rfind('.') + 1:]


def setup_module():
    common.prepareExtensions(NAME, config.EXTENSIONS_DIRECTORY, EXTENSIONS)


def teardown_module():
    common.cleanExtDirectory(config.EXTENSIONS_DIRECTORY)


@attr(tier=1)
class WrongConfiguration(TestCase):
    '''
    Test if wrong configuration is ignored.
    '''
    __test__ = True
    conf = config.WRONG_EXTENSION

    def setUp(self):
        self.domains = mla.domUtil.get(absLink=False)

    @istest
    @common.check(EXTENSIONS)
    def wrongConfiguration(self):
        ''' wrong configuration '''
        LOGGER.info('Checking for existence of %s.', self.conf['authz_name'])
        res = filter(lambda d: d.get_name() == self.conf['authz_name'],
                     self.domains)
        self.assertEqual(len(res), 0, 'Configuration %s was added' % self.conf)
        LOGGER.info('Enabled domains are: %s',
                    [d.get_name() for d in self.domains])


@attr(tier=1)
class DisabledConfiguration(TestCase):
    '''
    Test if disabled configuration is skipped.
    '''
    __test__ = True
    conf = config.DISABLED_EXTENSION

    def setUp(self):
        self.domains = mla.domUtil.get(absLink=False)

    @istest
    @common.check(EXTENSIONS)
    def disabledConfiguration(self):
        ''' disabled configuration '''
        LOGGER.info('Checking for existence of %s.', self.conf['authz_name'])
        res = filter(lambda d: d.get_name() == self.conf['authz_name'],
                     self.domains)
        self.assertEqual(len(res), 0, 'Configuration %s was added' % self.conf)
        LOGGER.info('Enabled domains are: %s',
                    [d.get_name() for d in self.domains])
