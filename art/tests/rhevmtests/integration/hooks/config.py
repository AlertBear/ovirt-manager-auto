"""
Config module for hooks test
"""
import art.rhevm_api.resources as resources
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.test_handler.settings import ART_CONFIG as art_config
from art.test_handler.settings import GE


HOOKS_VM_NAME = 'test_vm_hooks'

VM_PROPERTY_KEY = "UserDefinedVMProperties"
VNIC_PROPERTY_KEY = "CustomDeviceProperties"

CUSTOM_PROPERTY_HOOKS = "auto_custom_hook=^[0-9]+$"
CUSTOM_PROPERTY_VNIC_HOOKS = (
    "\"{type=interface;"
    "prop={speed=^([0-9]{1,5})$;"
    "port_mirroring=^(True|False)$;"
    "bandwidth=^([0-9]{1,5})$}}\""
)

custom_property_default = None
custom_property_vnic_default = None

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

engine_host = resources.Host(vdc_host)
engine_host.users.append(resources.RootUser(vdc_root_password))

engine = resources.Engine(
    engine_host,
    resources.ADUser(
        vdc_admin_user,
        vdc_password,
        resources.Domain(vdc_admin_domain),
    )
)

mgmt_bridge = parameters.get("mgmt_bridge")

storage_type = parameters.get("storage_type", None)
storage_type_local = enums["storage_type_local"]
local = parameters.get("local", 'false') if not storage_type else (
    storage_type == storage_type_local
)

dcs = [GE['data_center_name']]

# dc = None
# for _dc in dcs:
#     if _dc["local"] == local:
#         dc = _dc

compatibility_version = GE.get("version")
dcs_names = dcs
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
    rhevh_first = host_order == "rhevh_first"
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

hooks_host = resources.Host(ip=hosts_ips[0])
hooks_host.users.append(resources.RootUser(vdc_root_password))

external_templates = []
templates = []

for _template in GE["external_templates"]:
    external_templates.append(_template)

templates_names = [template["name"] for template in external_templates]

display_type_vnc = enums["display_type_vnc"]
vm_state_up = enums["vm_state_up"]
