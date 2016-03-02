"""
Scheduler - Rhevm Cluster Policies test initialization
"""
import logging
from rhevmtests.sla import config
import art.rhevm_api.tests_lib.low_level.sla as sla_api

logger = logging.getLogger(__name__)

#################################################


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Free all host CPU's from loading")
    sla_api.stop_cpu_loading_on_resources(config.VDS_HOSTS[:3])
