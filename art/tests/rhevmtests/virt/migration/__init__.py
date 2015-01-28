"""
Virt - Migration test initialization
"""

import os
import logging

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.datacenters as dc_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.high_level.datacenters as high_dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from rhevmtests.virt import config

logger = logging.getLogger(__name__)

# ################################################

NUM_OF_VMS = 5


def createVM(vm_name):
    if not vm_api.createVm(positive=True, vmName=vm_name,
                           vmDescription=config.VM_DESCRIPTION,
                           cluster=config.CLUSTER_NAME[0],
                           storageDomainName=config.STORAGE_NAME[0],
                           size=config.DISK_SIZE,
                           nic='nic1', network=config.MGMT_BRIDGE,
                           installation=config.INSTALLATION,
                           image=config.COBBLER_PROFILE,
                           user=config.VMS_LINUX_USER,
                           password=config.VMS_LINUX_PW,
                           os_type='RHEL6x64', useAgent=True):
        raise errors.VMException("Failed to create VM: " + vm_name)


def setup_package():
    """
    Prepare environment for Migration Test
    """
    if os.environ.get("JENKINS_URL"):
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            if not high_dc_api.build_setup(config.PARAMETERS,
                                           config.PARAMETERS,
                                           config.STORAGE_TYPE,
                                           config.TEST_NAME):
                raise errors.DataCenterException("Setup environment failed")
            logger.info("Add additional cluster %s to datacenter %s",
                        config.CLUSTER_NAME[1], config.DC_NAME[0])
            if not cluster_api.addCluster(True,
                                          name=config.CLUSTER_NAME[1],
                                          version=config.COMP_VERSION,
                                          data_center=config.DC_NAME[0],
                                          cpu=config.CPU_NAME):
                raise errors.ClusterException("Cluster creation failed")
        logger.info("Create additional datacenter %s",
                    config.ADDITIONAL_DC_NAME)
        if not dc_api.addDataCenter(True, name=config.ADDITIONAL_DC_NAME,
                                    local=True,
                                    version=config.COMP_VERSION):
            raise errors.DataCenterException("Datacenter creation failed")
        logger.info("Add cluster to datacenter %s",
                    config.ADDITIONAL_DC_NAME)
        if not cluster_api.addCluster(True,
                                      name=config.ADDITIONAL_CL_NAME,
                                      version=config.COMP_VERSION,
                                      data_center=config.ADDITIONAL_DC_NAME,
                                      cpu=config.CPU_NAME):
            raise errors.ClusterException("Cluster creation failed")
        if not config.GOLDEN_ENV:
            # Temporary update clusters to memory over commitment of 0%
            # Need to be removed once ART default will be 0%
            for cluster_name in [config.CLUSTER_NAME[0],
                                 config.CLUSTER_NAME[1],
                                 config.ADDITIONAL_CL_NAME]:
                logger.info('Update cluster %s to mem_ovrcmt_prc=0',
                            cluster_name)
                if not cluster_api.updateCluster(
                        True, cluster_name, mem_ovrcmt_prc=0):
                    raise errors.VMException("Failed to update \
                        cluster %s to mem_ovrcmt_prc=0" % cluster_name)
            logger.info('Create vms: %s', config.VM_NAMES[:5])
            for vm_name in config.VM_NAMES[:5]:
                createVM(vm_name)
            logger.info("Stop all vms")
            if not vm_api.stopVms(','.join(config.VM_NAMES[:5])):
                raise errors.VMException("Failed to stop vms")
        if config.GOLDEN_ENV:
            # Create the VMs from existing template, in the golden env.
            for vm_name in config.VM_NAMES[:5]:
                if not vm_api.createVm(
                        positive=True, vmName=vm_name,
                        cluster=config.CLUSTER_NAME[0],
                        vmDescription="mig_vm",
                        template=config.TEMPLATE_NAME[0]
                ):
                    raise errors.VMException("Fail to add VM %s" % vm_name)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logging.info("Remove cluster %s from datacenter %s",
                     config.ADDITIONAL_CL_NAME,
                     config.ADDITIONAL_DC_NAME)
        if not cluster_api.removeCluster(True,
                                         config.ADDITIONAL_CL_NAME):
            raise errors.ClusterException("Failed to remove cluster")
        logging.info("Remove additional datacenter %s",
                     config.ADDITIONAL_DC_NAME)
        if not dc_api.removeDataCenter(True, config.ADDITIONAL_DC_NAME):
            raise errors.DataCenterException("Failed to remove datacenter" %
                                             config.ADDITIONAL_DC_NAME)
        if not config.GOLDEN_ENV:
            logging.info("Remove additional cluster %s from datacenter %s",
                         config.CLUSTER_NAME[1], config.DC_NAME[0])
            if not cluster_api.removeCluster(True,
                                             config.CLUSTER_NAME[1]):
                raise errors.ClusterException("Failed to remove cluster")
            if not cleanDataCenter(True, config.DC_NAME[0],
                                   vdc=config.VDC_HOST,
                                   vdc_password=config.VDC_ROOT_PASSWORD):
                raise errors.DataCenterException("Clean up environment failed")
        if config.GOLDEN_ENV:
            logger.info("Stop test vms")
            vm_api.stop_vms_safely(config.VM_NAMES[:5], max_workers=5)
            logger.info("Remove test vms")
            if not vm_api.removeVms(True, config.VM_NAMES[:5]):
                raise errors.VMException("Failed to remove test vms")
