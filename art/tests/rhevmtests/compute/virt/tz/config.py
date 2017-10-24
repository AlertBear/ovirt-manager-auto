from rhevmtests.compute.virt.config import *  # flake8: noqa
from art.test_handler.tools import polarion, bz
from rhevmtests.helpers import get_gb

TZ_VM_NAME = "tz_vm_test_automation"
VM_MEMORY = get_gb(2)


VM_PARAMETERS = {
    'name': TZ_VM_NAME,
    'cluster': CLUSTER_NAME[0],
    'type': VM_TYPE,
    'display_type': VM_DISPLAY_TYPE,
    'memory': VM_MEMORY,
    'template': TEMPLATE_NAME[0],
    'ballooning': False,
}
REG_VMS_LIST = [TZ_VM_NAME]

GEN_TZ = {
    'wrong': 'Europe/Prague',
    'for_update': 'Europe/Kiev',
    'default': 'Etc/GMT',
    'name': 'DefaultGeneralTimeZone',
}

WIN_TZ = {
    'name': 'DefaultWindowsTimeZone',
    'for_update': 'Israel Standard Time',
    'default': 'GMT Standard Time',
    'wrong': 'Europe/Prague',
}
VM_TZ = [
    polarion("RHEVM-12711")(
        {'os_type': OS_RHEL_7, 'time_zone': GEN_TZ['default']}
    ),
    polarion("RHEVM-12709")(
        {'os_type': OS_WIN_7, 'time_zone': WIN_TZ['default']}
    )
]
UPDATE_VM_TZ = [
    polarion("RHEVM-21610")(
        [
            {'os_type': OS_RHEL_7, 'time_zone': GEN_TZ['default']},
            GEN_TZ['for_update'],
        ]
    ),
    polarion("RHEVM-21609")([
        {'os_type': OS_WIN_7, 'time_zone': WIN_TZ['default']},
        WIN_TZ['for_update']
    ])
]
UPDATE_RUNNING_VM = [
    polarion("RHEVM-21607")([
        {'os_type': OS_RHEL_7, 'time_zone': GEN_TZ['default']},
        GEN_TZ['for_update'],
    ]),
    bz({"1451285": {}})(polarion("RHEVM-21608"))([
        {'os_type': OS_WIN_7, 'time_zone': WIN_TZ['default']},
        WIN_TZ['for_update']
    ])
]
DEFAULT_TZ_DB = [
    polarion("RHEVM-12703")([WIN_TZ['name'], WIN_TZ['default']]),
    polarion("RHEVM-12701")([GEN_TZ['name'], GEN_TZ['default']])
]
CLI_CHANGE_DB = [
    polarion("RHEVM-21596")([
        GEN_TZ['name'],
        GEN_TZ['for_update'],
        GEN_TZ['for_update']
    ]),
    polarion("RHEVM-21595")([
        WIN_TZ['name'],
        WIN_TZ['for_update'],
        WIN_TZ['for_update']
    ]),
    polarion("RHEVM-12707")([
        GEN_TZ['name'],
        GEN_TZ['wrong'],
        GEN_TZ['default']
    ]),
    polarion("RHEVM-21636")([
        WIN_TZ['name'],
        WIN_TZ['wrong'],
        WIN_TZ['default']
    ])
]