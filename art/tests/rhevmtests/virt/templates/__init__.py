"""
Templates Test
"""

import os
import logging

import art.test_handler.exceptions as errors
from rhevmtests.virt import config
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters

logger = logging.getLogger("Templates")

#################################################


def setup_package():
    """
    Prepare environment for template test
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")
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
        logger.info("Running on golden env")
        return
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        if not datacenters.clean_datacenter(
                True,
                config.DC_NAME[0],
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise errors.DataCenterException("Clean up environment failed")
