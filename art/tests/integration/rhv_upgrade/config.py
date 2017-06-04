"""
This is the a base config for upgrade. It imports all config from rhevmtests
which is only a symlink in this folder to do not duplicate of the code.
You shouldn't directly import rhvmtest_config, just use this config instead.

If you want to add more specific configs for upgrade, here is the place you can
use.
"""

from art.test_handler.settings import ART_CONFIG

# RHEVM related constants and variables
enums = ART_CONFIG['elements_conf']['RHEVM Enums']
parameters = ART_CONFIG['PARAMETERS']
root_password = parameters.get('vdc_root_password')

product_map = {
    'rhvm': 'rhv',
    'rhevm': 'rhv',
    'rhv': 'rhv',
    'ovirt': 'ovirt',
}

product = product_map.get(ART_CONFIG['DEFAULT'].get("PRODUCT"), 'rhv')
current_version = ART_CONFIG['DEFAULT'].get("VERSION")
upgrade_version = parameters.get('upgrade_version', current_version)

# Entity related stuff
hosts = set()
hosts_rhel = set()
hosts_rhel_names = set()
hosts_rhvh_names = set()
hosts_rhvh = set()

HOST_RHVH_TYPE = 'ovirt_node'
HOST_RHEL_TYPE = 'rhel'

HOST_AVAILABLE_UPDATES_STARTED = 'Started to check for available updates'
HOST_AVAILABLE_UPDATES_FINISHED = 'Check for available updates on host'
HOST_AVAILABLE_UPDATES_FAILED = 'Failed to check for available updates'
