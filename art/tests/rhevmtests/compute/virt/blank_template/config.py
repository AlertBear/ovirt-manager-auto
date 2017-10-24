from rhevmtests.compute.virt.config import *  # noqa: F403, 401
from rhevmtests.networking import config as net_conf

NEW_NAME = "renamed_blank_template"
BLANK_TEMPLATE_VM = "blank_template_verification"
BT_VM_NIC = net_conf.VM_NICS[-1]

BLANK_TEMPLATE_VM_DEFAULTS = {
    "name": BLANK_TEMPLATE_VM,
    "cluster": CLUSTER_NAME[0],  # noqa: F405
    "template": BLANK_TEMPLATE,  # noqa: F405
    "os_type": VM_OS_TYPE,  # noqa: F405
    "type": VM_TYPE,  # noqa: F405
    "nic": BT_VM_NIC,
    "network": MGMT_BRIDGE  # noqa: F405
}
