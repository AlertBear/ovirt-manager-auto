from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.hosts import updateHost
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
import logging

logger = logging.getLogger("Soft_Fencing")

#################################################


def setup_package():
    """
    Prepare environment for Soft Fencing test
    """
    import config
    logger.info("Building setup...")
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.base_name)
    if not updateHost(True, config.host_with_pm, pm=True,
                      pm_address=config.pm_address,
                      pm_type=config.pm_type_ipmilan,
                      pm_password=config.pm_password,
                      pm_username=config.pm_user):
        raise errors.HostException("Can not update host %s"
                                   % config.hosts[0])
    return


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Teardown...")
    logger.info("Wait until datacenter up")
    if not waitForDataCenterState(config.dc_name):
        raise errors.DataCenterException("Datacenter down")
    if not cleanDataCenter(positive=True, datacenter=config.dc_name,
                           vdc=config.VDC,
                           vdc_password=config.VDC_PASSWORD):
        raise errors.DataCenterException("Cannot remove setup")
