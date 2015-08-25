"""
Bridgeless network feature test
"""

import logging
import rhevmtests.networking as networking
logger = logging.getLogger("Bridgeless_Networks_Init")

#################################################


def setup_package():
    """
    running cleanup
    """
    networking.network_cleanup()
