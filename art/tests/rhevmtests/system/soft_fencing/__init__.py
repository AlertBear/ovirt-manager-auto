from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.hosts import updateHost
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
import logging
from rhevmtests.system.soft_fencing import config

logger = logging.getLogger("Soft_Fencing")

#################################################


def setup_package():
    """
    Prepare environment for Soft Fencing test
    """
    logger.info("Building setup...")
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.TEST_NAME)
    if not updateHost(True, config.host_with_pm, pm=True,
                      pm_address=config.PM_ADDRESS,
                      pm_type=config.PM_TYPE_IPMILAN,
                      pm_password=config.PM_PASSWORD,
                      pm_username=config.PM_USER):
        raise errors.HostException("Can not update host %s"
                                   % config.hosts[0])
    return


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Teardown...")
    logger.info("Wait until datacenter up")
    if not waitForDataCenterState(config.DC_NAME):
        raise errors.DataCenterException("Datacenter down")
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME,
                           vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise errors.DataCenterException("Cannot remove setup")
