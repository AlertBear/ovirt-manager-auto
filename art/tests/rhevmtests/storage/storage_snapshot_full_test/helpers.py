"""Helper functions for snapshot full plan"""
from art.rhevm_api.utils.resource_utils import copyDataToVm, verifyDataOnVm
from art.rhevm_api.utils.test_utils import removeDirOnHost
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.tests_lib.low_level import vms
import config
from rhevmtests.storage import helpers
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
        user=config.VM_USER,
        password=config.VM_PASSWORD,
        osType='linux',
        dest=DEST_DIR,
        destToCompare=path
    )


def copy_data_to_vm(vm_name, path):
    """
    Copies data from path to DEST_DIR
    Parameters:
        * vm_name - name of vm to run process on
        * path - path to copy the files from
    """
    assert copyDataToVm(
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.VM_USER,
        password=config.VM_PASSWORD,
        osType='linux',
        src=path,
        dest=DEST_DIR
    )


def remove_dir_on_host(vm_name, dirname):
    """
    Removes directory given by path from vm vm_name

    Parameters:
        * vm_name - name of the vm
        * dirname - path to the directory that will be remove
    """
    assert removeDirOnHost(
        True,
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.VM_USER,
        password=config.VM_PASSWORD,
        osType='linux',
        dirname=dirname
    )


"""
Helpers functions for RAM Snapshot tests - 10134
"""


def start_cat_process_on_vm(vm_name, src):
    """
    Description: Helper function that starts a background cat process from the
    specified file to /dev/null
    Parameters:
        * vm_name - name of vm to run process on
        * src - source for cat process to read from
    Returns: True if process starts succesfully and the process PID
    """
    vm_ip = helpers.get_vm_ip(vm_name)
    logger.info('Starting cat on vm %s from %s to /dev/null', vm_name, src)
    cmd = 'cat %s > /dev/null &' % src
    status, _ = runMachineCommand(True, ip=vm_ip, user=config.VM_USER,
                                  password=config.VM_PASSWORD, cmd=cmd)

    if not status:
        logger.error('Error when running command %s on vm %s', cmd, vm_name)
        return False, None

    cmd = 'pgrep cat'

    status, out = runMachineCommand(True, ip=vm_ip, user=config.VM_USER,
                                    password=config.VM_PASSWORD, cmd=cmd)

    if not status:
        logger.error('Unable to find pid for cat process on vm %s', vm_name)
        return False, None

    output = out['out']
    logger.debug('output is %s', output.splitlines())
    pid = output.splitlines()[-1]
    logger.info('Last cat pid found: %s' % pid)

    return True, pid


def is_pid_running_on_vm(vm_name, pid, cmd):
    """
    Helper function to ensure a process with the given pid is running on the
    vm. The process' actual cmdline is then checked to ensure that it is the
    expected process and not another process with the pid of the expected one
    to prevent false positives.
    Parameters:
        * vm_name - name of vm to check process on
        * pid - the pid to look for
        * cmd - expected cmdline of the process
    Returns: True if process is running on vm_name

    """
    logger.info('Checking if process with pid %s is running on vm %s', pid,
                vm_name)
    if not vms.is_pid_running_on_vm(vm_name=vm_name, pid=pid,
                                    user=config.VM_USER,
                                    password=config.VM_PASSWORD):
        logger.info('Process with pid %s is not running on vm %s',
                    pid, vm_name)
        return False

    vm_ip = helpers.get_vm_ip(vm_name)
    logger.info('Checking cmdline of process %s on vm %s', pid, vm_name)
    command = 'cat /proc/%s/cmdline' % pid
    rc, out = runMachineCommand(True, ip=vm_ip, user=config.VM_USER,
                                password=config.VM_PASSWORD, cmd=command)

    if not rc:
        logger.info('Unable to check cmdline of process %s on vm %s', pid,
                    vm_name)
        return False

    cmdline = out['out'].replace('\x00', ' ').strip()
    logger.info('cmdline for pid %s on vm %s is: %s', pid, vm_name, cmdline)
    return cmdline.endswith(cmd)
