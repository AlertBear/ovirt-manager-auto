"""
Virt - Regression Vms Test Initialization
"""
import os
import logging

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.datacenters as dc_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.high_level.datacenters as high_dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter

logger = logging.getLogger(__name__)

#################################################

DISK_SIZE = 3 * (1024 ** 3)


def setup_package():
    """
    Prepare environment for Regression Vms test
    """
    import config
    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not high_dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                                       config.STORAGE_TYPE, config.TEST_NAME):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Add additional cluster to datacenter %s", config.dc_name)
        if not cluster_api.addCluster(True,
                                      name=config.additional_cluster_names[0],
                                      version=config.compatibility_version,
                                      data_center=config.dc_name,
                                      cpu=config.cpu_name):
            raise errors.ClusterException("Cluster creation failed")
        logger.info("Create additional datacenter %s", config.second_dc_name)
        if not dc_api.addDataCenter(True, name=config.second_dc_name,
                                    local=True,
                                    version=config.compatibility_version):
            raise errors.DataCenterException("Datacenter creation failed")
        logger.info("Add cluster to datacenter %s",
                    config.second_dc_name)
        if not cluster_api.addCluster(True,
                                      name=config.additional_cluster_names[1],
                                      version=config.compatibility_version,
                                      data_center=config.second_dc_name,
                                      cpu=config.cpu_name):
            raise errors.ClusterException("Cluster creation failed")


def teardown_package():
    """
    Clean test environment
    """
    import config
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logging.info("Remove cluster %s from datacenter %s",
                     config.additional_cluster_names[1],
                     config.second_dc_name)
        if not cluster_api.removeCluster(True,
                                         config.additional_cluster_names[1]):
            raise errors.ClusterException("Failed to remove cluster")
        logging.info("Remove additional datacenter %s", config.second_dc_name)
        if not dc_api.removeDataCenter(True, config.second_dc_name):
            raise errors.DataCenterException("Failed to remove datacenter" %
                                             config.second_dc_name)
        logging.info("Remove additional cluster %s from datacenter %s",
                     config.additional_cluster_names[0], config.dc_name)
        if not cluster_api.removeCluster(True,
                                         config.additional_cluster_names[0]):
            raise errors.ClusterException("Failed to remove cluster")
        if not cleanDataCenter(True, config.dc_name, vdc=config.VDC,
                               vdc_password=config.VDC_PASSWORD):
            raise errors.DataCenterException("Clean up environment failed")
