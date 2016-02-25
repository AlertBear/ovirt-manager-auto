"""
CPU QoS test
"""

from rhevmtests.sla.config import *  # flake8: noqa

DEFAULT_CPU_PROFILE_ID_CLUSTER_0 = None
DEFAULT_CPU_PROFILE_ID_CLUSTER_1 = None
QOS_VMS = ["_".join(["QOS_vm", str(num)]) for num in xrange(1, 4)]
QOS_template = "QOS_template"
QOS_VM_FROM_TEMPLATE = "QOS_VM_TEMPLATE"
QOSS={"qos_10": 10, "qos_25": 25, "qos_50": 50, "qos_75": 75}
VMS_CPU_PROFILES = dict(zip(QOS_VMS, sorted(QOSS.values())))
