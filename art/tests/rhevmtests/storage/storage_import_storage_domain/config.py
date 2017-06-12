"""
Config module for storage Import Storage Domain
"""
from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "import_storage_domain"

VM_NAME = "{0}_vm_%s".format(TESTNAME)

# fixture section
DOMAIN_TO_DETACH_AND_REMOVE = None
DOMAIN_TO_REMOVE = None
DC_TO_REMOVE_FROM = DATA_CENTER_NAME

DOMAIN_MOVED = False
