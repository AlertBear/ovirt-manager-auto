"""
Scheduler Sanity Test - test initialization
"""

import os
import logging
from rhevmtests.sla import config

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Even Vm Count Distribution Test
    """
    if os.environ.get("JENKINS_URL") and not config.GOLDEN_ENV:
        logger.info("Building setup...")
        if not dc_api.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
        ):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Create three new vms")
        for vm in config.VM_NAME[:3]:
            if not vm_api.createVm(
                True, vm, vmDescription="Test VM",
                cluster=config.CLUSTER_NAME[0],
                storageDomainName=config.STORAGE_NAME[0], size=config.GB,
                nic=config.NIC_NAME[0], network=config.MGMT_BRIDGE
            ):
                raise errors.VMException("Cannot create %s" % vm)
    logger.info("Select host %s as SPM", config.HOSTS[0])
    if not host_api.checkHostSpmStatus(True, config.HOSTS[0]):
        if not host_api.select_host_as_spm(
                True, config.HOSTS[0], config.DC_NAME[0]
        ):
            raise errors.DataCenterException(
                "Selecting host %s as SPM failed" % config.HOSTS[0]
            )
    if config.GOLDEN_ENV:
        logger.info("Deactivate additional host %s", config.HOSTS[2])
        if not host_api.deactivateHost(True, config.HOSTS[2]):
            raise errors.HostException("Failed to deactivate host")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Activate additional host %s", config.HOSTS[2])
        if not host_api.activateHost(True, config.HOSTS[2]):
            raise errors.HostException("Failed to activate host")
        logger.info("Remove all vms from cluster %s", config.CLUSTER_NAME[0])
        if not vm_api.remove_all_vms_from_cluster(
                config.CLUSTER_NAME[0], skip=config.VM_NAME
        ):
            raise errors.VMException("Failed to remove vms")
    if os.environ.get("JENKINS_URL") and not config.GOLDEN_ENV:
        if not cleanDataCenter(
                True, config.DC_NAME[0], vdc=config.VDC_HOST,
                vdc_password=config.VDC_PASSWORD
        ):
            raise errors.DataCenterException("Clean up environment failed")