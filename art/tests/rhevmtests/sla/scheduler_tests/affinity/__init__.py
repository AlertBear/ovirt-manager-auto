"""
Scheduler - Affinity Test initialization
"""

import os
import logging
from rhevmtests.sla import config

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Affinity Test
    """
    if os.environ.get("JENKINS_URL"):
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            if not dc_api.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            ):
                raise errors.DataCenterException("Setup environment failed")
            storage_domain = config.STORAGE_NAME[0]
            logger.info("Create new vms")
            for vm in config.VM_NAME[:3]:
                if not vm_api.createVm(
                    True, vm, 'Affinity VM',
                    cluster=config.CLUSTER_NAME[0],
                    storageDomainName=storage_domain,
                    size=config.GB, nic=config.NIC_NAME[0],
                    network=config.MGMT_BRIDGE
                ):
                    raise errors.VMException("Cannot create vm %s" % vm)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        if not vm_api.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            skip=config.VM_NAME
        ):
            raise errors.VMException("Failed to remove some vms")
        if not config.GOLDEN_ENV:
            if not dc_api.clean_datacenter(
                    True, config.DC_NAME[0],
                    vdc=config.VDC_HOST,
                    vdc_password=config.VDC_ROOT_PASSWORD
            ):
                raise errors.DataCenterException("Clean up environment failed")
