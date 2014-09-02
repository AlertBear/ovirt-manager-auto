"""
Consolidated network config module
"""

__test__ = False

from rhevmtests.config import *  # flake8: noqa
from collections import OrderedDict
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import vms

# Adjust parameters if running on golden environment
if GOLDEN_ENV:
    HOSTS = [host.name for host in NETWORK_HOSTS]
    DC_NAME = [hosts.getHostDC(HOSTS[0])]
    CLUSTER_NAME = [hosts.getHostCluster(HOSTS[0])]
    VM_NAME = vms.get_vms_from_cluster(CLUSTER_NAME[0])

# Global parameters
MTU = [9000, 5000, 2000, 1500]
VNIC_PROFILE = PARAMETERS.as_list('vnic_profile')
NETMASK = '255.255.255.0'
VLAN_NETWORKS = PARAMETERS.as_list('vlan_networks')
VLAN_ID = PARAMETERS.as_list('vlan_id')
BOND = PARAMETERS.as_list('bond')
NETWORKS = PARAMETERS.as_list('networks')

# Network Custom Priority parameters
BRIDGE_OPTS = OrderedDict({"priority": ["32768", "1"],
                           "multicast_querier": ["0", "1"]})
KEY1 = BRIDGE_OPTS.keys()[0]
KEY2 = BRIDGE_OPTS.keys()[1]
PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][1]])
DEFAULT_PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][0]])
MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][1]])
DEFAULT_MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][0]])

# Network Migration
NM_SOURCE_IP = '101.1.1.1'
NM_DEST_IP = '101.1.1.2'

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
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM"
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE"
EXPORT_TYPE = ENUMS['storage_dom_type_export']
EXPORT_STORAGE_NAME = "Export"
EXPORT_STORAGE_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_STORAGE_PATH = PARAMETERS.as_list('export_domain_path')[0]

# Topologies parameters
ADDR_AND_MASK = ["172.16.200.100", "255.255.255.0"]
DST_HOST_IP = "172.16.200.2"

# Port mirroring parameters
PM_VNIC_PROFILE = ['%s_PM' % net for net in [MGMT_BRIDGE] + VLAN_NETWORKS]
NUM_VMS = 5
MGMT_IPS = []  # Gets filled up during the test
NET1_IPS = ['5.5.5.1%s' % i for i in range(NUM_VMS + 1)]
NET2_IPS = ['6.6.6.1%s' % i for i in range(NUM_VMS + 1)]
NET2_TEMP_IP = '6.6.6.100'

# Topologies parameters
BOND_MODES = PARAMETERS.as_list("bond_modes")

# Labels parameters
LABEL_LIST = ["_".join(["label", str(elm)]) for elm in range(10)]
