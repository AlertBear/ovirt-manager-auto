"""
Ovirt Scheduler Proxy configuration file
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

PACKAGE_OVIRT_SCHEDULER_PROXY = "ovirt-scheduler-proxy"

SERVICE_OVIRT_SCHEDULER_PROXY = "ovirt-scheduler-proxy"

ENGINE_CONFIG_OVIRT_SCHEDULER_PROXY = "ExternalSchedulerEnabled"

# External scheduler plugins, that you need to put under the folder
# /usr/share/ovirt-scheduler-proxy/plugins/ on the engine
# to make it available from the REST API as new scheduling policy units
PLUGIN_EXTERNAL_SCHEDULER_FILTER = """
#!/bin/env python
class ExternalSchedulerFilterPlugin(object):
    def do_filter(self, hosts, vm, args):
        print ["{host_uuid}"]
"""

PLUGIN_EXTERNAL_SCHEDULER_WEIGHT = """
#!/bin/env python
class ExternalSchedulerWeightPlugin(object):
    def do_score(self, hosts, vm, args):
        hosts_scores = list()
        for host in hosts:
            if host == "{host_uuid}":
                continue
            hosts_scores.append((host, 50))
        print hosts_scores
"""

PLUGIN_EXTERNAL_SCHEDULER_BALANCE = """
#!/bin/env python
class ExternalSchedulerBalancePlugin(object):
    def do_balance(self, hosts, args):
        print ("{vm_uuid}", ["{host_uuid}"])
"""

PLUGIN_EXTERNAL_SCHEDULER_CORRUPTED = """
#!/bin/env python
class ExternalSchedulerCorruptedPlugin(object):
    def
"""

PLUGIN_EXTERNAL_SCHEDULER_TIMEOUT = """
#!/bin/env python
from time import sleep
class ExternalSchedulerTimeoutPlugin(object):
    def do_filter(self, hosts, vm, args):
        sleep(125)
        print []
"""

PLUGIN_EXTERNAL_SCHEDULER_STOPPED = """
#!/bin/env python
class ExternalSchedulerStoppedPlugin(object):
    def do_filter(self, hosts, vm, args):
        print []
"""

PLUGINS_EXTERNAL_SCHEDULER = [
    PLUGIN_EXTERNAL_SCHEDULER_FILTER,
    PLUGIN_EXTERNAL_SCHEDULER_WEIGHT,
    PLUGIN_EXTERNAL_SCHEDULER_BALANCE,
    PLUGIN_EXTERNAL_SCHEDULER_CORRUPTED,
    PLUGIN_EXTERNAL_SCHEDULER_TIMEOUT,
    PLUGIN_EXTERNAL_SCHEDULER_STOPPED
]

# External scheduler plugins paths
PATH_BASE = "/usr/share/ovirt-scheduler-proxy/plugins"
PATH_EXTERNAL_SCHEDULER_PLUGINS = [
    os.path.join(
        PATH_BASE, "{0}_{1}".format(script_name, "plugin.py")
    ) for script_name in (
        "filter", "weight", "balance", "corrupted", "timeout", "stopped"
    )
]

# External scheduler policy units
POLICY_UNIT_FILTER = "ExternalSchedulerFilterPlugin"
POLICY_UNIT_WEIGHT = "ExternalSchedulerWeightPlugin"
POLICY_UNIT_BALANCE = "ExternalSchedulerBalancePlugin"
POLICY_UNIT_CORRUPTED = "ExternalSchedulerCorruptedPlugin"
POLICY_UNIT_TIMEOUT = "ExternalSchedulerTimeoutPlugin"
POLICY_UNIT_STOPPED = "ExternalSchedulerStoppedPlugin"

EXTERNAL_SCHEDULER_POLICY_UNITS = [
    POLICY_UNIT_FILTER,
    POLICY_UNIT_WEIGHT,
    POLICY_UNIT_BALANCE,
    POLICY_UNIT_CORRUPTED,
    POLICY_UNIT_TIMEOUT,
    POLICY_UNIT_STOPPED
]

# External scheduler policies
EXTERNAL_POLICY_TIMEOUT = "timeout_external_policy"
EXTERNAL_POLICY_FILTER = "filter_external_policy"
EXTERNAL_POLICY_WEIGHT = "weight_external_policy"
EXTERNAL_POLICY_BALANCE = "balance_external_policy"
EXTERNAL_POLICY_SERVICE_STOPPED = "service_stopped_external_policy"

# String constants
HOST_UUID = "host_uuid"
VM_UUID = "vm_uuid"
