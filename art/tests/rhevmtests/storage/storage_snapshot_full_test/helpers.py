"""Helper functions for snapshot full plan"""
import shlex
from art.rhevm_api.utils.resource_utils import copyDataToVm, verifyDataOnVm
from art.rhevm_api.utils.test_utils import removeDirOnHost
from art.rhevm_api.tests_lib.low_level import vms
from rhevmtests.storage import helpers, config
import logging

logger = logging.getLogger(__name__)

__test__ = False

"""
Helpers functions for Storage live snapshot sanity tests - 5588
"""

VM_IP_ADDRESSES = dict()
DEST_DIR = '/var/tmp'
BASE_SNAP = "base_snap"  # Base snapshot description


def verify_data_on_vm(positive, vm_name, path):
    """
    Verifies /var/tmp directory agains given path
    """
    assert verifyDataOnVm(
        positive,
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW,
        osType='linux',
        dest=DEST_DIR,
        destToCompare=path
    )


def copy_data_to_vm(vm_name, path):
    """
    Copies data from path to DEST_DIR
    Parameters:
        * vm_name - name of VM to run process on
        * path - path to copy the files from
    """
    assert copyDataToVm(
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW,
        osType='linux',
        src=path,
        dest=DEST_DIR
    )


def remove_dir_on_host(vm_name, dirname):
    """
    Removes directory given by path from VM vm_name

    Parameters:
        * vm_name - name of the VM
        * dirname - path to the directory that will be remove
    """
    assert removeDirOnHost(
        True,
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW,
        osType='linux',
        dirname=dirname
    )


"""
Helpers functions for RAM Snapshot tests - 10134
"""


def start_cat_process_on_vm(vm_name, src):
    """
    Helper function that starts a background cat process from the
    specified file to /dev/null

    Args:
        vm_name(str): Name of VM to run process on
        src(src): Source for cat process to read from
    Returns:
        str: PID of the process
    Raises:
        Exception: If any of the commands fails to execute
    """
    logger.info("Starting cat on VM %s from %s to /dev/null", vm_name, src)
    vm_executor = helpers.get_vm_executor(vm_name)
    cmd = 'cat %s > /dev/null &' % src
    rc, _, error = vm_executor.run_cmd(cmd=shlex.split(cmd))

    if rc:
        logger.error(
            "Error when running command %s on VM %s: %s", cmd, vm_name, error
        )
        raise Exception("Error executing command %s, %s" % (cmd, error))

    cmd = 'pgrep cat'
    rc, output, error = vm_executor.run_cmd(cmd=shlex.split(cmd))

    if rc:
        logger.error(
            "Unable to find pid for cat process on VM %s: %s", vm_name, error
        )
        raise Exception("Error executing command %s, %s" % (cmd, error))

    logger.debug('output is %s', output.splitlines())
    pid = output.splitlines()[-1]
    logger.info("Last cat pid found: %s" % pid)

    return pid


def is_pid_running_on_vm(vm_name, pid, cmd):
    """
    Helper function to ensure a process with the given pid is running on the
    VM. The process' actual cmdline is then checked to ensure that it is the
    expected process and not another process with the pid of the expected one
    to prevent false positives.

    Args:
        vm_name (str): Name of VM to check process on
        pid (str): The pid to look for
        cmd (str): Expected cmdline of the process

    Returns:
        bool: True if process is running on vm_name
    """
    logger.info(
        "Checking if process with pid %s is running on VM %s", pid, vm_name
    )
    if not vms.is_pid_running_on_vm(
        vm_name=vm_name, pid=pid, user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW
    ):
        logger.error(
            "Process with pid %s is not running on VM %s", pid, vm_name
        )
        return False

    vm_executor = helpers.get_vm_executor(vm_name)
    logger.info("Checking cmdline of process %s on VM %s", pid, vm_name)
    command = 'cat /proc/%s/cmdline' % pid
    rc, output, error = vm_executor.run_cmd(cmd=shlex.split(command))

    if rc:
        logger.error(
            "Unable to check cmdline of process %s on VM %s: %s", pid,
            vm_name, error
        )
        return False

    cmdline = output.replace('\x00', ' ').strip()
    logger.info("cmdline for pid %s on VM %s is: %s", pid, vm_name, cmdline)
    return cmdline.endswith(cmd)
