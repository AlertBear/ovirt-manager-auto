'''
Sanity testing of upgrade.
'''

import config as cfg
import logging
from art.rhevm_api.tests_lib.low_level import vms
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest

LOGGER = logging.getLogger(__name__)


class UpgradeSanityTest(TestCase):
    """ Basic test """
    __test__ = True

    def setUp(self):
        LOGGER.debug("class UpgradeSanityTest setUp")

    def tearDown(self):
        LOGGER.debug("class UpgradeSanityTest tearDown")

    @istest
    def run_test(self):
        """ Test Case placeholder """
        LOGGER.debug("class UpgradeSanityTest test case")
