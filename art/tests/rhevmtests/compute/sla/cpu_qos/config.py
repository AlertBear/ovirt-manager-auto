"""
CPU QoS test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

DEFAULT_CPU_PROFILE_ID_CLUSTER_0 = None
DEFAULT_CPU_PROFILE_ID_CLUSTER_1 = None
DEFAULT_LOAD_VALUE = 50
LOAD_VALUES = [10, 25, 40]
QOS_TEMPLATE = "qos_template"
QOS_VM_FROM_TEMPLATE = "qos_vm_template"
QOSS = dict(("qos_%s" % i, i) for i in LOAD_VALUES)
CPU_PROFILES = dict(
    ("cpu_profile_%s" % i, "qos_%s" % i) for i in LOAD_VALUES
)
QOS_VMS = VM_NAME[:len(CPU_PROFILES)]
VMS_CPU_PROFILES = dict(zip(QOS_VMS, sorted(CPU_PROFILES)))

CPU_QOS_10 = "qos_10"
CPU_PROFILE_10 = "cpu_profile_10"
