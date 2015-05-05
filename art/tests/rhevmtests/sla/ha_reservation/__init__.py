"""
Ha reservation test initialization and teardown
"""

import os
import logging
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.high_level.datacenters as ll_datacenters
from rhevmtests.sla.ha_reservation import config

logger = logging.getLogger("HA_Reservation")
#################################################

CLUSTER_OVERCOMMITMENT_NONE = 100
CLUSTER_OVERCOMMITMENT_DESKTOP = 200


def setup_package():
    """
    Prepare environment for HA reservation test
    """

    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not config.GOLDEN_ENV:
            ll_datacenters.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            )
            for vm_name in config.VM_NAME[:3]:
                param_dict = dict(config.GENERAL_VM_PARAMS)
                param_dict.update(config.INSTALL_VM_PARAMS)
                logger.info(
                    "Create vm %s with parameters: %s", vm_name, param_dict
                )
                if not ll_vms.createVm(
                    positive=True,
                    vmName=vm_name,
                    vmDescription="VM for test 336832",
                    **param_dict
                ):
                    raise errors.VMException(
                        "Failed to create VM %s" % vm_name
                    )
            logger.info("Stop if need vms: %s", config.VM_NAME[:3])
            ll_vms.stop_vms_safely(config.VM_NAME[:3])
        else:
            logger.info(
                "Deactivate host %s on cluster %s",
                config.HOSTS[2], config.CLUSTER_NAME[0]
            )
            if not ll_hosts.deactivateHost(True, config.HOSTS[2]):
                raise errors.HostException(
                    "Failed to deactivate host %s" % config.HOSTS[2]
                )
        logger.info(
            "Update cluster %s memory over commitment to %d percent",
            config.CLUSTER_NAME[0], CLUSTER_OVERCOMMITMENT_NONE
        )
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=config.CLUSTER_NAME[0],
            ha_reservation=True,
            mem_ovrcmt_prc=CLUSTER_OVERCOMMITMENT_NONE
        ):
            raise errors.ClusterException(
                "Failed to update cluster %s" % config.CLUSTER_NAME[0]
            )
        for vm_name, params in config.SPECIFIC_VMS_PARAMS.iteritems():
            logger.info(
                "Update vm %s with parameters: %s",
                vm_name, params
            )
            if not ll_vms.updateVm(
                positive=True, vm=vm_name, **params
            ):
                raise errors.VMException(
                    "Failed to update vm %s" % vm_name
                )


def teardown_package():
    """
    Cleans the environment
    """

    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logger.info(
            "Update cluster %s memory over commitment to %d percent",
            config.CLUSTER_NAME[0], CLUSTER_OVERCOMMITMENT_DESKTOP
        )
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=config.CLUSTER_NAME[0],
            ha_reservation=False,
            mem_ovrcmt_prc=CLUSTER_OVERCOMMITMENT_DESKTOP
        ):
            logger.error(
                "Failed to update cluster memory overcommitment %s",
                config.CLUSTER_NAME[0]
            )
        if not config.GOLDEN_ENV:
            ll_datacenters.clean_datacenter(
                positive=True,
                datacenter=config.DC_NAME,
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )
        else:
            logger.info(
                "Activate host %s on cluster %s",
                config.HOSTS[2], config.CLUSTER_NAME[0]
            )
            if not ll_hosts.activateHost(True, config.HOSTS[2]):
                logger.error("Failed to activate host %s", config.HOSTS[0])
            for vm_name in config.VM_NAME[:3]:
                logger.info(
                    "Update vm %s to default parameters: %s",
                    vm_name, config.DEFAULT_VM_PARAMETERS
                )
                if not ll_vms.updateVm(
                    positive=True, vm=vm_name, **config.DEFAULT_VM_PARAMETERS
                ):
                    logger.error("Failed to update vm %s", vm_name)
