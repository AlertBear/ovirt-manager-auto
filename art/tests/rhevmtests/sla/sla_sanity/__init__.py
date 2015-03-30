"""
SLA test
"""

import os
import logging
from rhevmtests.sla import config
import art.test_handler.exceptions as errors

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import datacenters

logger = logging.getLogger("SLA")

#################################################


def setup_package():
    """
    Prepare environment for SLA test
    """
    if os.environ.get("JENKINS_URL") and not config.GOLDEN_ENV:
        logger.info("Building setup...")
        datacenters.build_setup(
            config.PARAMETERS, config.PARAMETERS,
            config.STORAGE_TYPE, config.TEST_NAME
        )


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
            datacenters.clean_datacenter(
                True, config.DC_NAME[0], vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )
