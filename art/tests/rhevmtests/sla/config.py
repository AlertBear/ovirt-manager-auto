"""
Configuration file for sla tests package
"""

from rhevmtests.config import *  # flake8: noqa

IBM_PM_USERNAME = 'USERID'
IBM_PM_PASSWORD = 'PASSW0RD'
DELL_PM_USERNAME = 'root'
DELL_PM_PASSWORD = 'calvin'
HP_PM_USERNAME = 'admin'
HP_PM_PASSWORD = 'admin'
PM_ADDRESS = 'pm_address'
PM_PASSWORD = 'pm_password'
PM_USERNAME = 'pm_username'
PM_TYPE = 'pm_type'
PM_SLOT = 'pm_slot'

pm_mapping = dict()

compute_servers = {
    'alma07.qa.lab.tlv.redhat.com': {
        PM_ADDRESS: 'alma07-mgmt.qa.lab.tlv.redhat.com',
        PM_TYPE: ENUMS['pm_ipmilan'],
        PM_USERNAME: IBM_PM_USERNAME,
        PM_PASSWORD: IBM_PM_PASSWORD
    },
    'rose05.qa.lab.tlv.redhat.com': {
        PM_ADDRESS: 'rose05-mgmt.qa.lab.tlv.redhat.com',
        PM_TYPE: ENUMS['pm_ipmilan'],
        PM_USERNAME: DELL_PM_USERNAME,
        PM_PASSWORD: DELL_PM_PASSWORD
    },
    'master-vds10.qa.lab.tlv.redhat.com': {
        PM_ADDRESS: 'qabc3-mgmt.qa.lab.tlv.redhat.com',
        PM_TYPE: ENUMS['pm_bladecenter'],
        PM_USERNAME: IBM_PM_USERNAME,
        PM_PASSWORD: IBM_PM_PASSWORD,
        PM_SLOT: 3
    },
    'aqua-vds2.qa.lab.tlv.redhat.com': {
        PM_ADDRESS: 'aqua-vds2-mgmt.qa.lab.tlv.redhat.com',
        PM_TYPE: ENUMS['pm_ipmilan'],
        PM_USERNAME: DELL_PM_USERNAME,
        PM_PASSWORD: DELL_PM_PASSWORD
    }
}

puma_servers = dict(
    (
        'puma%d.scl.lab.tlv.redhat.com' % i, {
            PM_ADDRESS: 'puma%d-mgmt.qa.lab.tlv.redhat.com' % i,
            PM_TYPE: ENUMS['pm_ipmilan'],
            PM_USERNAME: HP_PM_USERNAME,
            PM_PASSWORD: HP_PM_PASSWORD
        }
    ) for i in xrange(11, 31)
)

cheetah_servers = dict(
    (
        'cheetah0%d.scl.lab.tlv.redhat.com' % i, {
            PM_ADDRESS: 'cheetah0%d-mgmt.qa.lab.tlv.redhat.com' % i,
            PM_TYPE: ENUMS['pm_ipmilan'],
            PM_USERNAME: DELL_PM_USERNAME,
            PM_PASSWORD: DELL_PM_PASSWORD
        }
    ) for i in xrange(1, 3)
)

for server_dict in (compute_servers, puma_servers, cheetah_servers):
    pm_mapping.update(server_dict)


NUM_OF_DEVICES = int(STORAGE_CONF.get("%s_devices" % STORAGE_TYPE_NFS, 0))
STORAGE_NAME = [
    "_".join([STORAGE_TYPE_NFS, str(i)]) for i in xrange(NUM_OF_DEVICES)
]

HOST_VM_MAP = {
    VM_NAME[0]: HOSTS[0],
    VM_NAME[1]: HOSTS[1],
    VM_NAME[2]: HOSTS[2]
} if len(HOSTS) >= 3 else None

HOSTS_WITH_DUMMY = list(HOSTS)
while len(HOSTS_WITH_DUMMY) < 3:
    HOSTS_WITH_DUMMY.append(None)

VM_OS_TYPE = ENUMS['rhel7ppc64'] if PPC_ARCH else ENUMS['rhel6x64']
VM_DISPLAY_TYPE = ENUMS[
    'display_type_vnc'
] if PPC_ARCH else ENUMS['display_type_spice']

DEFAULT_VM_PARAMETERS = {
    'memory': GB,
    'memory_guaranteed': GB,
    'cpu_socket': 1,
    'cpu_cores': 1,
    'os_type': VM_OS_TYPE,
    'type': VM_TYPE_DESKTOP,
    'display_type': VM_DISPLAY_TYPE,
    'placement_affinity': VM_MIGRATABLE,
    'placement_host': VM_ANY_HOST,
    'cluster': CLUSTER_NAME[0],
    'watchdog_model': '',
    'highly_available': False
}

VDS_HOSTS_WITH_DUMMY = list(VDS_HOSTS)
while len(VDS_HOSTS_WITH_DUMMY) < 3:
    VDS_HOSTS_WITH_DUMMY.append(None)
