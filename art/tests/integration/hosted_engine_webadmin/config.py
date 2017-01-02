"""
HE webadmin test configuration file
"""
import pytest

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG, opts


################################
# General configuration values #
################################
TEST_NAME = "update_HE_VM"

PARAMETERS = ART_CONFIG["PARAMETERS"]
ENUMS = opts["elements_conf"]["RHEVM Enums"]

# DISK SIZES
MB = 1024 ** 2
GB = 1024 ** 3

# ENGINE SECTION
DC_NAME = "Default"
CLUSTER_NAME = "Default"
REST_CONNECTION = ART_CONFIG["REST_CONNECTION"]
VDC_HOST = REST_CONNECTION["host"]
VDC_ROOT_PASSWORD = PARAMETERS.get("vdc_root_password")
VDC_PASSWORD = REST_CONNECTION["password"]
VDC_PORT = REST_CONNECTION["port"]
VDC_ADMIN_USER = REST_CONNECTION["user"]
VDC_ADMIN_DOMAIN = REST_CONNECTION["user_domain"]
ENGINE_ENTRY_POINT = REST_CONNECTION["entry_point"]

# Management network
MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')

# HOSTS
HOSTS = ["hosted_engine_%s" % i for i in xrange(1, 3)]
HOSTS_IP = PARAMETERS.as_list("vds")
HOSTS_PW = PARAMETERS.as_list("vds_password")[0]

# VM STATUSES
VM_UP = ENUMS["vm_state_up"]

# NEW OBJECT ORIENTED APPROACH
VDS_HOSTS = [
    resources.VDS(
        h, HOSTS_PW,
    ) for h in HOSTS_IP
]
OVIRT_SERVICE = "ovirt-engine"
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)
ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        VDC_ADMIN_USER,
        VDC_PASSWORD,
        resources.Domain(VDC_ADMIN_DOMAIN),
    ),
    schema=REST_CONNECTION.get("schema"),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT,
)

HE_VM_NAME = "HostedEngine"
HE_STORAGE_NAME = "hosted_storage"
STORAGE_TYPE = PARAMETERS.get("storage_type")

OVF_UPDATE_INTERVAL = "OvfUpdateIntervalInMinutes"
OVF_UPDATE_INTERVAL_VALUE = 1
WAIT_FOR_OVF_UPDATE = 90

###################################
# Hosted Engine HA test constants #
###################################
HOSTED_ENGINE_CMD = "hosted-engine"

SAMPLER_TIMEOUT = 600
SAMPLER_SLEEP = 30

# Maintenance modes for HE
MAINTENANCE_LOCAL = "local"
MAINTENANCE_GLOBAL = "global"
MAINTENANCE_NONE = "none"

# Test constants
ADDITIONAL_HE_VM_NIC_NAME = "eth1"
EXPECTED_MEMORY = 8 * GB
EXPECTED_CPUS = 4
DEFAULT_CPUS_VALUE = 2
TEST_NETWORK = "test_network"

non_ge = pytest.mark.skipif(
    "prepared_env" in ART_CONFIG,
    reason="Tests not supported on GE"
)
