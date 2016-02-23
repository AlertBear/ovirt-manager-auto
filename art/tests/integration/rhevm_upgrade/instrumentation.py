'''
Sanity testing of upgrade.
'''

import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.unittest_lib import BaseTestCase as TestCase
from art.test_handler.exceptions import StorageDomainException

import config as cfg

LOGGER = logging.getLogger(__name__)


def setup_module():
    """
    Build datacenter
    """
    params = cfg.PARAMETERS
    build_setup(config=params, storage=params,
                storage_type=params.get('storage_type'),
                basename=params.get('basename'))
    LOGGER.debug("setup_module: adding hosts and so on")


class UpgradeSanityInstrumentation(TestCase):
    """ Install and test the setup """
    __test__ = True

    @classmethod
    def setup_class(cls):
        LOGGER.debug("setUpClass: adding VMs")

    def run_tests(self):
        """ create a vm on master storage domain """
        status, masterDomain = ll_sd.findMasterStorageDomain(
            True, cfg.DC_NAME
        )
        if not status:
            raise StorageDomainException('Master storage domain not found.')
        assert ll_vms.createVm(
            True, cfg.VM_NAME, 'desc.',
            cluster=cfg.CLUSTER_NAME,
            size=cfg.DISK_SIZE,
            nic=cfg.NIC_NAME,
            os_type=cfg.OS_TYPE,
            storageDomainName=masterDomain['masterDomain'],
            installation=True,
            useAgent=True,
            image='rhel6.5-agent3.5',
            user=cfg.VM_LINUX_USER,
            password=cfg.VM_LINUX_PASSWORD,
            network=cfg.MGMT_BRIDGE,
        ), "Failed to create vm '%s'" % cfg.VM_NAME

    def test_pre_upgrade(self):
        LOGGER.debug("pre-upgrade tests")
        assert ll_vms.checkVMConnectivity(
            True,
            cfg.VM_NAME,
            cfg.OS_TYPE,
            nic=cfg.NIC_NAME,
            user=cfg.VM_LINUX_USER,
            password=cfg.VM_LINUX_PASSWORD,
        ), "Failed to connect to vm '%s'" % cfg.VM_NAME
