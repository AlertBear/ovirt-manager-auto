"""
Ha reservation test initialization and teardown
"""

import os
import logging
import art.test_handler.exceptions as errors
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.high_level.datacenters import (
    build_setup,
    clean_datacenter,
)
from art.rhevm_api.tests_lib.low_level import vms

from rhevmtests.sla.ha_reservation import config

logger = logging.getLogger("HA_Reservation")
#################################################


def setup_package():
    """
    Prepare environment for MOM test
    """

    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not config.GOLDEN_ENV:
            build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            )
        for vm_name, params in config.SPECIFIC_VMS_PARAMS.iteritems():
            param_dict = dict(config.GENERAL_VM_PARAMS)
            param_dict.update(params)
            if not config.GOLDEN_ENV:
                param_dict.update(config.INSTALL_VM_PARAMS)
            else:
                logger.info("Create vm %s from template %s",
                            vm_name, config.TEMPLATE_NAME[0])
                param_dict['template'] = config.TEMPLATE_NAME[0]
            logger.info("Create vm %s with parameters %s", vm_name, param_dict)
            if not vms.createVm(
                True, vmName=vm_name, vmDescription="VM for test 336832",
                **param_dict
            ):
                raise errors.VMException(
                    "Failed to create VM for allocation"
                )
        vms.stop_vms_safely(config.SPECIFIC_VMS_PARAMS.keys())
        logger.info("RHEL successfully installed on testing VMs")
        if config.GOLDEN_ENV:
            logger.info("Deactivate host %s on cluster %s",
                        config.HOSTS[2], config.CLUSTER_NAME[0])
            if not hosts.deactivateHost(True, config.HOSTS[2]):
                raise errors.HostException("Failed to deactivate hosts")
        logger.info("Update cluster %s memory over commitment to %d percent",
                    config.CLUSTER_NAME[0], 100)
        if not clusters.updateCluster(
            True, config.CLUSTER_NAME[0], ha_reservation=True,
            mem_ovrcmt_prc=100
        ):
            raise errors.ClusterException("Failed to update cluster")
        logger.info("Cluster configuration updated")


def teardown_package():
    """
    Cleans the environment
    """

    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        if not vms.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            config.VM_NAME
        ):
            raise errors.VMException("Failed to remove all vms")
        logger.info("Update cluster %s memory over commitment to %d percent",
                    config.CLUSTER_NAME[0], 200)
        if not clusters.updateCluster(
            True, config.CLUSTER_NAME[0], ha_reservation=False,
            mem_ovrcmt_prc=200
        ):
            raise errors.ClusterException("Failed to update cluster")
        if not config.GOLDEN_ENV:
            clean_datacenter(
                True, config.DC_NAME, vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )
        else:
            logger.info("Activate host %s on cluster %s",
                        config.HOSTS[2], config.CLUSTER_NAME[0])
            if not hosts.activateHost(True, config.HOSTS[2]):
                raise errors.HostException("Failed to activate host")
