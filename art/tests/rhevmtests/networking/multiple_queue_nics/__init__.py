"""
multiple_queue_nics job
"""

import logging
import art.rhevm_api.utils.test_utils as test_utils
import rhevmtests.networking as networking
import rhevmtests.networking.config as config
import art.test_handler.exceptions as exceptions

logger = logging.getLogger("Multiple_Queues_Nics_Init")
VER = config.COMP_VERSION
# ################################################


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
    logger.info(
        "Configuring engine to support queues for %s version", VER
    )
    param = [
        "CustomDeviceProperties='{type=interface;prop={queues=[1-9][0-9]*}}'",
        "'--cver=%s'" % VER
    ]
    if not test_utils.set_engine_properties(
            engine_obj=config.ENGINE, param=param
    ):
        raise exceptions.NetworkException(
            "Failed to enable queue via engine-config"
        )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Removing queues support from engine for %s version", VER)
    param = ["CustomDeviceProperties=''", "'--cver=%s'" % VER]
    if not test_utils.set_engine_properties(
            engine_obj=config.ENGINE, param=param
    ):
        logger.error(
            "Failed to remove queues support via engine-config"
        )
