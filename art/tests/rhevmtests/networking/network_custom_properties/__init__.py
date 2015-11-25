
"""
Network custom properties feature init
"""

import logging
import rhevmtests.networking as networking
import rhevmtests.networking.config as config
import art.test_handler.exceptions as exceptions
import art.rhevm_api.utils.test_utils as test_utils

logger = logging.getLogger("Network_Custom_Properties_Init")

# ################################################


def setup_package():
    """
    Configuring engine and running cleanup
    """
    logger.info(
        "Configuring engine to support ethtool opts for %s version",
        config.COMP_VERSION
    )
    cmd = [
        "UserDefinedNetworkCustomProperties=ethtool_opts=.*",
        "--cver=%s" % config.COMP_VERSION
        ]
    if not test_utils.set_engine_properties(config.ENGINE, cmd):
        raise exceptions.NetworkException("Couldn't run %s" % cmd)

    networking.network_cleanup()
