"""
Consolidated network config module
"""

__test__ = False

from rhevmtests.config import *  # flake8: noqa
from collections import OrderedDict
from random import randint

# Adjust parameters if running on golden environment
if GOLDEN_ENV:
    STORAGE_TYPE = "nfs"
    VDS_HOSTS = [resources.VDS(h, HOSTS_PW) for h in HOSTS_IP]
else:
    HOSTS_IP = [host.ip for host in VDS_HOSTS]

# Global parameters
EXTRA_DC = "NET_DC_2"
MTU = [9000, 5000, 2000, 1500]
NETMASK = '255.255.255.0'
VNIC_PROFILE = PARAMETERS.as_list('vnic_profile')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
NETWORKS = PARAMETERS.as_list('networks')
TIMEOUT = 60

# Network Custom Priority parameters
BRIDGE_OPTS = OrderedDict({"priority": ["32768", "1"],
                           "multicast_querier": ["0", "1"]})
KEY1 = BRIDGE_OPTS.keys()[0]
KEY2 = BRIDGE_OPTS.keys()[1]
PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][1]])
DEFAULT_PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][0]])
MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][1]])
DEFAULT_MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][0]])
TX_CHECKSUM = "-K {nic} tx {state}"
AUTONEG = "-A {nic} autoneg {state}"

# Network Migration
NM_SOURCE_IP = '5.5.5.10'
NM_DEST_IP = '5.5.5.20'

# MultiHost and multiple_gw parameters
SUBNET = "1.1.1.0"
MG_GATEWAY = "1.1.1.254"
MG_IP_ADDR = "1.1.1.1"

# Network migration parameters
FIREWALL_SRV = "iptables"

# Jumbo frame parameters
VM_NICS = ['eth0', 'eth1', 'eth2', 'eth3']
NUM_PACKETS = 1000
INTER_SUBNET = '3.3.3.'
IPS = ['3.3.3.1', '3.3.3.2']
SEND_MTU = [4500, 8500, 1500, 1000]
SOURCE_IP = '100.1.1.1'
DEST_IP = '100.1.1.2'
GATEWAY = '3.3.3.254'
TRAFFIC_TIMEOUT = 120
J_VLAN_NETWORKS = ['sw201', 'sw202', 'sw203', 'sw204', 'sw205']
J_VLAN_ID = ['201', '202', '203', '204', '205']

# Import/Export parameters
IE_VM = "IE_VM"
IE_TEMPLATE = "IE_TEMP"
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM"
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE"
EXPORT_TYPE = ENUMS['storage_dom_type_export']
# take following parameters from global config:
# EXPORT_STORAGE_NAME, EXPORT_STORAGE_ADDRESS, EXPORT_STORAGE_PATH

# Topologies parameters
# Due to the switch configuration with specific IP
# https://engineering.redhat.com/rt/Ticket/Display.html?id=336074
ADDR_AND_MASK = ["10.35.147.50", "255.255.255.240"]
DST_HOST_IP = "10.35.147.62"

# Port mirroring parameters
PM_VNIC_PROFILE = ['%s_PM' % net for net in [MGMT_BRIDGE] + VLAN_NETWORKS]
NUM_VMS = 5
MGMT_IPS = []  # Gets filled up during the test
NET1_IPS = ['5.5.%s.%s' % (
    randint(1, 250), randint(1, 250)) for i in range(NUM_VMS + 1)]
NET2_IPS = ['6.6.%s.%s' % (
    randint(1, 250), randint(1, 250)) for i in range(NUM_VMS + 1)]

# Topologies parameters
BOND_MODES = PARAMETERS.as_list("bond_modes")

# Labels parameters
LABEL_LIST = ["_".join(["label", str(elm)]) for elm in range(10)]

# Queues parameters
NUM_QUEUES = [5, 6]
PROP_QUEUES = ["=".join(["queues", str(i)]) for i in NUM_QUEUES]
VM_FROM_TEMPLATE = "vm_from_queues_template"

# Big MAC pool range
BMPR_VM_NAME = "BigRangeMacPool_VM1"
MAC_POOL_RANGE_CMD = "MacPoolRanges"
