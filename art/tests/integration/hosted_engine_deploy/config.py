"""
HE Deploy test configuration file
"""
from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG


################################
# General configuration values #
################################
PARAMETERS = ART_CONFIG["PARAMETERS"]

# HOSTS
HOSTS = PARAMETERS.as_list("vds")
HOSTS_IP = list(HOSTS)
HOSTS_PW = PARAMETERS.as_list("vds_password")[0]

# NEW OBJECT ORIENTED APPROACH
VDS_HOSTS = [
    resources.VDS(
        h, HOSTS_PW,
    ) for h in HOSTS_IP
]

MGMT_BRIDGE = PARAMETERS.get("mgmt_bridge")

#######################################
# Hosted Engine Deploy test constants #
#######################################
HOSTED_ENGINE_CMD = "hosted-engine"
HOSTED_ENGINE_HA_PACKAGE = "ovirt-hosted-engine-ha"
HOSTED_ENGINE_SETUP_PACKAGE = "ovirt-hosted-engine-setup"
HOSTED_ENGINE_ENV_DEFAULT = "/etc/ovirt-hosted-engine-setup.env.d/rhevm_qe.env"

# Services constants
OVIRT_HA_AGENT_SERVICE = "ovirt-ha-agent"
OVIRT_HA_BROKER_SERVICE = "ovirt-ha-broker"

# Sampler constants
SAMPLER_HOST_REBOOT_SLEEP = 30
SAMPLER_HOST_REBOOT_TIMEOUT = 600

SAMPLER_REPROVISION_SLEEP = 60
SAMPLER_REPROVISION_TIMEOUT = 3600

SAMPLER_ENGINE_START_SLEEP = 30
SAMPLER_ENGINE_START_TIMEOUT = 600

# Deploy methods constants
DISK_DEPLOY = "disk"

# Appliance constants
APPLIANCE_PATH = None
RHEVM_APPLIANCE_PACKAGE = "rhevm-appliance"
RHEL_RHEVM_APPLIANCE_DIR = "/tmp"
RHEVH_RHEVM_APPLIANCE_DIR = "/data"
APPLIANCE_OVA_URL = PARAMETERS.get("rhevm_appliance_url", "")

# Network constants
VDS_ACTIVE_INTERFACES = [
    vds_resource.get_network().find_int_by_ip(
        vds_resource.ip
    ) for vds_resource in VDS_HOSTS
]
VDS_DEFAULT_GATEWAY = [
    vds_resource.get_network().find_default_gw() for vds_resource in VDS_HOSTS
]

# Host constants
AMD_MODEL = "model_Opteron_G1"
INTEL_MODEL = "model_Conroe"

# Storage constants
STORAGE_PARAMETERS = ART_CONFIG["STORAGE_PARAMETERS"]
HOSTED_ENGINE_DISK_SIZE = 60

ISCSI_TYPE = "iscsi"
ISCSI_USER = STORAGE_PARAMETERS.get("iscsi_user", "")
ISCSI_SERVER = STORAGE_PARAMETERS["iscsi_server"]
ISCSI_PORTAL_IP = STORAGE_PARAMETERS["iscsi_portal_ip"]
ISCSI_DEFAULT_PORT = "3260"
ISCSI_INITIATOR_FILE = "/etc/iscsi/initiatorname.iscsi"
ISCSI_PASSWORD = STORAGE_PARAMETERS.get("iscsi_password", "")

NFS_TYPE = "nfs"
NFS3_TYPE = "nfs3"
NFS4_TYPE = "nfs4"
DEFAULT_VOL_NFS = "nfs01/"

STORAGE_CLASS_D = {
    NFS_TYPE: "NFSStorage",
    ISCSI_TYPE: "ISCSIStorage"
}

# VM constants
VM_PARAMETERS = ART_CONFIG["VM_PARAMETERS"]

VM_FQDN = VM_PARAMETERS["vm_fqdn"]
VM_DOMAIN = ".".join(VM_FQDN.split(".")[1:])
VM_MAC_ADDRESS = VM_PARAMETERS["vm_mac_address"]

# Engine constants
REST_CONNECTION = ART_CONFIG["REST_CONNECTION"]

VDC_PORT = REST_CONNECTION["port"]
VDC_PASSWORD = REST_CONNECTION["password"]
VDC_ADMIN_USER = REST_CONNECTION["user"]
VDC_ADMIN_DOMAIN = REST_CONNECTION["user_domain"]
VDC_ROOT_PASSWORD = PARAMETERS["vdc_root_password"]
ENGINE_ENTRY_POINT = REST_CONNECTION["entry_point"]

ENGINE_HOST = resources.Host(VM_FQDN)
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

