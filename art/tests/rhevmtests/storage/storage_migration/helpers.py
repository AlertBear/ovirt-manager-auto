"""
Live Storage Migration test helpers functions
"""
import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    jobs as ll_jobs,
)
from art.core_api.apis_exceptions import APITimeout
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


def wait_for_disks_and_snapshots(vms_to_wait_for, live_operation=True):
    """
    Wait for given VMs snapshots and disks status to be 'OK'
    """
    for vm_name in vms_to_wait_for:
        if ll_vms.does_vm_exist(vm_name):
            try:
                disks = [d.get_id() for d in ll_vms.getVmDisks(vm_name)]
                ll_disks.wait_for_disks_status(disks, key='id')
                ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
            except APITimeout:
                assert False, (
                    "Snapshots failed to reach OK state on VM '%s'" % vm_name
                )
    if live_operation:
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
    else:
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])