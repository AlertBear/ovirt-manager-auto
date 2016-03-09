"""
Consolidated network config module
"""

__test__ = False

from rhevmtests.config import *  # flake8: noqa
from collections import OrderedDict
from random import randint
import art.test_handler.exceptions as exceptions

# Global parameters
STORAGE_TYPE = "nfs"
EXTRA_DC = ["_".join(["EXTRA_DC", str(i)]) for i in range(6)]
EXTRA_CL = ["".join(["NET_Cluster", str(i)]) for i in range(5)]
MTU = [9000, 5000, 2000, 1500]
NETMASK = '255.255.255.0'
VNIC_PROFILE = PARAMETERS.as_list('vnic_profile')
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
NETWORKS = PARAMETERS.as_list('networks')
TIMEOUT = 60
NET_EXCEPTION = exceptions.NetworkException
DEFAULT_MAC_POOL = "Default"
VM_NICS = ['eth0', 'eth1', 'eth2', 'eth3']
FIREWALL_SRV = "iptables"
BOND_MODES = PARAMETERS.as_list("bond_modes")
LABEL_LIST = ["_".join(["label", str(elm)]) for elm in range(10)]
DUMMY_0 = "dummy_0"
DUMP_TIMEOUT = TIMEOUT * 4
DC_0 = DC_NAME[0]
CL_0 = CLUSTER_NAME[0]
CL_1 = CLUSTER_NAME[1]
PASSTHROUGH_INTERFACE = "pci_passthrough"
VM_0 = VM_NAME[0]
VM_1 = VM_NAME[1]
HOST_0_NICS = None  # Filled in test
VDS_0_HOST = None  # Filled in test
HOST_0_NAME = None  # Filled in test
HOST_0_IP = None  # Filled in test
HOST_1_NICS = None  # Filled in test
VDS_1_HOST = None  # Filled in test
HOST_1_NAME = None  # Filled in test
HOST_1_IP = None  # Filled in test

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
RX_CHECKSUM = "-K {nic} rx {state}"

# MultiHost and multiple_gw parameters
SUBNET = "5.5.5.0"
MG_GATEWAY = "5.5.5.254"
MG_IP_ADDR = "5.5.5.1"

# Jumbo frame parameters
NUM_PACKETS = 1000
INTER_SUBNET = '3.3.3.'
IPS = ['3.3.3.1', '3.3.3.2']
SEND_MTU = [4500, 8500, 1500, 1000]
SOURCE_IP = '100.1.1.1'
DEST_IP = '100.1.1.2'
GATEWAY = '3.3.3.254'
TRAFFIC_TIMEOUT = 120
VM_IP_LIST = []

# Import/Export parameters
NAME_INT = randint(1, 100)
IE_VM = "IE_VM_%s" % NAME_INT
IE_TEMPLATE = "IE_TEMP_%s" % NAME_INT
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM_%s" % NAME_INT
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE_%s" % NAME_INT
EXPORT_TYPE = ENUMS['storage_dom_type_export']

# Topologies parameters
# Due to the switch configuration with specific IP
# https://engineering.redhat.com/rt/Ticket/Display.html?id=336074
ADDR_AND_MASK = ["10.35.147.50", "255.255.255.240"]
DST_HOST_IP = "10.35.147.62"

# Port mirroring parameters
PM_VNIC_PROFILE = ['%s_PM' % net for net in [MGMT_BRIDGE] + VLAN_NETWORKS]
NUM_VMS = 5
MGMT_IPS = []  # Gets filled up during the test
NET1_IPS = [
    '5.5.%s.%s' % (
        randint(1, 250), randint(1, 250)
    ) for i in range(NUM_VMS + 1)
]
NET2_IPS = [
    '6.6.%s.%s' % (
        randint(1, 250), randint(1, 250)
    ) for i in range(NUM_VMS + 1)
]

# Queues parameters
NUM_QUEUES = [5, 6]
PROP_QUEUES = ["=".join(["queues", str(i)]) for i in NUM_QUEUES]
VM_FROM_TEMPLATE = "vm_from_queues_template"

# Big MAC pool range
BMPR_VM_NAME = "BigRangeMacPool_VM1"
MAC_POOL_RANGE_CMD = "MacPoolRanges"

# PPC
VM_DISPLAY_TYPE = ENUMS[
    "display_type_vnc"
] if PPC_ARCH else ENUMS["display_type_spice"]

# QoS parameters
QOS_TEST_VALUE = 10
HOST_NET_QOS_TYPE = "hostnetwork"
NET_QOS_TYPE = "network"

# libvirt
LIBVIRTD_CONF = "/etc/libvirt/libvirtd.conf"
SASL_OFF = "none"
SASL_ON = "sasl"

# MAC pool range
MAC_POOL_RANGE_LIST = [
    ("00:00:00:10:10:10", "00:00:00:10:10:11"),
    ("00:00:00:20:10:10", "00:00:00:20:10:12"),
    ("00:00:00:30:10:10", "00:00:00:30:10:12")
]
EXT_DC_1 = EXTRA_DC[1]

# Management network as role
EXT_DC_0 = EXTRA_DC[0]
EXTRA_CLUSTER_0 = EXTRA_CL[0]
