"""
Templates Test
"""

import os
import logging

from rhevmtests.virt import config
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter

logger = logging.getLogger("Templates")

#################################################


def setup_package():
    """
    Prepare environment for template test
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        return
    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TEST_NAME)


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")
        return
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        dc_name = config.DC_name
        cleanDataCenter(True, dc_name, vdc=config.VDC_HOST,
                        vdc_password=config.VDC_ROOT_PASSWORD)
