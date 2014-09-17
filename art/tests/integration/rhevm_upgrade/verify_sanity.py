'''
Sanity testing of upgrade.
'''

import logging

from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import removeVm, checkVMConnectivity
from art.test_handler.exceptions import VMException
from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import attr

from rhevm_upgrade import config

LOGGER = logging.getLogger(__name__)


def teardown_module():
    """
    Clean datacenter
    """
    cleanDataCenter(True, config.DC_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)
    LOGGER.debug("tearDownClass: cleaned the DC")


@attr(tier=1)
class UpgradeSanityVerification(TestCase):
    """ Basic test """
    __test__ = True

    @classmethod
    def tearDownClass(cls):
        if not removeVm(positive=True, vm=config.VM_NAME, stopVM='true'):
            raise VMException("Cannot remove vm %s" % config.VM_NAME)
        LOGGER.info("Successfully removed %s.", config.VM_NAME)

    def test_post_upgrade(self):
        """ Run tests after the upgrade """
        LOGGER.debug("post-upgrade tests")
        assert checkVMConnectivity(True, config.VM_NAME, 'rhel',
                                   nic=config.NIC_NAME,
                                   user=config.VM_LINUX_USER,
                                   password=config.VMS_LINUX_PW)
