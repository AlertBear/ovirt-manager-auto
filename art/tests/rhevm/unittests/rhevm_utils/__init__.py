
"""
This module provides way to test RHEVM CLI tools.

There is separate class for each utility, you can use it to execute specific
utility on your setup and then call 'autoTest' function which requires
no parameter and will perform sanity check according passed params to
utility.

Tt also provides base for unittests which is used to automate TCMS test plans.
You can run these tests like this way:

run all tests:
nosetests --tc-file=unittest_conf.py --tc-format=python --with-xunit rhevm_utils
run test for specific utility:
nosetests --tc-file=unittest.conf --with-xunit rhevm_utils.<spec> ...

You can also run sanity checks from xml, there is wrappers module which
execute specific utility and then call autoTest.

Also you can run some tests using rhevm_utils module itself, try use:
python rhevm_utils --help
"""

import configobj
import unittest
import logging

from rhevm_utils.base import Setup, PRODUCT_RHEVM, PRODUCT_RHEVM, config as configuration
from rhevm_utils.setup import SetupUtility, SetupTestCase
from rhevm_utils.cleanup import CleanUpUtility, CleanUpTestCase
from rhevm_utils.iso_uploader import ISOUploadUtility
from rhevm_utils.log_collector import LogCollectorUtility
from rhevm_utils.config import ConfigUtility
from rhevm_utils.manage_domains import ManageDomainsUtility
from rhevm_utils.upgrade import UpgradeUtility
from rhevm_utils.errors import RHEVMUtilsError
import errors

class RHEVMUtilities(Setup):
    """
    Top level class encapsulates all utilities. It contains attribute for each
    utility named accordinally.
    """

    def __init__(self, *args, **kwargs):
        """
        C'tor
        Parameters:
         * host - address to rhevm setup (VDC)
         * user - root username
         * passwd - root password
         * dbuser - name of database user
        """
        super(RHEVMUtilities, self).__init__(*args, **kwargs)
        self.setup = SetupUtility(self)
        self.cleanup = CleanUpUtility(self)
        self.iso_uploader = ISOUploadUtility(self)
        self.log_collector = LogCollectorUtility(self)
        self.config = ConfigUtility(self)
        self.manage_domains = ManageDomainsUtility(self)
        self.upgrade = UpgradeUtility(self)


def setUpPackage():
    """
    Setup module function, put here every thing what should be done when module
    is loaded by unittests.
    """
    logging.basicConfig(level=logging.DEBUG)
    #from testconfig import config
    logging.debug("LOADED CONFIG: %s", configuration)

__all__ = ["SetupUtility", "ISOUploadUtility", "LogCollectorUtility", \
        "ConfigUtility", "ManageDomainsUtility", "UpgradeUtility", \
        "CleanUpUtility", "RHEVMUtilities", "RHEVMUtilsError", "errors", \
        "PRODUCT_RHEVM", "PRODUCT_OVIRT"]

if __name__ == "__main__":
    # due py2.6 compatability
    from rhevm_utils.__main__ import main
    main()

