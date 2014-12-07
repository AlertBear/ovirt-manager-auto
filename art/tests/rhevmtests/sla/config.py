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
    }
}

puma_servers = dict(
    (
        'puma%d.scl.lab.tlv.redhat.com' % i, {
            PM_ADDRESS: 'puma%d-mgmt.qa.lab.tlv.redhat.com' % i,
            PM_TYPE: ENUMS['pm_ilo4'],
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
