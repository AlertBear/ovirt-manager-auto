'''
Sanity testing of upgrade.
'''

import logging

from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.unittest_lib import BaseTestCase as TestCase

from rhevmtests.system.upgradeSanity import config

LOGGER = logging.getLogger(__name__)


def setup_module():
    """
    Build datacenter
    """
    params = config.PARAMETERS
    build_setup(config=params, storage=params,
                storage_type=params.get('storage_type'),
                basename=params.get('basename'))
    LOGGER.debug("setup_module: adding hosts and so on")


class UpgradeSanityInstrumentation(TestCase):
    """ Install and test the setup """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        LOGGER.debug("setUpClass: adding VMs")

    def run_tests(self):
        """ Test Case placeholder """
        LOGGER.debug("placeholder test case")

    def test_pre_upgrade(self):
        """ Run tests before the upgrade """
        LOGGER.debug("pre-upgrade")
        self.run_tests()
