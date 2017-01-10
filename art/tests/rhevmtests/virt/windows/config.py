#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Vm Pool test config
"""
import rhevmtests.helpers as gen_helper
from rhevmtests.virt.config import *  # flake8:  noqa

WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
CPU_TYPE_MIN = 'Intel SandyBridge Family'
MIGRATION_POLICY_MINIMAL_DOWNTIME = '80554327-0569-496b-bdeb-fcbbf52b827b'
MIGRATION_POLICY_LEGACY = '00000000-0000-0000-0000-000000000000'
BANDWIDTH = 'auto'
# vms
WINDOWS_2012 = 'window_2012'
WINDOWS_2008_RC2 = 'window_2008'
WINDOWS_7 = 'window_7'
SKIP_MESSAGE_CPU = (
    "Skip windows test: \n"
    "Cluster not support minimum CPU: 'Intel SandyBridge Family'"
)
# templates
WINDOWS_TEMPLATES_NAME = [
    TEMPLATE_NAME[1], TEMPLATE_NAME[2], TEMPLATE_NAME[3]
]
WINDOWS_VM_NAMES = [
    WINDOWS_2008_RC2, WINDOWS_7, WINDOWS_2012
]
VM_START_STOP_SETTINGS = {
    WINDOWS_2008_RC2: {},
    WINDOWS_7: {},
    WINDOWS_2012: {}
}
VM_PARAMETERS = {
    WINDOWS_7: {
        'memory': gen_helper.get_gb(4),
        'memory_guaranteed': gen_helper.get_gb(3),
        'max_memory': gen_helper.get_gb(10),
        'os_type': ENUMS['windows7x64'],
        'type': VM_TYPE_DESKTOP,
        'time_zone': WIN_TZ

    },
    WINDOWS_2008_RC2: {
        'memory': gen_helper.get_gb(6),
        'memory_guaranteed': gen_helper.get_gb(4),
        'max_memory': gen_helper.get_gb(10),
        'os_type': ENUMS['windows2008r2x64'],
        'type': VM_TYPE_DESKTOP,
        'time_zone': WIN_TZ
    },
    WINDOWS_2012: {
        'memory': gen_helper.get_gb(6),
        'memory_guaranteed': gen_helper.get_gb(4),
        'max_memory': gen_helper.get_gb(10),
        'os_type': ENUMS['windows2012x64'],
        'type': VM_TYPE_SERVER,
        'time_zone': WIN_TZ
    }
}
