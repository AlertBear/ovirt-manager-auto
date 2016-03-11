"""
Config module for Guest Agent
"""

__test__ = False


from rhevmtests.system.guest_tools.config import *  # flake8: noqa

# images names have to be same as test classes, because we need to have them
# sorted so we can import glance images in corect order
TEST_IMAGES = {
    'rhel5_x86_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
    'rhel6_x86_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
    'rhel5_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
    'rhel6_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
    'rhel7_x64_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
    'ubuntu-12.04_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
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
GA_REPO_OLDER_NAME = 'rhevm_older'
GA_REPO_OLDER_URL = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_vt/%s'

GUEST_ROOT_USER = 'root'
GUEST_ROOT_PASSWORD = '123456'
