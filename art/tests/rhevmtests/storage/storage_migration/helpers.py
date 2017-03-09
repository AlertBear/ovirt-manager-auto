"""
Live Storage Migration test helpers functions
"""
import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
)
from rhevmtests.storage.helpers import prepare_disks_for_vm


def add_new_disk_for_test(
    vm_name, alias, provisioned_size=(1 * config.GB), sparse=False,
    disk_format=config.RAW_DISK, wipe_after_delete=False, attach=False,
    sd_name=None
):
    """
    Prepares disk for given vm
    """
    disk_params = config.disk_args.copy()
    disk_params['alias'] = alias
    disk_params['active'] = False
    disk_params['provisioned_size'] = provisioned_size
    disk_params['format'] = disk_format
    disk_params['sparse'] = sparse
    disk_params['wipe_after_delete'] = wipe_after_delete
    disk_params['storagedomain'] = sd_name

    assert ll_disks.addDisk(True, **disk_params), (
        "Failed to add disk %s" % alias
    )
    ll_disks.wait_for_disks_status([alias])
    if attach:
        prepare_disks_for_vm(vm_name, [alias])
