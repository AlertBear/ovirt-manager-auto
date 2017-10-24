"""
Hosted Engine HA test configuration file
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

HOSTED_ENGINE_CMD = "hosted-engine"
COPY_CMD = "cp"

SAMPLER_TIMEOUT = 600
SAMPLER_SLEEP = 30

IPTABLES_BACKUP_FILE = "/tmp/iptables.backup"
HOSTED_ENGINE_CONF_FILE = "/etc/ovirt-hosted-engine/hosted-engine.conf"
HOSTED_ENGINE_CONF_FILE_BACKUP = "%s.backup" % HOSTED_ENGINE_CONF_FILE

SCORE = "score"
UP_TO_DATE = "live-data"
ENGINE_STATUS = "engine-status"
HE_STATS = [SCORE, UP_TO_DATE, ENGINE_STATUS]
HOSTNAME = "hostname"
ENGINE_HEALTH = "health"
ENGINE_HEALTH_BAD = "bad"
ENGINE_HEALTH_GOOD = "good"
VM_STATE = "vm"
VM_STATE_UP = "up"
HE_VM_STATS = [ENGINE_HEALTH, VM_STATE]

# Maintenance modes for HE
MAINTENANCE_LOCAL = "local"
MAINTENANCE_GLOBAL = "global"
MAINTENANCE_NONE = "none"

# Dropped scores(BASE_SCORE - PENALTY_SCORE)
MAX_SCORE = 3400
GATEWAY_SCORE = 1800
CPU_LOAD_SCORE = 2400
ZERO_SCORE = 0

WAIT_TIMEOUT = 600
STOP_TIMEOUT = 300
CPU_SCORE_TIMEOUT = 1200
WAIT_FOR_STATE_TIMEOUT = 1200
POWER_MANAGEMENT_TIMEOUT = 1200
TCP_TIMEOUT = 20
IO_TIMEOUT = 20

BROKER_SERVICE = "ovirt-ha-broker"
AGENT_SERVICE = "ovirt-ha-agent"

# HE stats script constants
HE_STATS_SCRIPT_NAME = "get_he_stats.py"
SCRIPT_DEST_PATH = "/tmp/get_he_stats.py"

HE_ISCSI_STORAGE_DOMAIN_MSG = "Test does not supported on ISCSI storage"
IS_ISCSI_STORAGE_DOMAIN = False

METADATA_UPDATE_INTERVAL = 60
VM_VDSM_STATE_UP = "Up"

POSTGRESQL_SERVICE = "postgresql"
