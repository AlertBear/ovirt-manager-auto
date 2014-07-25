"""
SLA test
"""

import os
import logging

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter

logger = logging.getLogger("SLA")

#################################################


def setup_package():
    """
    Prepare environment for SLA test
    """
    if os.environ.get("JENKINS_URL"):
        import config
        logger.info("Building setup...")
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TEST_NAME)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        import config
        logger.info("Teardown...")
        dc_name = config.DC_NAME[0]
        cleanDataCenter(True, dc_name, vdc=config.VDC_HOST,
                        vdc_password=config.VDC_ROOT_PASSWORD)
