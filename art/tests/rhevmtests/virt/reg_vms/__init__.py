"""
Virt - Regression Vms Test Initialization
"""
import os
import logging

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.datacenters as dc_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.high_level.datacenters as high_dc_api
from rhevmtests.virt import config

logger = logging.getLogger(__name__)

#################################################

DISK_SIZE = 3 * (1024 ** 3)


def setup_package():
    """
    Prepare environment for Regression Vms test
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")
        return
    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not high_dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                                       config.STORAGE_TYPE, config.TEST_NAME):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Add additional cluster to datacenter %s",
                    config.DC_NAME[0])
        if not cluster_api.addCluster(True,
                                      name=config.CLUSTER_NAME[1],
                                      version=config.COMP_VERSION,
                                      data_center=config.DC_NAME[0],
                                      cpu=config.CPU_NAME):
            raise errors.ClusterException("Cluster creation failed")
        logger.info("Create additional datacenter %s", config.DC_NAME[1])
        if not dc_api.addDataCenter(True, name=config.DC_NAME[1],
                                    local=True,
                                    version=config.COMP_VERSION):
            raise errors.DataCenterException("Datacenter creation failed")
        logger.info("Add cluster to datacenter %s",
                    config.DC_NAME[1])
        if not cluster_api.addCluster(True,
                                      name=config.CLUSTER_NAME[2],
                                      version=config.COMP_VERSION,
                                      data_center=config.DC_NAME[1],
                                      cpu=config.CPU_NAME):
            raise errors.ClusterException("Cluster creation failed")


def teardown_package():
    """
    Clean test environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")
        return
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logging.info("Remove cluster %s from datacenter %s",
                     config.CLUSTER_NAME[2], config.DC_NAME[1])
        if not cluster_api.removeCluster(True, config.CLUSTER_NAME[2]):
            raise errors.ClusterException("Failed to remove cluster")
        logging.info("Remove additional datacenter %s", config.DC_NAME[1])
        if not dc_api.removeDataCenter(True, config.DC_NAME[1]):
            raise errors.DataCenterException("Failed to remove datacenter" %
                                             config.DC_NAME[1])
        logging.info("Remove additional cluster %s from datacenter %s",
                     config.CLUSTER_NAME[1], config.DC_NAME[0])
        if not cluster_api.removeCluster(True,
                                         config.CLUSTER_NAME[1]):
            raise errors.ClusterException("Failed to remove cluster")
        if not high_dc_api.clean_datacenter(
                True, config.DC_NAME[0],
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise errors.DataCenterException("Clean up environment failed")
