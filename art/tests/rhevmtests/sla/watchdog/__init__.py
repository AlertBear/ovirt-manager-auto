"""
Init File for Watchdog test
"""

import os
import logging

from rhevmtests.sla.watchdog import config
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.datacenters as ll_datacenters

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Watchdog test
    """
    if os.environ.get("JENKINS_URL"):
        params = dict(config.GENERAL_VM_PARAMS)
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            ll_datacenters.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            )
            params.update(config.INSTALL_VM_PARAMS)
            for vm in config.VM_NAME[:2]:
                logger.info("Create vm %s with parameters: %s", vm, params)
                if not ll_vms.createVm(
                    positive=True,
                    vmName=vm,
                    vmDescription="Watchdog VM",
                    **params
                ):
                    raise errors.VMException("Cannot add VM %s" % vm)
            ll_vms.stop_vms_safely(config.VM_NAME[:2])
        else:
            for vm in config.VM_NAME[:2]:
                logger.info("Update vm %s with parameters: %s", vm, params)
                if not ll_vms.updateVm(True, vm, **params):
                    raise errors.VMException("Failed to update vm %s" % vm)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        if not config.GOLDEN_ENV:
            ll_datacenters.clean_datacenter(
                True, config.DC_NAME[0], vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )
        else:
            # Before update vms, I want to be sure that vms in state down
            logger.info("Stop safely vms %s", config.VM_NAME[:2])
            ll_vms.stop_vms_safely(config.VM_NAME[:2])
            for vm in config.VM_NAME[:2]:
                logger.info(
                    "Update vm %s with parameters: %s",
                    vm, config.DEFAULT_VM_PARAMETERS
                )
                if not ll_vms.updateVm(
                    True, vm, **config.DEFAULT_VM_PARAMETERS
                ):
                    logger.error("Failed to update vm %s", vm)
