"""
Scheduler Sanity Test - Test Initialization
"""
import logging

from rhevmtests.sla import config

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Scheduler Sanity Test
    """
    logger.info("Deactivate additional host %s", config.HOSTS[2])
    if not host_api.deactivateHost(True, config.HOSTS[2]):
        raise errors.HostException("Failed to deactivate host")


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Activate additional host %s", config.HOSTS[2])
    if not host_api.activateHost(True, config.HOSTS[2]):
        logger.error("Failed to activate host")
    logger.info("Remove all vms from cluster %s", config.CLUSTER_NAME[0])
    if not vm_api.remove_all_vms_from_cluster(
        config.CLUSTER_NAME[0], skip=config.VM_NAME
    ):
        logger.error("Failed to remove vms")
