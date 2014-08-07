"""
Config module for Guest Tools
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

from rhevmtests.system.guest_tools.config import *  # flake8: noqa

WINXP_TOOLS_DICT = '{"RHEV-Tools":"3.2.8", "RHEV-Agent":"3.2.5",\
                     "RHEV-Serial":"3.2.4", "RHEV-Network":"3.2.4",\
                     "RHEV-Spice-Agent":"3.2.5", "RHEV-USB":"3.2.3",\
                     "RHEV-SSO":"3.2.4", "RHEV-Spice":"3.2.3"}'
WIN7_TOOLS_DICT = '{ "RHEV-Tools":"3.2.8", "RHEV-Agent":"3.2.5",\
                     "RHEV-Serial":"3.2.4", "RHEV-Network":"3.2.4",\
                     "RHEV-Spice-Agent":"3.2.5", "RHEV-USB":"3.2.3",\
                     "RHEV-SSO":"3.2.4", "RHEV-Spice":"3.2.3"}'
SKIP_INSTALL = 1
SKIP_UNINSTALL = 0
