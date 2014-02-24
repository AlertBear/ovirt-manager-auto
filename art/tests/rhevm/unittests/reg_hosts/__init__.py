"""
Setup for regression hosts test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter,\
    createDatacenter
from art.test_handler.exceptions import DataCenterException
from art.test_handler.exceptions import HostException
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters


logger = logging.getLogger("Regression hosts")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    logger.info("Creating data center, cluster, adding host and storage")
    if not datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                   config.STORAGE_TYPE, config.TEST_NAME):
        raise DataCenterException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME,
                           vdc=config.VDC, vdc_password=config.VDC_PASSWORD):
        raise DataCenterException("Cannot remove setup")
