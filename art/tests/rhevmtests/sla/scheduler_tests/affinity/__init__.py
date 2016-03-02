"""
Scheduler - Affinity Test initialization
"""
import logging
from rhevmtests.sla import config as conf
from art.rhevm_api.utils import test_utils
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd

logger = logging.getLogger(__name__)

#################################################

AREM_OPTION = "AffinityRulesEnforcementManagerEnabled"


def setup_package():
    """
    Prepare environment for Affinity Test
    """
    logger.info("Disable AREM manager via engine-config")
    cmd = ["{0}=false".format(AREM_OPTION)]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd):
        raise errors.UnkownConfigurationException(
            "Failed to set %s option to false" % AREM_OPTION
        )
    if not ll_sd.waitForStorageDomainStatus(
        positive=True,
        dataCenterName=conf.DC_NAME[0],
        storageDomainName=conf.STORAGE_NAME[0],
        expectedStatus=conf.SD_ACTIVE
    ):
        raise errors.StorageDomainException(
            "Storage domain %s not active" % conf.STORAGE_NAME[0]
        )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Enable AREM manager via engine-config")
    cmd = ["{0}=true".format(AREM_OPTION)]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd):
        logger.error("Failed to set %s option to false", AREM_OPTION)
    if not ll_sd.waitForStorageDomainStatus(
        positive=True,
        dataCenterName=conf.DC_NAME[0],
        storageDomainName=conf.STORAGE_NAME[0],
        expectedStatus=conf.SD_ACTIVE
    ):
        logger.error(
            "Storage domain %s not active", conf.STORAGE_NAME[0]
        )
