"""
SLA test
"""

import os
import logging

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.test_handler.exceptions as errors

from rhevmtests.sla.watchdog import config

logger = logging.getLogger("SLA")
AFFINITY = config.ENUMS['vm_affinity_user_migratable']

#################################################


def setup_package():
    """
    Prepare environment for SLA test
    """
    if os.environ.get("JENKINS_URL"):
        params = dict(config.GENERAL_VM_PARAMS)
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            datacenters.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            )
            vms_to_create = [config.VM_NAME[0], config.WATCHDOG_VM]
            params.update(config.INSTALL_VM_PARAMS)
        else:
            params['template'] = config.TEMPLATE_NAME[0]
            vms_to_create = [config.WATCHDOG_VM]
        for vm in vms_to_create:
            if not vms.createVm(
                positive=True, vmName=vm,
                vmDescription="Watchdog VM",
                **params
            ):
                raise errors.VMException("Cannot add VM %s" % vm)
        vms.stop_vms_safely(vms_to_create)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logger.info("Remove all exceed vms")
        if not vms.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0], skip=config.VM_NAME
        ):
            raise errors.VMException("Failed to remove vms")
        if not config.GOLDEN_ENV:
            cleanDataCenter(
                True, config.DC_NAME[0], vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )
