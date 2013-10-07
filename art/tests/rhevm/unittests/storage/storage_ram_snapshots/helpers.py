from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.tests_lib.low_level import vms
import config
import logging

logger = logging.getLogger(__name__)

__test__ = False


def start_cat_process_on_vm(vm_name, src):
    """
    Description: Helper function that starts a background cat process from the
    specified file to /dev/null
    Parameters:
        * vm_name - name of vm to run process on
        * src - source for cat process to read from
    Returns: True if process starts succesfully and the process PID
    """
    vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
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
    """
    logger.info('Checking if process with pid %s is running on vm %s', pid,
                vm_name)
    if not vms.is_pid_running_on_vm(vm_name=vm_name, pid=pid,
                                    user=config.VM_USER,
                                    password=config.VM_PASSWORD):
        logger.info('Process with pid %s is not running on vm %s', pid, vm_name)
        return False

    vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
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
