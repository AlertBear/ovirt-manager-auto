"""
Config module for hooks test
"""
import art.rhevm_api.resources as resources
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.test_handler.settings import ART_CONFIG as art_config, opts as options


parameters = art_config["PARAMETERS"]
rest_connection = art_config["REST_CONNECTION"]

enums = options["elements_conf"]["RHEVM Enums"]
configuration_variables = options["elements_conf"]["RHEVM Utilities"]

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

engine_host = resources.Host(vdc_host)
engine_host.users.append(
    resources.RootUser(vdc_root_password)
)
engine = resources.Engine(
    engine_host,
    resources.ADUser(
        vdc_admin_user,
        vdc_password,
        resources.Domain(vdc_admin_domain),
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

golden_env = art_config["prepared_env"]
dcs = golden_env["dcs"]
dc = None
for _dc in dcs:
    if int(_dc["local"]) == local:
        dc = _dc

compatibility_version = dc["compatibility_version"]
dcs_names = [dc["name"]]
clusters = dc["clusters"]
clusters_names = [cluster["name"] for cluster in clusters]

hosts = []
hosts_ips = []
hosts_user = "root"
hosts_password = parameters.as_list("vds_password")[0]

hosts_objects = ll_hosts.HOST_API.get(absLink=False)
if not hosts_objects:
    raise EnvironmentError("No hosts in environment!")

host_order = parameters.get("host_order")
if host_order in ("rhevh_first", "rhel_first"):
    rhevh_first = host_order == "rhevh_first"
    hosts_objects.sort(key=lambda host: host.get_type(), reverse=rhevh_first)

    for host_object in hosts_objects:
        host_name = host_object.name
        new_name = "temp_{0}".format(host_name)
        if ll_hosts.updateHost(True, host_name, name=new_name):
            host_object.name = new_name

    for i in range(len(dcs)):
        dc = dcs[i]
        for cluster in dc["clusters"]:
            for host in cluster["hosts"]:
                new_name = host["name"]
                host_name = hosts_objects[i].name
                if ll_hosts.updateHost(True, host_name, name=new_name):
                    hosts_objects[i].name = new_name
                    cluster_name = cluster["name"]

                    if cluster_name != ll_hosts.getHostCluster(new_name):
                        hl_hosts.move_host_to_another_cluster(
                            new_name, cluster_name
                        )

for host in hosts_objects:
    hosts.append(host.name)
    hosts_ips.append(host.address)

external_templates = []
templates = []
for cluster in clusters:
    for template in cluster["templates"]:
        templates.append(template)
    for ets in cluster["external_templates"]:
        for source_type in ("glance", "export_domain"):
            if ets[source_type]:
                for external_template in ets[source_type]:
                    external_templates.append(external_template)

templates_names = [
    template["name"] for template in templates
] + [
    template["name"] for template in external_templates
]

display_type_vnc = enums["display_type_vnc"]
vm_state_up = enums["vm_state_up"]

HOOKS_VM_NAME = 'test_vm_hooks'
CUSTOM_PROPERTY_HOOKS = "'UserDefinedVMProperties=auto_custom_hook=^[0-9]+$'"
CUSTOM_PROPERTY_VNIC_HOOKS = (
    "'CustomDeviceProperties={type=interface;"
    "prop={speed=^([0-9]{1,5})$;"
    "port_mirroring=^(True|False)$;"
    "bandwidth=^([0-9]{1,5})$}}'"
)

custom_property_default = None
custom_property_vnic_default = None
