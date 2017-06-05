"""
Config module for Guest Tools
"""
import re

from rhevmtests.coresystem.guest_tools.config import *  # flake8: noqa

PRODUCT = 'rhevm'
if PRODUCT_BUILD:
    RHEVM_VERSION = re.search("^\d+.\d+", PRODUCT_BUILD).group(0)
else:
    PRODUCT_BUILD = None

RHEL_VERSION = re.search("^\d+", ENGINE_HOST.os.distribution.version).group(0)
REPO = "http://bob.eng.lab.tlv.redhat.com/builds/latest_%s/el%s/noarch/" % (
    "4.1", RHEL_VERSION  # TODO: fix this when there is WGT in 4.2
)
WESTMERE_CL_CPU_LVL = "Intel Westmere Family"
TIMEZONE = ENUMS['timezone_win_gmt_standard_time']
GUEST_TOOLS_INSTALLED_TIMEOUT = 600

ELEMENTS_CONF = ART_CONFIG['elements_conf']
# WGT
WIN2008R2_64B = ELEMENTS_CONF['Win2008R2_64b']
WIN2012R2_64B = ELEMENTS_CONF['Win2012R2_64b']
WIN2012_64B = ELEMENTS_CONF['Win2012_64b']
WIN7_32B = ELEMENTS_CONF['Win7_32b']
WIN7_64B = ELEMENTS_CONF['Win7_64b']
WIN8_1_32B = ELEMENTS_CONF['Win8_1_32b']
WIN8_1_64B = ELEMENTS_CONF['Win8_1_64b']
WIN8_32B = ELEMENTS_CONF['Win8_32b']
WIN8_64B = ELEMENTS_CONF['Win8_64b']
WIN10_32B = ELEMENTS_CONF['Win10_32b']
WIN10_64B = ELEMENTS_CONF['Win10_64b']
WIN2016_64B = ELEMENTS_CONF['Win2016_64b']
