from rhevmtests.compute.virt.config import *  # flake8: noqa
from rhevmtests.networking import config as net_conf


SMBIOS_VM_NIC = net_conf.VM_NICS[-1]

SMBIOS_VM = "vm_smbios_testing"

SMBIOS_VMS_LIST = list()

custom_uuid = "4c4c4544-0057-5610-8056-c4c04f4d5731"
incorrect_uuid = "111111"


SMBIOS_VM_DEFAULTS = {
    "name": SMBIOS_VM,
    "cluster": CLUSTER_NAME[0],  # noqa: F405
    "template": TEMPLATE_NAME[0],  # noqa: F405
    "os_type": VM_OS_TYPE,  # noqa: F405
    "type": VM_TYPE,  # noqa: F405
    "nic": SMBIOS_VM_NIC,
    "display_type": VM_DISPLAY_TYPE,  # noqa: F405
    "network": MGMT_BRIDGE  # noqa: F405
}

CMD = ["dmidecode", "-s", "system-uuid"]
