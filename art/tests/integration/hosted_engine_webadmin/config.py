"""
HE webadmin test configuration file
"""

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG


################################
# General configuration values #
################################
GE = "prepared_env" in ART_CONFIG
PARAMETERS = ART_CONFIG["PARAMETERS"]

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
# HOSTS
HOSTS = []
VDS_HOSTS = []
HOSTS_IP = []
HE_HOSTS = []
HOSTS_PW = PARAMETERS["vds_password"][0]
if not GE:
    HOSTS = ["hosted_engine_%s" % i for i in xrange(1, 3)]
    HOSTS_IP = PARAMETERS["vds"]

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
    schema=REST_CONNECTION.get("scheme"),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT,
)

HE_VM_NAME = "HostedEngine"
HE_SD_NAME = "hosted_storage"
STORAGE_TYPE = PARAMETERS.get("storage_type")

OVF_UPDATE_INTERVAL = "OvfUpdateIntervalInMinutes"
OVF_UPDATE_INTERVAL_VALUE = 1
DEFAULT_OVF_UPDATE_INTERVAL_VALUE = 60
WAIT_FOR_OVF_UPDATE = 90

###################################
# Hosted Engine HA test constants #
###################################
HOSTED_ENGINE_CMD = "hosted-engine"

SAMPLER_TIMEOUT = 600
UPDATE_HE_STATS_TIMEOUT = 120
SAMPLER_SLEEP = 30

# Maintenance modes for HE
MAINTENANCE_NONE = "none"
MAINTENANCE_GLOBAL = "global"

# Test constants
ADDITIONAL_HE_VM_NIC_NAME = "eth1"
EXPECTED_MEMORY = 8 * GB
EXPECTED_CPUS = None
TEST_NETWORK = "test_network"

MAX_MEMORY = "max_memory"
VM_MEMORY_GUARANTEED = "memory_guaranteed"
HE_VM_MAX_MEMORY = 16 * GB

INIT_HE_VM_CPUS = None
