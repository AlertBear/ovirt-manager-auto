"""
Config module for Guest Tools
"""
import re

from rhevmtests.system.guest_tools.config import *  # flake8: noqa

__test__ = False

PRODUCT = 'rhevm'
RHEVM_VERSION = re.search("^\d+.\d+", PRODUCT_BUILD).group(0)
RHEL_VERSION = re.search("^\d+", ENGINE_HOST.os.distribution.version).group(0)
REPO = "http://bob.eng.lab.tlv.redhat.com/builds/latest_%s/el%s/noarch/" % (
    RHEVM_VERSION, RHEL_VERSION
)
