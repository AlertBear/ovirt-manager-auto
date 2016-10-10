"""
Config module for hooks test
"""

from rhevmtests.system.config import *  # flake8: noqa

__test__ = False

VM_UP = ENUMS['vm_state_up']
HOOKS_VM_NAME = 'test_vm_hooks'
DISPLAY_TYPE = ENUMS['display_type_vnc']
if not GOLDEN_ENV:
    TEMPLATE_NAME = [PARAMETERS.get('template', 'hooks_template')]
