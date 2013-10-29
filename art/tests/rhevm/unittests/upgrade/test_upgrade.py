import config as cfg
import logging
from art.rhevm_api.tests_lib.low_level import vms
from unittest import TestCase
from nose.tools import istest


LOGGER = logging.getLogger(__name__)


class UpgradeTest(TestCase):
    """ Basic run vm test """
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, cfg.VM_NAME, '',
                            cluster=cfg.CLUSTER_NAME,
                            storageDomainName=cfg.STORAGE_NAME, size=cfg.GB)

    def tearDown(self):
        assert vms.removeVm(True, cfg.VM_NAME, stopVM='true')
        import time
        time.sleep(5)

    @istest
    def run_vm(self):
        """ Run vm """
        self.assertTrue(vms.startVm(True, cfg.VM_NAME))
