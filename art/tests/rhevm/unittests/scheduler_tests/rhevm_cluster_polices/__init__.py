"""
Scheduler - Rhevm Cluster Policies test initialization
"""

import logging

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api
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
    if not dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                              config.STORAGE_TYPE, config.TEST_NAME):
        raise errors.DataCenterException("Setup environment failed")
    logger.info("Select host %s as SPM", config.load_host_3)
    if not host_api.checkHostSpmStatus(True, config.load_host_3):
        if not host_api.select_host_as_spm(True, config.load_host_3,
                                           config.dc_name):
            raise errors.DataCenterException("Selecting host %s as SPM failed"
                                             % config.load_host_3)
    logger.info("Create new vms")
    vm_dic = {config.vm_for_migration: config.load_host_1,
              config.support_vm_1: config.load_host_2,
              config.support_vm_2: config.load_host_3}
    for vm, placement_host in vm_dic.iteritems():
        if not vm_api.createVm(positive=True, vmName=vm,
                               vmDescription="Test VM",
                               cluster=config.cluster_name,
                               storageDomainName=config.data_name[0],
                               size=DISK_SIZE, nic='nic1',
                               placement_host=placement_host,
                               network=config.cluster_network):
            raise errors.VMException("Cannot create vm %s" % vm)


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Teardown...")
    if not cleanDataCenter(True, config.dc_name, vdc=config.VDC,
                           vdc_password=config.VDC_PASSWORD):
        raise errors.DataCenterException("Clean up environment failed")
