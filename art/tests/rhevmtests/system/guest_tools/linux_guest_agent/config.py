"""
Config module for Guest Agent
"""

__test__ = False


from rhevmtests.system.guest_tools.config import *  # flake8: noqa
from art.rhevm_api.resources.package_manager import YumPackageManager
from art.rhevm_api.resources.package_manager import APTPackageManager

# images names have to be same as test classes, because we need to have them
# sorted so we can import glance images in corect order
TEST_IMAGES = {
    'rhel5_x86_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YumPackageManager,
        'ip': '10.34.61.85',
    },
    'rhel6_x86_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YumPackageManager,
        'ip': '10.34.61.12',
    },
    'rhel5_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YumPackageManager,
        'ip': '10.34.61.149',
    },
    'rhel6_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YumPackageManager,
        'ip': '10.34.60.82',
    },
    'rhel7.1_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': YumPackageManager,
        'ip': '10.34.60.120',
    },
    'ubuntu-12.04_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'manager': APTPackageManager,
        'ip': '10.34.60.104',
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

PACKAGE_NAME = '%s-common' % GA_NAME

# GA repositories
UBUNTU_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo:/ubuntu:/14.04/xUbuntu_14.04/'
GA_REPO_NAME = 'rhevm_latest'
GA_REPO_URL = 'http://bob.eng.lab.tlv.redhat.com/builds/3.6/%s/%s'

GUEST_ROOT_USER = 'root'
GUEST_ROOT_PASSWORD = '123456'
