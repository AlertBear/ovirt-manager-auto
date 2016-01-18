"""
Live Storage Migration test helpers functions
"""
import config
import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    wait_for_disks_status, addDisk,
)
from art.test_handler import exceptions
from rhevmtests.storage.helpers import prepare_disks_for_vm

logger = logging.getLogger(__name__)


def add_new_disk_for_test(
    vm_name, alias, provisioned_size=(1 * config.GB), sparse=False,
    disk_format=config.RAW_DISK, wipe_after_delete=False, attach=False,
    sd_name=None
):
    """
    Prepares disk for given vm
    """
    disk_params = {
        'alias': alias,
        'active': False,
        'provisioned_size': provisioned_size,
        'interface': config.VIRTIO,
        'format': disk_format,
        'sparse': sparse,
        'wipe_after_delete': wipe_after_delete,
        'storagedomain': sd_name,
    }

    if not addDisk(True, **disk_params):
        raise exceptions.DiskException(
            "Can't create disk with params: %s" % disk_params)
    logger.info("Waiting for disk %s to be ok", alias)
    wait_for_disks_status([alias])
    if attach:
        prepare_disks_for_vm(vm_name, [alias])
