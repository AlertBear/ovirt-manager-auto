"""
Config module for Guest Agent
"""

__test__ = False


from utilities.enum import Enum
from rhevmtests.system.guest_tools.config import *  # flake8: noqa

YUM = '/usr/bin/yum'
APT = '/usr/bin/apt-get'

# images names have to be same as test classes, because we need to have them
# sorted so we can import glance images in corect order
TEST_IMAGES = {
    'rhel5_x86_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YUM,
    },
    'rhel6_x86_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YUM,
    },
    'rhel5_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YUM,
    },
    'rhel6_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YUM,
    },
    'ubuntu-12.04_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': APT,
    },
}

INSTALL_TIMEOUT = PARAMETERS.get('install_timeout', 480)
TIMEOUT = PARAMETERS.get('timeout', 320)
AGENT_SERVICE_NAME = 'ovirt-guest-agent'
UPSTREAM = 'ovirt' in PRODUCT_NAME.lower()

if UPSTREAM:
    GA_NAME = 'ovirt-guest-agent'
else:
    GA_NAME = 'rhevm-guest-agent'

# TCMS plans
TCMS_PLAN_ID_RHEL = 3146
TCMS_PLAN_ID_UBUNTU = 12286
TCMS_PLAN_ID_SUSE = 12287

# GA repositories
UBUNTU_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo:/ubuntu:/14.04/xUbuntu_14.04/'
SUSE_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo/openSUSE_13.1/home:evilissimo.repo'
RHEL_GA_RPM = 'http://bob.eng.lab.tlv.redhat.com/builds/3.6/3.6.0/latest_3.6.0/ovirt-release-master-latest.master.noarch.rpm'

GUEST_ROOT_USER = 'root'
GUEST_ROOT_PASSWORD = '123456'
