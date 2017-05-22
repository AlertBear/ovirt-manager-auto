"""
Hosted Engine HA test configuration file
"""
import socket

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG, opts

################################
# General configuration values #
################################
GE = "prepared_env" in ART_CONFIG
PARAMETERS = ART_CONFIG["PARAMETERS"]
ENUMS = opts["elements_conf"]["RHEVM Enums"]

# ENGINE SECTION
DC_NAME = "Default"
CLUSTER_NAME = "Default"
REST_CONNECTION = ART_CONFIG["REST_CONNECTION"]
VDC_HOST = REST_CONNECTION["host"]
VDC_ROOT_PASSWORD = PARAMETERS.get("vdc_root_password")

# HOSTS
HOST_STATUS_UP = ENUMS["host_state_up"]
HOSTS = []
VDS_HOSTS = []
HOSTS_IP = []
HE_HOSTS = []
HOSTS_PW = PARAMETERS.as_list("vds_password")[0]
if not GE:
    HOSTS = ["hosted_engine_%s" % i for i in xrange(1, 3)]
    HOSTS_IP = PARAMETERS.as_list("vds")

# VM STATUSES
VM_UP = ENUMS["vm_state_up"]

OVIRT_SERVICE = "ovirt-engine"
POSTGRESQL_SERVICE = "postgresql"
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)
SLAVE_HOST = resources.Host(socket.getfqdn())
SLAVE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)

############################
# Power Management Mapping #
############################
IBM_PM_USERNAME = "USERID"
IBM_PM_PASSWORD = "PASSW0RD"
PM_ADDRESS = "pm_address"
PM_PASSWORD = "pm_password"
PM_USERNAME = "pm_username"
PM_TYPE = "pm_type"
PM_SLOT = "pm_slot"

# FOREMAN DETAILS
FOREMAN_URL = PARAMETERS.get('foreman_url')
FOREMAN_USER = PARAMETERS.get('foreman_user')
FOREMAN_PASSWD = PARAMETERS.get('foreman_password')

PMS = {
    "master-vds10.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "qabc3-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_bladecenter"],
        PM_USERNAME: IBM_PM_USERNAME,
        PM_PASSWORD: IBM_PM_PASSWORD,
        PM_SLOT: "5"
    }
}


###################################
# Hosted Engine HA test constants #
###################################
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

ISCSI_STORAGE_DOMAIN = "iscsi"
HE_ISCSI_STORAGE_DOMAIN_MSG = "Test does not supported on ISCSI storage"

IS_ISCSI_STORAGE_DOMAIN = False

METADATA_UPDATE_INTERVAL = 60
VM_VDSM_STATE_UP = "Up"

# Auto-import constants
HE_VM_NAME = "HostedEngine"
HE_STORAGE_NAME = "hosted_storage"
STORAGE_TYPE = PARAMETERS.get("storage_type")

HA_VM_NAME = "golden_env_mixed_virtio_0"
MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge')
