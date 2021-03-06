"""
HE webadmin test configuration file
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

HOSTED_ENGINE_CMD = "hosted-engine"

SAMPLER_TIMEOUT = 600
UPDATE_HE_STATS_TIMEOUT = 120
SAMPLER_SLEEP = 30

# Maintenance modes for HE
MAINTENANCE_NONE = "none"
MAINTENANCE_GLOBAL = "global"

PARAMS_HE_GLOBAL_MAINTENANCE = "global_maintenance"
PARAMS_HE_LOCAL_MAINTENANCE = "local_maintenance"
PARAMS_HE_SCORE = "score"

# Test constants
ADDITIONAL_HE_VM_NIC_NAME = "eth1"
EXPECTED_MEMORY = 8 * GB
EXPECTED_CPUS = None
TEST_NETWORK = "test_network"

HE_VM_MAX_MEMORY = 16 * GB

INIT_HE_VM_CPUS = None

TEST_PARAMS_QUOTA_NAME = "he_quota"

SLEEP_OVF_UPDATE = 60
SLEEP_SANLOCK_UPDATE = 60
