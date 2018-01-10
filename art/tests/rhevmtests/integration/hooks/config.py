"""
Config module for hooks test
"""
from rhevmtests.config import *  # flake8: noqa

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

display_type_vnc = ENUMS["display_type_vnc"]
