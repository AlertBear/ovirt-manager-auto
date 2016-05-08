"""
multiple_queue_nics job
"""

import logging
import rhevmtests.networking as networking

logger = logging.getLogger("Multiple_Queues_Nics_Init")


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