# Answer file constants
ANSWER_FILE_PATH = "/tmp/temp_answer_file.conf"
ANSWER_FILE_HEADER = "[environment:default]"

ANSWER_SECTION_OVEHOSTED_VM = "OVEHOSTED_VM"
ANSWER_SECTION_OVEHOSTED_CORE = "OVEHOSTED_CORE"
ANSWER_SECTION_OVEHOSTED_VDSM = "OVEHOSTED_VDSM"
ANSWER_SECTION_OVEHOSTED_NOTIF = "OVEHOSTED_NOTIF"
ANSWER_SECTION_OVEHOSTED_ENGINE = "OVEHOSTED_ENGINE"
ANSWER_SECTION_OVEHOSTED_NETWORK = "OVEHOSTED_NETWORK"
ANSWER_SECTION_OVEHOSTED_STORAGE = "OVEHOSTED_STORAGE"
ANSWER_SECTION_OVEHOSTED_FIRST_HOST = "OVEHOSTED_FIRST_HOST"


DEFAULT_ANSWER_FILE_D = {
    ANSWER_SECTION_OVEHOSTED_VM: {
        "vmMemSizeMB": 4096,
        "vmBoot": DISK_DEPLOY,
        "vmVCpus": 2,
        "vmMACAddr": VM_MAC_ADDRESS,
        "automateVMShutdown": True,
        "cloudinitInstanceHostName": VM_FQDN,
        "cloudinitInstanceDomainName": VM_DOMAIN,
        "cloudinitExecuteEngineSetup": True,
        "cloudinitVMStaticCIDR": False,
        "cloudInitISO": "generate",
        "cloudinitVMETCHOSTS": False,
        "cloudinitVMDNS": False,
        "cloudinitRootPwd": "qum5net"
    },
    ANSWER_SECTION_OVEHOSTED_CORE: {
        "screenProceed": True,
        "deployProceed": True,
        "confirmSettings": True
    },
    ANSWER_SECTION_OVEHOSTED_VDSM: {
        "consoleType": "vnc"
    },
    ANSWER_SECTION_OVEHOSTED_NOTIF: {
        "smtpPort": "25",
        "smtpServer": "localhost",
        "sourceEmail": "root@localhost",
        "destEmail": "root@localhost"
    },
    ANSWER_SECTION_OVEHOSTED_ENGINE: {
        "clusterName": "Default",
        "adminPassword": "123456",
        "appHostName": VDS_HOSTS[0].fqdn
    },
    ANSWER_SECTION_OVEHOSTED_NETWORK: {
        "fqdn": VM_FQDN,
        "bridgeName": MGMT_BRIDGE,
        "firewallManager": "iptables"
    },
    ANSWER_SECTION_OVEHOSTED_STORAGE: {
        "imgSizeGB": 50,
        "storageDomainName": "hosted_storage",
        "storageDatacenterName": "hosted_datacenter"
    }
}

ADDITIONAL_HOST_SPECIFIC_PARAMETERS = {
    ANSWER_SECTION_OVEHOSTED_CORE: {
        "isAdditionalHost": True
    },
    ANSWER_SECTION_OVEHOSTED_FIRST_HOST: {
        "fetchAnswer": True,
        "fqdn": VDS_HOSTS[0].fqdn
    }
}

ISCSI_SPECIFIC_PARAMETERS = {
    "domainType": ISCSI_TYPE,
    "iSCSIPortalIPAddress": ISCSI_PORTAL_IP,
    "iSCSIPortalPort": ISCSI_DEFAULT_PORT,
    "iSCSIPortalUser": ISCSI_USER,
    "iSCSIPortalPassword": ISCSI_PASSWORD
}

NFS_SPECIFIC_PARAMETERS = {
    "domainType": NFS3_TYPE
}

HOSTED_ENGINE_DEPLOY_CMD = [
    HOSTED_ENGINE_CMD, "--deploy", "--config-append=%s" % ANSWER_FILE_PATH
]

# Machine dialog constants
ANSWER_NO = "No"
ANSWER_YES = "Yes"
DEFAULT_ANSWER = ""

# Otopi event constants
EVENT_NAME = "name"
EVENT_VALUE = "value"
ATTRIBUTE_NOTE = "note"
ATTRIBUTE_RECORD = "record"

# RHEVH constants
RHEVH = "Red Hat Enterprise Virtualization Hypervisor"
RHEVH_FLAG = VDS_HOSTS[0].get_os_info()["dist"] == RHEVH

# Engine health page constant
ENGINE_HEALTH_PAGE_URL = "http://%s/ovirt-engine/services/health" % VM_FQDN
