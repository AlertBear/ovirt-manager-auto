"""
Scheduler - Rhevm Cluster Policies test initialization
"""

import os
import logging

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from rhevmtests.scheduler_tests.rhevm_cluster_polices import config

logger = logging.getLogger(__name__)

#################################################

DISK_SIZE = 3 * 1024 * 1024 * 1024


def setup_package():
    """
    Prepare environment for Rhevm Cluster Policies Test
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                                  config.STORAGE_TYPE, config.TEST_NAME):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Select host %s as SPM", config.LOAD_HOST_2)
        if not host_api.checkHostSpmStatus(True, config.LOAD_HOST_2):
            if not host_api.select_host_as_spm(True, config.LOAD_HOST_2,
                                               config.DC_NAME[0]):
                raise errors.DataCenterException("Selecting host %s "
                                                 "as SPM failed"
                                                 % config.LOAD_HOST_2)
        logger.info("Create new vms")
        vm_dic = {config.VM_FOR_MIGRATION: config.LOAD_HOST_0,
                  config.SUPPORT_VM_1: config.LOAD_HOST_1,
                  config.SUPPORT_VM_2: config.LOAD_HOST_2}
        for vm, placement_host in vm_dic.iteritems():
            if not vm_api.createVm(positive=True, vmName=vm,
                                   vmDescription="Test VM",
                                   cluster=config.CLUSTER_NAME[0],
                                   storageDomainName=config.STORAGE_NAME[0],
                                   size=DISK_SIZE, nic='nic1',
                                   placement_host=placement_host,
                                   network=config.MGMT_BRIDGE):
                raise errors.VMException("Cannot create vm %s" % vm)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        if not cleanDataCenter(True, config.DC_NAME[0], vdc=config.VDC_HOST,
                               vdc_password=config.VDC_ROOT_PASSWORD):
            raise errors.DataCenterException("Clean up environment failed")
