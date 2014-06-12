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

logger = logging.getLogger(__name__)

#################################################

NUM_OF_VMS = 5


def setup_package():
    """
    Prepare environment for Migration Test
    """
    if os.environ.get("JENKINS_URL"):
        import config
        logger.info("Building setup...")
        if not high_dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                                       config.STORAGE_TYPE, config.TEST_NAME):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Add additional cluster %s to datacenter %s",
                    config.additional_cluster_names[0], config.second_dc_name)
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
            vm_names = config.vm_names
            logger.info('Create vms: %s', config.vm_names[:5])
            for vm_name in vm_names[:5]:
                results.append(executor.submit(
                    vm_api.createVm, positive=True, vmName=vm_name,
                    vmDescription=config.vm_description,
                    cluster=config.cluster_name,
                    storageDomainName=config.storage_name,
                    size=config.DISK_SIZE,
                    nic='nic1', network=config.cluster_network,
                    installation=config.installation, image=config.image,
                    cobblerAddress=config.cobblerAddress,
                    cobblerUser=config.cobblerUser,
                    cobblerPasswd=config.cobblerPasswd,
                    user=config.VM_LINUX_USER,
                    password=config.VM_LINUX_PASSWORD,
                    os_type='RHEL6x64', useAgent=True))
        raise_if_exception(results)
        logger.info("Stop all vms")
        if not vm_api.stopVms(','.join(vm_names[:5])):
            raise errors.VMException("Failed to stop vms")


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        import config
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
