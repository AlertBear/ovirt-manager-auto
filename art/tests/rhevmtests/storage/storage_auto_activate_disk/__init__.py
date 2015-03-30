"""
Storage Auto Activate Tests
"""

import logging
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from rhevmtests.storage.storage_auto_activate_disk import config

logger = logging.getLogger(__name__)


def setup_package():
    """
    Setup datacenter with hosts and storage domains as defined in conf file
    """
    logger.info("Building setup...")
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config=config.PARAMETERS,
                                storage=config.PARAMETERS,
                                storage_type=config.STORAGE_TYPE,
                                basename=config.TESTNAME)


def teardown_package():
    """
    Clean storage domains, Remove hosts and datacenter
    """
    logger.info("teardown")
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
