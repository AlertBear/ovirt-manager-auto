"""
Setup for regression hosts test
"""

import logging

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.test_handler.exceptions import DataCenterException
from rhevmtests.system.reg_hosts import config


logger = logging.getLogger("Regression hosts")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        return
    logger.info("Creating data center, cluster, adding host and storage")
    if not datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                   config.STORAGE_TYPE, config.TEST_NAME):
        raise DataCenterException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        return
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                           vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise DataCenterException("Cannot remove setup")
