"""
Scheduler - Even Vm Count Distribution test initialization
"""

import os
import logging
from rhevmtests.sla import config

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api

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
        logger.info("Create five new vms")
        for vm in config.VM_NAME:
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
                "Selecting host as SPM failed"
            )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Remove all vms from cluster %s", config.CLUSTER_NAME[0])
    if not vm_api.remove_all_vms_from_cluster(
        config.CLUSTER_NAME[0],
        skip=config.VM_NAME
    ):
        raise errors.VMException("Failed to remove vms")
    if os.environ.get("JENKINS_URL") and not config.GOLDEN_ENV:
        if not dc_api.clean_datacenter(
                True, config.DC_NAME[0],
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise errors.DataCenterException("Clean up environment failed")
