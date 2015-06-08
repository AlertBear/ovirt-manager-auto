"""
Config module for hooks test
"""

__test__ = False

from rhevmtests.system.config import *  # flake8: noqa

VM_UP = ENUMS['vm_state_up']
HOOKS_VM_NAME = 'test_vm_hooks'
if not GOLDEN_ENV:
    TEMPLATE_NAME = [PARAMETERS.get('template', 'hooks_template')]
