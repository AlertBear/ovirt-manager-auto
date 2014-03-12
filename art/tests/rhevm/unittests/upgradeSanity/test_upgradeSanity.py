'''
Sanity testing of upgrade.
1 DC, 1 Cluster, 1 host, 1 SD and 1 VM will be created.
Test will create and run VM on 3.2 setup then upgrade to 3.3 and try the same.
'''

import config as cfg
import logging
from art.rhevm_api.tests_lib.low_level import vms
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest

LOGGER = logging.getLogger(__name__)


class UpgradeSanityTest(TestCase):
    """ Basic run vm test """
    __test__ = True

    def setUp(self):
        LOGGER.debug("class UpgradeSanityTest setUp")
        assert vms.createVm(True, cfg.VM_NAME, '',
                            cluster=cfg.CLUSTER_NAME,
                            storageDomainName=cfg.STORAGE_NAME, size=cfg.GB,
                            network=config.MGMT_BRIDGE)

    def tearDown(self):
        LOGGER.debug("class UpgradeSanityTest tearDown")
        assert vms.removeVm(True, cfg.VM_NAME, stopVM='true', wait=True)

    @istest
    def run_vm(self):
        """ Run vm """
        LOGGER.debug("class UpgradeSanityTest run_vm")
        self.assertTrue(vms.startVm(True, cfg.VM_NAME))
