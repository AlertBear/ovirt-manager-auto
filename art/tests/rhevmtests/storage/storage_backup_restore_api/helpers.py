"""
Storage backup restore API
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Backup_API
"""
import config
import logging
import shlex
from art.rhevm_api.utils.test_utils import get_api
from utilities.machine import Machine

DISKS_API = get_api('disk', 'disks')
COPY_DISK_TIMEOUT = 2000


LOGGER = logging.getLogger(__name__)

VM_IP_ADDRESSES = dict()
BASE_SNAP_DESC = "base_snap"  # Base snapshot description
RESTORED_VM = "restored_vm"
TRANSIENT_DIR_PATH = "/var/lib/vdsm/transient"
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'


def is_transient_directory_empty(host):
    """
    Checking the transient folder
        * host - host ip or fqdn
    return:
        True if the directory is empty, False otherwise
    """
    LOGGER.info("Checking transient directory")
    vdsm_machine = Machine(
        host=host, user=config.HOSTS_USER,
        password=config.HOSTS_PW).util('linux')

    return vdsm_machine.is_dir_empty(dir_path=TRANSIENT_DIR_PATH)


def copy_backup_disk(vm_ip, source_disk, destination_disk,
                     timeout=COPY_DISK_TIMEOUT):
    """
    Copy disks using dd command in specified machine
    Parameters:
        * vm_ip - ip of vm that the operation should executes on
        * source_disk - name of source device (e.g. vdb)
        * destination_disk - name of destination device (e.g. vdc)
        * timeout - timeout for operation
    Return:
        True if operation succeeded, False otherwise
    """
    vm_machine = Machine(
        host=vm_ip,
        user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW).util('linux')

    command = DD_COMMAND % (source_disk, destination_disk)

    LOGGER.info("copying data from %s to %s on vm %s", source_disk,
                destination_disk, vm_ip)

    ecode, out = vm_machine.runCmd(shlex.split(command),
                                   timeout=timeout)

    LOGGER.debug("dd output: %s", out.strip())
    return ecode
