import logging
from rhevmtests.system.soft_fencing import config
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts

logger = logging.getLogger("Soft_Fencing")


def setup_package():
    """
    Prepare environment for Soft Fencing test
    """
    config.host_with_pm = config.HOSTS[0]
    config.host_without_pm = config.HOSTS[1]
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
    if not hl_hosts.remove_power_management(host_name=config.host_with_pm):
        logger.error("Cannot remove power management")
