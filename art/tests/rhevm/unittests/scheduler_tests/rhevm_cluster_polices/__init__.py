"""
Scheduler - Rhevm Cluster Policies test initialization
"""

import logging

import art.test_handler.exceptions as Errors
import art.rhevm_api.tests_lib.low_level.vms as Vm
import art.rhevm_api.tests_lib.high_level.datacenters as Datacenter
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter

logger = logging.getLogger("rhevm_cluster_polices")

#################################################

DISK_SIZE = 3 * 1024 * 1024 * 1024


def setup_package():
    """
    Prepare environment for Rhevm Cluster Policies Test
    """
    import config
    logger.info("Building setup...")
    if not Datacenter.build_setup(config.PARAMETERS, config.PARAMETERS,
                                  config.STORAGE_TYPE, config.TEST_NAME):
        raise Errors.DataCenterException("Setup environment failed")
    logger.info("Create new vm")
    if not Vm.createVm(positive=True, vmName=config.vm_for_migration,
                       vmDescription="Test VM",
                       cluster=config.cluster_name,
                       storageDomainName=config.data_name[0],
                       size=DISK_SIZE, nic='nic1',
                       placement_host=config.load_host_1):
        raise Errors.VMException("Cannot create vm %s" %
                                 config.vm_for_migration)


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Teardown...")
    if not cleanDataCenter(True, config.dc_name, vdc=config.VDC,
                           vdc_password=config.VDC_PASSWORD):
        raise Errors.DataCenterException("Clean up environment failed")
