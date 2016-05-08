
"""
Network custom properties feature init
"""

import logging
import rhevmtests.networking as networking

logger = logging.getLogger("Network_Custom_Properties_Init")

# ################################################


def setup_package():
    """
    Running cleanup
    """
    networking.network_cleanup()
