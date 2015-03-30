#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Migration test initialization
"""

import os
import logging

from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from rhevmtests.networking import network_cleanup
from rhevmtests.networking import config as netconf
import art.test_handler.exceptions as errors
from art.test_handler.exceptions import (
    NetworkException, TestException
)
from rhevmtests.virt.migration.helper import set_host_status
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
from rhevmtests.virt import config
from rhevmtests.virt.migration import helper
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import vms as hl_vm
from art.rhevm_api.tests_lib.high_level.networks import (
    create_basic_setup, remove_basic_setup
)


logger = logging.getLogger("Virt_Network_Migration_Init")

# ################################################

NUM_OF_VMS = 5


def setup_package():
    """
    Prepare environment for Migration Test
    In case of GE environment:
      1. run network cleanup
      2. start vm
      3. set two hosts to maintenance
    In case of Non-GE environment:
      builds setup:
      DC, Cluster, Template, and VMs
    For all environments:
      1. Create additional data center and cluster
      3. Update clusters to memory over commitment of 0%
    """
    if os.environ.get("JENKINS_URL"):
        if config.GOLDEN_ENV:
            network_cleanup()
            logger.info(
                "Running on golden env, starting VM %s on host %s",
                config.VM_NAME[0],
                config.HOSTS[0]
            )
            if not hl_vm.start_vm_on_specific_host(
                vm=config.VM_NAME[0], host=config.HOSTS[0]
            ):
                raise NetworkException(
                    "Cannot start VM %s on host %s" %
                    (
                        config.VM_NAME[0],
                        config.HOSTS[0]
                    )
                )
            if not vms.waitForVMState(vm=config.VM_NAME[0]):
                raise NetworkException(
                    "VM %s did not come up" %
                    config.VM_NAME[0]
                )
            logger.info(
                "Set all but 2 hosts in the Cluster %s to the maintenance "
                "state", config.CLUSTER_NAME[0]
            )
            set_host_status()
        if not config.GOLDEN_ENV:
            logger.info("Non GE, building environment")
            if not helper.prepare_environment():
                raise TestException("Failed to create environment")
        logger.info("For all environments:")
        logger.info("add additional data center and cluster")
        if not create_basic_setup(
            config.ADDITIONAL_DC_NAME,
            storage_type=netconf.STORAGE_TYPE,
            version=config.COMP_VERSION,
            cluster=config.ADDITIONAL_CL_NAME,
            cpu=config.CPU_NAME
        ):
            raise errors.TestException(
                "Failed to create additional data center %s and cluster %s " %
                (
                    config.ADDITIONAL_DC_NAME,
                    config.ADDITIONAL_CL_NAME
                )
            )
        # update cluster over commit to none
        logger.info("For all clusters update over commit to 'none'")
        for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
            logger.info(
                "Update cluster %s to mem_ovrcmt_prc=0", cluster_name
            )
            if not cluster_api.updateCluster(
                True, cluster_name, mem_ovrcmt_prc=0
            ):
                raise errors.VMException(
                    "Failed to update cluster %s to mem_ovrcmt_prc=0" %
                    cluster_name
                )


def teardown_package():
    """
    Teardown:
     In case of GE environment:
       1. stop VMs
       2. set hosts to active
     In case of Non-GE environment:
       Cleans the environment: remove DC ,Cluster, host and VMs
     For all environments:
       Remove additional data center and cluster
       update cluster over commit to 200%
    """
    logger.info("Teardown...")
    if os.environ.get("JENKINS_URL"):
        logger.info("For all environments:")
        # update clusters over commit back to 200%
        logger.info("For all clusters update over commit back to '200%'")
        for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
            logger.info(
                "Update cluster %s to mem_ovrcmt_prc=200", cluster_name
            )
            if not cluster_api.updateCluster(
                True, cluster_name, mem_ovrcmt_prc=200
            ):
                logger.error(
                    "Failed to update cluster %s to mem_ovrcmt_prc=0",
                    cluster_name
                )

        logging.info(
            "Remove additional data center %s and cluster %s",
            config.ADDITIONAL_DC_NAME,
            config.ADDITIONAL_CL_NAME
        )
        if not remove_basic_setup(
            config.ADDITIONAL_DC_NAME,
            cluster=config.ADDITIONAL_CL_NAME,
        ):
            logger.error(
                "Failed to remove additional data center %s and cluster %s",
                config.ADDITIONAL_DC_NAME,
                config.ADDITIONAL_CL_NAME
            )
        if not config.GOLDEN_ENV:
            try:
                logger.info("Non GE environment:")
                logging.info("Remove all elements in data center: dataCenter,"
                             "storage domains, hosts & cluster."
                             "in data center %s ", config.DC_NAME[0])
                if not clean_datacenter(
                    True, config.DC_NAME[0], vdc=config.VDC_HOST,
                    vdc_password=config.VDC_ROOT_PASSWORD
                ):
                    logger.error("Clean up environment failed")
            except Exception, e:
                logger.error(
                    "Non GE environment:tearDown failed, %s",
                    e.message
                )
        if config.GOLDEN_ENV:
            try:
                logger.info("GE environment:")
                logger.info(
                    "Running on golden env, stopping VM %s", config.VM_NAME[0]
                )
                if not vms.stopVm(True, vm=config.VM_NAME[0]):
                    logger.error(
                        "Failed to stop VM: %s", config.VM_NAME[0]
                    )
                logger.info("Set inactive hosts to the active state")
                set_host_status(activate=True)
            except Exception, e:
                logger.error("tearDown failed, %s", e.message)
