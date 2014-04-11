'''
Sanity testing of upgrade.
'''

import logging

from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.unittest_lib import BaseTestCase as TestCase

import config as cfg

LOGGER = logging.getLogger(__name__)


def teardown_module():
    """
    Clean datacenter
    """
    cleanDataCenter(True, cfg.DC_NAME, vdc=cfg.VDC,
                    vdc_password=cfg.VDC_PASSWORD)
    LOGGER.debug("tearDownClass: cleaned the DC")


class UpgradeSanityVerification(TestCase):
    """ Basic test """
    __test__ = True

    @classmethod
    def tearDownClass(cls):
        LOGGER.debug("tearDownClass: stop VMs")

    def run_tests(self):
        """ Test Case placeholder """
        LOGGER.debug("placeholder test case")

    def test_post_upgrade(self):
        """ Run tests after the upgrade """
        LOGGER.debug("post-upgrade")
        self.run_tests()
