"""
IO feature test
"""
import logging
import rhevmtests.networking as networking


logger = logging.getLogger("IO_Test_Init")
#################################################


def setup_package():
    """
    running cleanup
    """
    networking.network_cleanup()
