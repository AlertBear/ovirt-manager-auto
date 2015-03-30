"""
Allow big ranges in MacPoolManager
"""

import logging
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from art.rhevm_api.utils.test_utils import(
    set_engine_properties, get_engine_properties
)
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking import config, network_cleanup

logger = logging.getLogger("BigRangeMacPool_Init")

ENGINE_DEFAULT_MAC_RANGE = []


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")
        network_cleanup()
        logger.info("Get engine default MAC pool range")
        engine_default_mac_range = get_engine_properties(
            config.ENGINE, [config.MAC_POOL_RANGE_CMD]
        )[0]
        ENGINE_DEFAULT_MAC_RANGE.append(engine_default_mac_range)

    else:
        logger.info("Create setup with datacenter, cluster, host and storage")
        if not prepareSetup(
            hosts=config.VDS_HOSTS[0], cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            storage_type=config.STORAGE_TYPE, cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0], lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION
        ):
            raise NetworkException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")
        logger.info("Setting engine MacPoolRange to default")
        cmd = "=".join(
            [config.MAC_POOL_RANGE_CMD, ENGINE_DEFAULT_MAC_RANGE[0]]
        )
        if not set_engine_properties(config.ENGINE_HOST, [cmd]):
            logger.error(
                "Failed to set MAC: %s", ENGINE_DEFAULT_MAC_RANGE[0]
            )

    else:
        logger.info("Removing setup")
        if not clean_datacenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")
