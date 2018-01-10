"""
SNMP Traps v3 configuration file
"""
from rhevmtests.config import *  # flake8: noqa

# Logs constants
NOTIFIER_LOG = '/var/log/ovirt-engine/notifier/notifier.log'
SNMPD_LOG = "/var/log/snmpd.log"
LOGS_LIST = [NOTIFIER_LOG, SNMPD_LOG]

OVIRT_USER = "ovirt"
OVIRT_GROUP = OVIRT_USER

# SNMP related packages
SNMP_PACKAGES = ["net-snmp-utils", "net-snmp"]

# Services and configuration lists lists
SERVICES = ["snmpd", "snmptrapd", "ovirt-engine-notifier"]
CONFIGURATIONS = [
    "snmptrapd", "snmptrapd_users",
    "snmpd", "ovirt_notifier"
]

NOTIFIER_SERVICE = NOTIFIER_CONFIG = -1

# Disk size for virtual machine constant size
GB = 1024 ** 3
# List of virtual machines names for SNMP test module
snmp_vms_names = ["snmp_vm_{0}".format(i) for i in range(2)]
