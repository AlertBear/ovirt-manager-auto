"""
SNMP Traps v3 configuration file
"""
import logging

from art.rhevm_api.resources import Host, RootUser, Engine, ADUser, Domain
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.test_handler.settings import ART_CONFIG as art_config
from art.test_handler.settings import GE

# Logs constants
NOTIFIER_LOG = '/var/log/ovirt-engine/notifier/notifier.log'
SNMPD_LOG = "/var/log/snmpd.log"
LOGS_LIST = [NOTIFIER_LOG, SNMPD_LOG]

OVIRT_USER = "ovirt"
OVIRT_GROUP = OVIRT_USER

# SNMP related packages
SNMP_PACKAGES = ["net-snmp-utils", "net-snmp"]

# Services and configuration lists lists
SERVICES = ["snmpd", "snmptrapd", "ovirt-engine-notifier"]
CONFIGURATIONS = [
    "snmptrapd", "snmptrapd_users",
    "snmpd", "ovirt_notifier"
]

NOTIFIER_SERVICE = NOTIFIER_CONFIG = -1

# Disk size for virtual machine constant size
GB = 1024 ** 3

logger = logging.getLogger(__file__)

parameters = art_config["PARAMETERS"]
rest_connection = art_config["REST_CONNECTION"]

enums = art_config["elements_conf"]["RHEVM Enums"]
configuration_variables = art_config["elements_conf"]["RHEVM Utilities"]

vdc_host = rest_connection["host"]
vdc_root_user = "root"
vdc_root_password = parameters.get("vdc_root_password")
vdc_port = rest_connection["port"]

vdc_admin_user = rest_connection["user"]
vdc_password = rest_connection["password"]
vdc_admin_domain = rest_connection["user_domain"]

scheme = rest_connection.get("scheme")
schema = rest_connection.get("schema")

engine_entry_point = rest_connection["entry_point"]
engine_url = "{0}://{1}:{2}/{3}".format(
    scheme,
    vdc_host,
    vdc_port,
    engine_entry_point
)

engine_host = Host(vdc_host)
engine_host.users.append(
    RootUser(vdc_root_password)
)
engine = Engine(
    engine_host,
    ADUser(
        vdc_admin_user,
        vdc_password,
        Domain(vdc_admin_domain),
    ),
    schema=schema,
    port=vdc_port,
    entry_point=engine_entry_point
)

mgmt_bridge = parameters.get("mgmt_bridge")

storage_type = parameters.get("storage_type", None)
storage_type_local = enums["storage_type_local"]

local = parameters.get("local", None) if not storage_type else (
    storage_type == storage_type_local
)


dcs = GE['data_center_name']
# for dc in :
#     dcs.append(dc)

# dc = None
# for _dc in dcs:
#     if _dc["local"] == local:
#         dc = _dc

compatibility_version = GE.get("version")
dcs_names = [dcs]
clusters = GE["clusters"]
clusters_names = [cluster["name"] for cluster in clusters]

hosts = []
hosts_ips = []
hosts_user = "root"
hosts_password = parameters["vds_password"][0]

hosts_objects = ll_hosts.HOST_API.get(abs_link=False)
if not hosts_objects:
    raise EnvironmentError("No hosts in environment!")

host_order = parameters.get("host_order")
if host_order in ("rhevh_first", "rhel_first"):
    rhevh_first = host_order == "rhevm_first"
    hosts_objects.sort(key=lambda host: host.get_type(), reverse=rhevh_first)

    for host_object in hosts_objects:
        host_name = host_object.name
        new_name = "temp_{0}".format(host_name)
        if ll_hosts.update_host(True, host_name, name=new_name):
            host_object.name = new_name

    for i in range(len(dcs)):
        dc = dcs[i]
        for cluster in dc["clusters"]:
            for host in cluster["hosts"]:
                new_name = host["name"]
                host_name = hosts_objects[i].name
                if ll_hosts.update_host(True, host_name, name=new_name):
                    hosts_objects[i].name = new_name
                    cluster_name = cluster["name"]

                    if cluster_name != ll_hosts.get_host_cluster(new_name):
                        hl_hosts.move_host_to_another_cluster(
                            new_name, cluster_name
                        )

for host in hosts_objects:
    hosts.append(host.name)
    hosts_ips.append(host.address)

external_templates = []
templates = []
external_templates = []
templates = []

for _template in GE["external_templates"]:
    external_templates.append(_template)

templates_names = [template["name"] for template in external_templates]

# VM States
vm_state_up = enums["vm_state_up"]
vm_state_down = enums["vm_state_down"]

display_type_vnc = enums["display_type_vnc"]

# List of virtual machines names for SNMP test module
snmp_vms_names = ["snmp_vm_{0}".format(i) for i in range(2)]
