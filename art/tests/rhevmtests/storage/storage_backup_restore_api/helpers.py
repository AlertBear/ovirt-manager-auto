"""
Storage backup restore API
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Backup_API
"""
import logging
import shlex

from art.rhevm_api.utils.test_utils import get_api
import rhevmtests.storage.helpers as storage_helpers

DISKS_API = get_api('disk', 'disks')
COPY_DISK_TIMEOUT = 2000

logger = logging.getLogger(__name__)

TRANSIENT_DIR_PATH = "/var/lib/vdsm/transient"
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=4096 conv=noerror,sync'


def is_transient_directory_empty(host):
    """
    Checking the transient folder
        * host - host ip or fqdn
    return:
        True if the directory is empty, False otherwise
    """
    logger.info("Checking transient directory")
    return storage_helpers.is_dir_empty(
        host_name=host, dir_path=TRANSIENT_DIR_PATH
    )


def copy_backup_disk(
    vm_name, source_disk, destination_disk, timeout=COPY_DISK_TIMEOUT
):
    """
    Copy disks using dd command in specified machine

    Args:
        vm_name (str): The name of the vm that the operation should be
            executed on
        source_disk (str): The name of source device (e.g. vdb)
        destination_disk (str): The name of destination device (e.g. vdc)
        timeout (int): The timeout for operation in seconds
    Return:
        True if operation succeeded, False otherwise
    """
    vm_executor = storage_helpers.get_vm_executor(vm_name)
    command = DD_COMMAND % (source_disk, destination_disk)
    logger.info(
        "copying data from %s to %s on vm %s",
        source_disk, destination_disk, vm_name
    )
    rc, out, err = vm_executor.run_cmd(
        shlex.split(command), io_timeout=timeout
    )
    logger.debug("The dd output is: '%s'", out.strip())
    return not rc
