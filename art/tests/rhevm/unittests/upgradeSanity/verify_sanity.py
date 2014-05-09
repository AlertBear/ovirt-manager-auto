'''
Sanity testing of upgrade.
'''

import logging

from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import removeVm, checkVMConnectivity
from art.test_handler.exceptions import VMException
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
        if not removeVm(positive=True, vm=cfg.VM_NAME, stopVM='true'):
            raise VMException("Cannot remove vm %s" % cfg.VM_NAME)
        LOGGER.info("Successfully removed %s.", cfg.VM_NAME)

    def test_post_upgrade(self):
        """ Run tests after the upgrade """
        LOGGER.debug("post-upgrade tests")
        assert checkVMConnectivity(True, cfg.VM_NAME, 'rhel', nic=cfg.NIC_NAME,
                                   user=cfg.VM_LINUX_USER,
                                   password=cfg.VM_LINUX_PASSWORD)
