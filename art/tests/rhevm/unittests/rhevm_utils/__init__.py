"""
    rhevm utils package
"""

import logging


def setUpPackage():
    """
    Setup module function, put here every thing what should be done when module
    is loaded by unittests.
    """
    from rhevm_utils.base import config as configuration

    logging.basicConfig(level=logging.DEBUG)
    #from testconfig import config
    logging.debug("LOADED CONFIG: %s", configuration)
