#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Migration test initialization
"""

import logging
from rhevmtests import networking
from rhevmtests.virt import config
from art.test_handler import exceptions
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from rhevmtests.networking import helper as net_helper
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.virt.helper as virt_helper

logger = logging.getLogger("Virt_Network_Migration_Init")


# ################################################
def setup_package():
    """
    Prepare environment for Migration Test
    In case of GE environment:
      1. run network cleanup
      2. In case if PPC: Import vm from glance and start vm
         Else:use GE vm
      3. set two hosts to maintenance
      4. Create additional data center and cluster
      5. Update clusters to memory over commitment of 0%
    """
    networking.network_cleanup()
    if not config.PPC_ARCH:
        virt_helper.create_vm_from_glance_image(
            image_name=config.MIGRATION_IMAGE_VM,
            vm_name=config.MIGRATION_VM
        )
        if not ll_vms.updateVm(
            positive=True,
            vm=config.MIGRATION_VM,
            memory=config.GB * 2,
            memory_guaranteed=config.GB,
            os_type=config.OS_RHEL_7
        ):
            raise exceptions.VMException(
                "Failed to update vm memory and os type"
            )
    if not net_helper.run_vm_once_specific_host(
        vm=config.MIGRATION_VM, host=config.HOSTS[0],
        wait_for_up_status=True
    ):
        raise exceptions.VMException()

    logger.info(
        "Set all but 2 hosts in the Cluster %s to the maintenance "
        "state", config.CLUSTER_NAME[0]
    )
    virt_helper.set_host_status()
    logger.info("Add additional data center and cluster")
    if not hl_networks.create_basic_setup(
        config.ADDITIONAL_DC_NAME,
        version=config.COMP_VERSION,
        cluster=config.ADDITIONAL_CL_NAME,
        cpu=config.CPU_NAME
    ):
        raise errors.TestException(
            "Failed to create additional data center %s and cluster %s " %
            (config.ADDITIONAL_DC_NAME, config.ADDITIONAL_CL_NAME)
        )
    # update cluster over commit to none
    logger.info("For all clusters update over commit to 'none'")
    for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
        logger.info(
            "Update cluster %s to mem_ovrcmt_prc=0", cluster_name
        )
        if not cluster_api.updateCluster(True, cluster_name, mem_ovrcmt_prc=0):
            raise errors.VMException(
                "Failed to update cluster %s to mem_ovrcmt_prc=0" %
                cluster_name
            )


def teardown_package():
    """
    Teardown:
     In case of GE environment:
       1. In case of PPC: remove migrate
       2. Stop all GE VMs
       2. set hosts to active
       3. Remove additional data center and cluster
       4. Update cluster over commit to 200%
    """
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
                "Failed to update cluster %s to mem_ovrcmt_prc=0", cluster_name
            )

    logging.info(
        "Remove additional data center %s and cluster %s",
        config.ADDITIONAL_DC_NAME,
        config.ADDITIONAL_CL_NAME
    )
    if not hl_networks.remove_basic_setup(
        config.ADDITIONAL_DC_NAME, cluster=config.ADDITIONAL_CL_NAME,
    ):
        logger.error(
            "Failed to remove additional data center %s and cluster %s",
            config.ADDITIONAL_DC_NAME, config.ADDITIONAL_CL_NAME
        )
    if not config.PPC_ARCH:
        if not ll_vms.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0], skip=config.VM_NAME
        ):
            logger.error("Failed to remove VM: %s", config.MIGRATION_VM)
    if not ll_vms.stop_vms_safely([config.MIGRATION_VM]):
        logger.error("Failed to stop VM: %s", config.MIGRATION_VM)
    logger.info("Set inactive hosts to the active state")
    virt_helper.set_host_status(activate=True)
