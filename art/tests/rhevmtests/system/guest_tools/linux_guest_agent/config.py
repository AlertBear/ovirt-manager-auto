"""
Config module for Guest Agent
"""

__test__ = False

from utilities.enum import Enum
from rhevmtests.system.guest_tools.config import *  # flake8: noqa


eOS = Enum(RHEL_6_64b='RHEL_6_64b', RHEL_6_32b='RHEL_6_32b',
           RHEL_5_64b='RHEL_5_64b', RHEL_5_32b='RHEL_5_32b',
           UBUNTU_14_04_64b='UBUNTU_14_04_64b',
           SUSE_13_1_64b='SUSE_13_1_64b')
TEST_NAME = "RHEL_guest_agent"
INSTALL_TIMEOUT = PARAMETERS.get('install_timeout', 480)
TIMEOUT = PARAMETERS.get('timeout', 320)

TEMPLATES = {eOS.RHEL_6_64b: {'name': 'rhel6_x64'},
             eOS.RHEL_6_32b: {'name': 'rhel6_x86'},
             eOS.RHEL_5_64b: {'name': 'rhel5_x64'},
             eOS.RHEL_5_32b: {'name': 'rhel5_x86'},
             eOS.UBUNTU_14_04_64b: {'name': 'ubuntu_14_04'}}

AGENT_SERVICE_NAME = 'ovirt-guest-agent'

# TCMS plans
TCMS_PLAN_ID_RHEL = 3146
TCMS_PLAN_ID_UBUNTU = 12286
TCMS_PLAN_ID_SUSE = 12287

# GA repositories
UBUNTU_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo:/ubuntu:/14.04/xUbuntu_14.04/'
SUSE_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo/openSUSE_13.1/home:evilissimo.repo'
RHEL_REPOSITORY = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_is/'
RHEL_BEFORE_REPOSITORY = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_is/'
