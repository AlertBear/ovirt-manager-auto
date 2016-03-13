import logging
from rhevmtests.system.soft_fencing import config
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.datacenters as hl_datacenters

logger = logging.getLogger("Soft_Fencing")

#################################################


def setup_package():
    """
    Prepare environment for Soft Fencing test
    """
    config.host_with_pm = config.HOSTS[0]
    config.host_without_pm = config.HOSTS[1]
    logger.info("Building setup...")
    hl_datacenters.build_setup(
        config.PARAMETERS,
        config.PARAMETERS,
        config.STORAGE_TYPE,
        config.TEST_NAME
    )
    agent = {
        "agent_type": config.PM_TYPE_IPMILAN,
        "agent_address": config.PM_ADDRESS,
        "agent_username": config.PM_USER,
        "agent_password": config.PM_PASSWORD,
        "concurrent": False,
        "order": 1
    }
    if not hl_hosts.add_power_management(
        host_name=config.host_with_pm, pm_agents=[agent]
    ):
        raise errors.HostException()


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Teardown...")
    logger.info("Wait until datacenter up")
    if not ll_datacenters.waitForDataCenterState(config.DC_NAME[0]):
        logger.error("Datacenter down")
    if not hl_datacenters.clean_datacenter(
            positive=True, datacenter=config.DC_NAME[0],
            vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
    ):
        logger.error("Cannot remove setup")
