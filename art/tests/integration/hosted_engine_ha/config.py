"""
Hosted Engine HA test configuration file
"""
import socket
from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG, opts


################################
# General configuration values #
################################
PARAMETERS = ART_CONFIG["PARAMETERS"]
ENUMS = opts["elements_conf"]["RHEVM Enums"]

# DISK SIZES
MB = 1024 ** 2
GB = 1024 ** 3

# ENGINE SECTION
REST_CONNECTION = ART_CONFIG["REST_CONNECTION"]
VDC_HOST = REST_CONNECTION["host"]
VDC_ROOT_PASSWORD = PARAMETERS.get("vdc_root_password")
VDC_PASSWORD = REST_CONNECTION["password"]
VDC_PORT = REST_CONNECTION["port"]
VDC_ADMIN_USER = REST_CONNECTION["user"]
VDC_ADMIN_DOMAIN = REST_CONNECTION["user_domain"]
ENGINE_ENTRY_POINT = REST_CONNECTION["entry_point"]

# HOSTS
HOSTS = PARAMETERS.as_list("vds")
HOSTS_IP = list(HOSTS)
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
SLAVE_HOST = resources.Host(socket.getfqdn())
SLAVE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)

############################
# Power Management Mapping #
############################
IBM_PM_USERNAME = "USERID"
IBM_PM_PASSWORD = "PASSW0RD"
DELL_PM_USERNAME = "root"
DELL_PM_PASSWORD = "calvin"
HP_PM_USERNAME = "admin"
HP_PM_PASSWORD = "admin"
PM_ADDRESS = "pm_address"
PM_PASSWORD = "pm_password"
PM_USERNAME = "pm_username"
PM_TYPE = "pm_type"
PM_SLOT = "pm_slot"

pm_mapping = dict()

compute_servers = {
    "alma07.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "alma07-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_ipmilan"],
        PM_USERNAME: IBM_PM_USERNAME,
        PM_PASSWORD: IBM_PM_PASSWORD
    },
    "rose05.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "rose05-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_ipmilan"],
        PM_USERNAME: DELL_PM_USERNAME,
        PM_PASSWORD: DELL_PM_PASSWORD
    },
    "master-vds10.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "qabc3-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_bladecenter"],
        PM_USERNAME: IBM_PM_USERNAME,
        PM_PASSWORD: IBM_PM_PASSWORD,
        PM_SLOT: "3"
    },
    "aqua-vds2.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "aqua-vds2-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_ipmilan"],
        PM_USERNAME: DELL_PM_USERNAME,
        PM_PASSWORD: DELL_PM_PASSWORD
    },
    "alma05.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "alma05-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_ilo4"],
        PM_USERNAME: DELL_PM_USERNAME,
        PM_PASSWORD: DELL_PM_PASSWORD
    },
    "alma06.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "alma06-mgmt.qa.lab.tlv.redhat.com",
        PM_TYPE: ENUMS["pm_ilo4"],
        PM_USERNAME: DELL_PM_USERNAME,
        PM_PASSWORD: DELL_PM_PASSWORD
    }
}

puma_servers = dict(
    (
        "puma%d.scl.lab.tlv.redhat.com" % i, {
            PM_ADDRESS: "puma%d-mgmt.qa.lab.tlv.redhat.com" % i,
            PM_TYPE: ENUMS["pm_ipmilan"],
            PM_USERNAME: HP_PM_USERNAME,
            PM_PASSWORD: HP_PM_PASSWORD
        }
    ) for i in xrange(11, 31)
)

cheetah_servers = dict(
    (
        "cheetah0%d.scl.lab.tlv.redhat.com" % i, {
            PM_ADDRESS: "cheetah0%d-mgmt.qa.lab.tlv.redhat.com" % i,
            PM_TYPE: ENUMS["pm_ipmilan"],
            PM_USERNAME: DELL_PM_USERNAME,
            PM_PASSWORD: DELL_PM_PASSWORD
        }
    ) for i in xrange(1, 3)
)

for server_dict in (compute_servers, puma_servers, cheetah_servers):
    pm_mapping.update(server_dict)

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
HOSTED_ENGINE_CONF_FILE_TMP = "/tmp/hosted-engine.conf"

SCORE = "score"
UP_TO_DATE = "live-data"
ENGINE_STATUS = "engine-status"
HOSTNAME = "hostname"
ENGINE_HEALTH = "health"
ENGINE_HEALTH_BAD = "bad"
ENGINE_HEALTH_GOOD = "good"
VM_STATE = "vm"
VM_STATE_UP = "up"
VM_STATE_DOWN = "down"

# Maintenance modes for HE
MAINTENANCE_LOCAL = "local"
MAINTENANCE_GLOBAL = "global"
MAINTENANCE_NONE = "none"

# Dropped scores(BASE_SCORE - PENALTY_SCORE)
MAX_SCORE = 3400
GATEWAY_SCORE = 1800
FREE_MEMORY_SCORE = 3000
CPU_LOAD_SCORE = 2400
ZERO_SCORE = 0

WAIT_TIMEOUT = 600
STOP_TIMEOUT = 300
CPU_SCORE_TIMEOUT = 1200
WAIT_FOR_STATE_TIMEOUT = 1200
POWER_MANAGEMENT_TIMEOUT = 1200
TCP_TIMEOUT = 20
IO_TIMEOUT = 20

SYSTEMD = "Systemd"
BROKER_SERVICE = "ovirt-ha-broker"
AGENT_SERVICE = "ovirt-ha-agent"
VDSM_SERVICE = "vdsmd"

# HE stats script constants
GET_HE_STATS_SCRIPT = "tests/integration/hosted_engine_ha/get_he_stats.py"
SCRIPT_DEST_PATH = "/tmp/get_he_stats.py"

# String constants
VM_NOT_STARTED_ON_SECOND_HOST = "Vm not started on second host"
ENGINE_NOT_STARTED_ON_SECOND_HOST = "Engine not started on second host"
HE_VM_NOT_STARTED = "HE vm not started"
ENGINE_UP = "Engine still alive"
