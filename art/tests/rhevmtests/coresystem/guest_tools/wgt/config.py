"""
Config module for Guest Tools
"""
import re

from rhevmtests.coresystem.guest_tools.config import *  # flake8: noqa

PRODUCT = 'rhevm'
RHEVM_VERSION = re.search("^\d+.\d+", PRODUCT_BUILD).group(0)
RHEL_VERSION = re.search("^\d+", ENGINE_HOST.os.distribution.version).group(0)
REPO = "http://bob.eng.lab.tlv.redhat.com/builds/latest_%s/el%s/noarch/" % (
    "4.1", RHEL_VERSION  # TODO: fix this when there is WGT in 4.2
)
WESTMERE_CL_CPU_LVL = "Intel Westmere Family"
