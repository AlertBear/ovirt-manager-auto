"""
Config module for Guest Agent
"""
from rhevmtests.coresystem.guest_tools.config import *  # flake8: noqa

# images names have to be same as test classes, because we need to have them
# sorted so we can import glance images in corect order
TEST_IMAGES = {
    'rhel6_x86_Disk1': {
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
    'ubuntu-16.04_Disk1': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
    'ATOMIC-IMAGE-QE': {
        'image': None,
        'machine': None,
        'id': None,
        'ip': None,
    },
}

RHEL_BASE_IMAGE_NAME = "rhel"
ATOMIC_BASE_IMAGE_NAME = "ATOMIC"

GAINSTALLED_TIMEOUT = 60
GAHOOKS_TIMEOUT = 60
AGENT_SERVICE_NAME = 'ovirt-guest-agent'
UPSTREAM = 'ovirt' in PRODUCT_NAME.lower()

GA_NAME = 'ovirt-guest-agent'
OLD_PACKAGE_NAME = 'ovirt-guest-agent-common'

# GA repositories
UBUNTU_REPOSITORY = 'http://download.opensuse.org/repositories/home:/evilissimo:/ubuntu:/16.04/xUbuntu_16.04/'

GA_REPO_NAME = 'rhevm_latest'
if not UPSTREAM:
    GA_REPO_URL = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_4.2/%s'
else:
    GA_REPO_URL = 'http://resources.ovirt.org/pub/ovirt-master-snapshot/rpm/%s'

GA_REPO_OLDER_NAME = 'rhevm_older'
if not UPSTREAM:
    GA_REPO_OLDER_URL = 'http://bob.eng.lab.tlv.redhat.com/builds/latest_4.1/%s'
else:
    GA_REPO_OLDER_URL = 'http://resources.ovirt.org/repos/ovirt/tested/4.1/rpm/%s'

ATOMIC_REPO_URL = 'brew-pulp-docker01.web.prod.ext.phx2.redhat.com:8888'
ATOMIC_PACKAGE_PATH = '/rhev4/%s' % GA_NAME

GUEST_ROOT_USER = 'root'
GUEST_ROOT_PASSWORD = '123456'

CLOUD_INIT_SCRIPT = """
yum_repos:
    ovirt:
        name: oVirt latest
        baseurl: %s
        enabled: true
        gpgcheck: false
packages:
    ovirt-guest-agent-common
runcmd:
    - [ service, ovirt-guest-agent, restart ]
"""

SSHD_CONFIG_PATH = "/etc/ssh/sshd_config"
ATOMIC_ROOT = "/var/lib/containers/atomic/ovirt-guest-agent.0/rootfs"

ATOMIC_CLOUD_INIT_SCRIPT = """
runcmd:
    - [ atomic, -y, containers, delete, -a ]
    - [ atomic, pull, --storage=ostree, 'http:{url}{path}' ]
    - [ atomic, install, --system, '{url}{path}' ]
    - [ echo, 'ListenAddress 0.0.0.0', '>>', {sshd_config} ]
    - [ echo, 'PermitRootLogin yes', '>>', {sshd_config} ]
    - [ echo, 'PasswordAuthentication yes', '>>', {sshd_config} ]
    - [ systemctl, restart, ovirt-guest-agent, sshd ]
""".format(
    url=ATOMIC_REPO_URL, path=ATOMIC_PACKAGE_PATH,
    password=GUEST_ROOT_PASSWORD, sshd_config=SSHD_CONFIG_PATH
)

MIGRATION_POLICY_LEGACY = '00000000-0000-0000-0000-000000000000'
MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED = '80554327-0569-496b-bdeb-fcbbf52b827c'
