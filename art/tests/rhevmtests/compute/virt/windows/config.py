#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Windows config file
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa
import rhevmtests.helpers as gen_helper

REMOTE_KEY_PRODUCT_FILE = (
    '/etc/ovirt-engine/osinfo.conf.d/10-product_keys.properties'
)
LOCAL_KEY_PRODUCT_FILE = (
    'tests/rhevmtests/compute/virt/windows/conf_files/10-product_keys'
    '.properties'
)
WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
CPU_TYPE_MIN = 'Intel SandyBridge Family'
MIGRATION_POLICY_MINIMAL_DOWNTIME = '80554327-0569-496b-bdeb-fcbbf52b827b'
MIGRATION_POLICY_LEGACY = '00000000-0000-0000-0000-000000000000'
BANDWIDTH = 'auto'
# vms
WINDOWS_2012 = 'windows_2012'
WINDOWS_10 = 'windows_10'
WINDOWS_7 = 'windows_7'

# templates
WINDOWS_2012_TEMPLATE = 'Windows_2012_x64_GA_template'
WINDOWS_10_TEMPLATE = 'Windows_2010_x64_GA_template'
WINDOWS_7_TEMPLATE = 'Windows_2007_x64_GA_template'

SKIP_MESSAGE_CPU = (
    "Skip windows test: \n"
    "Cluster not support minimum CPU: 'Intel SandyBridge Family'"
)
SKIP_SEAL_TEMPLATE_DONT_EXISTS = (
    "Skip windows test: \n"
    "Sealed templates did not created, check logs"
)

WINDOWS_VM_NAMES = [
    WINDOWS_10, WINDOWS_7, WINDOWS_2012
]
VM_PARAMETERS = {
    WINDOWS_7: {
        'memory': gen_helper.get_gb(4),
        'memory_guaranteed': gen_helper.get_gb(3),
        'max_memory': gen_helper.get_gb(10),
        'os_type': ENUMS['windows7x64'],
        'type': VM_TYPE_DESKTOP,
        'time_zone': WIN_TZ

    },
    WINDOWS_10: {
        'memory': gen_helper.get_gb(4),
        'memory_guaranteed': gen_helper.get_gb(4),
        'max_memory': gen_helper.get_gb(10),
        'os_type': ENUMS['windows10x64'],
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

WINDOWS_10_SEAL_TEMPLATE = "Windows_10_seal_template"
WINDOWS_2012_SEAL_TEMPLATE = "Windows_2012_seal_template"
WINDOWS_7_SEAL_TEMPLATE = "Windows_7_seal_template"
WINDOWS_SEAL_TEMPLATES = [WINDOWS_10_SEAL_TEMPLATE, WINDOWS_2012_SEAL_TEMPLATE]
WINDOWS_SEAL_VM_TO_TEMPLATES = {
    WINDOWS_10: WINDOWS_SEAL_TEMPLATES[0],
    WINDOWS_2012: WINDOWS_SEAL_TEMPLATES[1]
}
WINDOWS_SEAL_VMS = [WINDOWS_10, WINDOWS_2012]

# sysprep initialization parameters
LOCALE_GB_FULL_DISPLAY = 'en-gb;English (United Kingdom)'
LOCALE_GB = 'en-GB'
SYSPREP_HOST_NAME = 'SYSPREP_TEST'
TZ_TOGA = 'Tonga Standard Time'
TZ_TOGA_UTC = 'UTC+13:00'
# os types
WIN_OS_TYPE_SERVER = 'server'
WIN_OS_TYPE_DESKTOP = 'desktop'
# user lists
USERS_LIST_DESKTOP = ['QE', 'Administrator', 'user']
USERS_LIST_SERVER = ['Administrator', 'QE']
USER_LIST_BY_OS_TYPE = {
    WIN_OS_TYPE_DESKTOP: USERS_LIST_DESKTOP,
    WIN_OS_TYPE_SERVER: USERS_LIST_SERVER
}
TIMEOUT_SEAL_VM = 600


# initialization parameters
INIT_PARAMS = {
    'host_name': SYSPREP_HOST_NAME,
    'timezone': TZ_TOGA,
    'input_locale': LOCALE_GB,
    'system_locale': LOCALE_GB,
    'ui_language': LOCALE_GB,
    'user_locale': LOCALE_GB,
}
INIT_PARAMS_CUSTOM_FILE = {
    'custom_script': None
}

SYSPREP_EXPECTED_VALUES_BASE = {
    'Host Name': SYSPREP_HOST_NAME,
    'Time Zone': TZ_TOGA_UTC,
    'System Locale': LOCALE_GB_FULL_DISPLAY,
}
SYSPREP_FILE_VALUES = {
    'ComputerName': SYSPREP_HOST_NAME,
    'TimeZone': TZ_TOGA,
    'InputLocale': LOCALE_GB,
    'SystemLocale': LOCALE_GB,
    'UILanguage': LOCALE_GB,
    'UserLocale': LOCALE_GB
}
IS_VM_INITIALIZED_QUREY = (
    "select is_initialized from vm_static where vm_name='"
)
