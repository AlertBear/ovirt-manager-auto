"""
Virt - Migration test initialization
"""

import os
import logging
from concurrent.futures.thread import ThreadPoolExecutor

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.datacenters as dc_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.high_level.datacenters as high_dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.utils.test_utils import raise_if_exception
from rhevmtests.virt import config

logger = logging.getLogger(__name__)

#################################################

NUM_OF_VMS = 5


def setup_package():
    """
    Prepare environment for Migration Test
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not high_dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                                       config.STORAGE_TYPE, config.TEST_NAME):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Add additional cluster %s to datacenter %s",
                    config.additional_cluster_names[0], config.second_dc_name)
        if not cluster_api.addCluster(True,
                                      name=config.additional_cluster_names[0],
                                      version=config.COMP_VERSION,
                                      data_center=config.dc_name,
                                      cpu=config.CPU_NAME):
            raise errors.ClusterException("Cluster creation failed")
        logger.info("Create additional datacenter %s", config.second_dc_name)
        if not dc_api.addDataCenter(True, name=config.second_dc_name,
                                    local=True,
                                    version=config.COMP_VERSION):
            raise errors.DataCenterException("Datacenter creation failed")
        logger.info("Add cluster to datacenter %s",
                    config.second_dc_name)
        if not cluster_api.addCluster(True,
                                      name=config.additional_cluster_names[1],
                                      version=config.COMP_VERSION,
                                      data_center=config.second_dc_name,
                                      cpu=config.CPU_NAME):
            raise errors.ClusterException("Cluster creation failed")
        # Temporary update clusters to memeory over commitment of 0%
        # Need to be removed once ART default will be 0%
        for cluster_name in [config.cluster_name,
                             config.additional_cluster_names[0],
                             config.additional_cluster_names[1]]:
            logger.info('Update cluster %s to mem_ovrcmt_prc=0', cluster_name)
            if not cluster_api.updateCluster(
                    True, cluster_name, mem_ovrcmt_prc=0):
                raise errors.VMException("Failed to update \
                    cluster %s to mem_ovrcmt_prc=0" % cluster_name)
        results = list()
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            logger.info('Create vms: %s', config.VM_NAMES[:5])
            for vm_name in config.VM_NAMES[:5]:
                results.append(executor.submit(
                    vm_api.createVm, positive=True, vmName=vm_name,
                    vmDescription=config.VM_DESCRIPTION,
                    cluster=config.cluster_name,
                    storageDomainName=config.storage_name,
                    size=config.DISK_SIZE,
                    nic='nic1', network=config.MGMT_BRIDGE,
                    installation=config.INSTALLATION,
                    image=config.COBBLER_PROFILE,
                    cobblerAddress=config.COBBLER_ADDRESS,
                    cobblerUser=config.COBBLER_USER,
                    cobblerPasswd=config.COBBLER_PASSWD,
                    user=config.VMS_LINUX_USER,
                    password=config.VMS_LINUX_PW,
                    os_type='RHEL6x64', useAgent=True))
        raise_if_exception(results)
        logger.info("Stop all vms")
        if not vm_api.stopVms(','.join(config.VM_NAMES[:5])):
            raise errors.VMException("Failed to stop vms")


def teardown_package():
    """
    Cleans the environment
    """
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
        if not cleanDataCenter(True, config.dc_name, vdc=config.VDC_HOST,
                               vdc_password=config.VDC_ROOT_PASSWORD):
            raise errors.DataCenterException("Clean up environment failed")
