"""
Config module for storage vm sanity
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "full_disk_tests"

VM1_NAME = "full_disk_vm1_%s" % TESTNAME
VM2_NAME = "full_disk_vm2_%s" % TESTNAME

TEMPLATE_NAME = PARAMETERS.get('template', 'full_disk_template')
SNAPSHOT_NAME = PARAMETERS.get('snapshot_name', 'full_disk_snapshot')

# TODO: remove
ISCSI_DOMAIN = "iscsi_domain"

# TODO: remove
STORAGE_SECTION = STORAGE_CONF
if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    EXTEND_LUN = STORAGE_SECTION['PARAMETERS.extend_lun']
    # Size of device (in GB)
    EXTEND_SIZE = int(EXTEND_LUN['devices_capacity'])
    EXTEND_LUN_ADDRESS = PARAMETERS.as_list("extend_lun_address")
    EXTEND_LUN_TARGET = PARAMETERS.as_list("extend_lun_target")
    EXTEND_LUN = PARAMETERS.as_list("extend_lun")

    # Adds to EXTEND_LUNS a dictionary with all the luns data used to be
    # extended
    EXTEND_LUNS = []
    for address, target, lun in zip(
        EXTEND_LUN_ADDRESS, EXTEND_LUN_TARGET, EXTEND_LUN
    ):
        EXTEND_LUNS.append({
            "lun_targets": [target],
            "lun_addresses": [address],
            "lun_list": [lun],
        })
