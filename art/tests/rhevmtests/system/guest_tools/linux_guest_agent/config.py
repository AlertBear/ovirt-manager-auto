"""
Config module for Guest Agent
"""
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

GAINSTALLED_TIMEOUT = 60
GAHOOKS_TIMEOUT = 60
AGENT_SERVICE_NAME = 'ovirt-guest-agent'
UPSTREAM = 'ovirt' in PRODUCT_NAME.lower()

GA_NAME = 'ovirt-guest-agent'
OLD_GA_NAME = 'rhevm-guest-agent'

# GA repositories
UBUNTU_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo:/ubuntu:/14.04/xUbuntu_14.04/'

GA_REPO_NAME = 'rhevm_latest'
if not UPSTREAM:
    GA_REPO_URL = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_4.1/%s'
else:
    GA_REPO_URL = 'http://resources.ovirt.org/repos/ovirt/tested/4.1/rpm/%s'

GA_REPO_OLDER_NAME = 'rhevm_older'
if not UPSTREAM:
    GA_REPO_OLDER_URL = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_4.0/%s'
else:
    GA_REPO_OLDER_URL = 'http://resources.ovirt.org/repos/ovirt/tested/4.0/rpm/%s'

GUEST_ROOT_USER = 'root'
GUEST_ROOT_PASSWORD = '123456'

MIGRATION_POLICY_LEGACY = '00000000-0000-0000-0000-000000000000'
MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED = '80554327-0569-496b-bdeb-fcbbf52b827c'
