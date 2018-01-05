"""
config module for host regression test
"""
from rhevmtests.coresystem.config import *  # flake8: noqa

PM1_ADDRESS = '10.35.35.35'
PM2_ADDRESS = '10.11.11.11'
PM_TYPE_DEFAULT = 'apc'
PM1_USER = 'user1'
PM2_USER = 'user2'
PM1_PASS = 'pass1'
PM2_PASS = 'pass2'

HOST_WITHOUT_HE = None  # Filled in setup fixture
