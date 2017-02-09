"""
This is the a base config for upgrade. It imports all config from rhevmtests
which is only a symlink in this folder to do not duplicate of the code.
You shouldn't directly import rhvmtest_config, just use this config instead.

If you want to add more specific configs for upgrade, here is the place you can
use.
"""

from art.test_handler.settings import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']

product_map = {
    'rhvm': 'rhv',
    'rhevm': 'rhv',
    'rhv': 'rhv',
    'ovirt': 'ovirt',
}

product = product_map.get(ART_CONFIG['DEFAULT'].get("PRODUCT"), 'rhv')
current_version = ART_CONFIG['DEFAULT'].get("VERSION")
upgrade_version = PARAMETERS.get('upgrade_version', current_version)
