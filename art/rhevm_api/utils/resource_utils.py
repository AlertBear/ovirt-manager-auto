
import os
import shlex
import logging
from traceback import format_exc
from utilities.machine import Machine
import art.test_handler.settings as settings
from art.core_api import is_action
from art.rhevm_api.utils.test_utils import cleanupData
from art.rhevm_api.utils.name2ip import name2ip, LookUpVMIpByName

logger = logging.getLogger('test_utils')


@is_action('runMachineCommand', id_name='runMachineCommand')
@name2ip("ip", "vmName")
def runMachineCommand(positive, ip=None, user=None, password=None,
                      type='linux', cmd='', **kwargs):
    '''
    wrapper for runCmd
    '''
    if 'cmd_list' not in kwargs:
        cmd = shlex.split(cmd)
    try:
        if not ip:
            machine = Machine().util()
        else:
            machine = Machine(ip, user, password).util(type)
        ecode, out = machine.runCmd(cmd, **kwargs)
        logger.debug('%s: runcmd : %s, result: %s,'' out: %s',
                     machine.host, cmd, ecode, out)
        return positive == ecode, {'out': out}
    except Exception as ex:
        logger.error("Failed to run command : %s : %s", cmd, ex)
    return False, {'out': None}


@is_action('copyDataToVm', id_name='copyDataToVm')
@LookUpVMIpByName("ip", "vmName")
def copyDataToVm(ip, user, password, osType, src, dest):
    '''
    Copy dirs/files to VM
    Parameters:
        ip - VM IP address
        user - VM user
        password - VM password
        osType - VM os type
        src - local source directory/file
        dest - remote destination directory/file
    Return:
        True/False
    '''
    try:
        machine = Machine(ip, user, password).util(osType)
        return machine.copyTo(src, dest, 300)
    except Exception as err:
        logger.error("copy data to %s: %s" % (ip, err))
    return False


@is_action('verifyDataOnVm', id_name='verifyDataOnVm')
@LookUpVMIpByName("ip", "vmName")
def verifyDataOnVm(positive, ip, user, password, osType, dest, destToCompare):
    '''
    Description: Verify dirs/files on VM
    Parameters:
        ip - VM IP address
        user - VM user
        password - VM password
        osType - VM os type
        src - remote source directory/file
        dest - local destination directory/file
        destToCompare - local destination directory/file to compare with
    Return:
        True/False
    '''
    try:
        machine = Machine(ip, user, password).util(osType)
        srcLocal = "{0}/{1}".format(dest, os.path.basename(destToCompare))
        if not machine.copyFrom(srcLocal, dest, 300, exc_info=positive):
            logger.error("copy data from %s" % ip)
            return False == positive
        logger.info("compare: %s to %s" % (srcLocal, destToCompare))
        res = machine.compareDirs(srcLocal, destToCompare)
        cleanupData(srcLocal)
        return res == positive
    except Exception as err:
        logger.error("verify data on %s: %s" % (ip, err))
    return False == positive


@is_action('runBenchmarkOnVm', id_name='runBenchmarkOnVm')
@LookUpVMIpByName("ip", "vmName")
def runBenchmarkOnVm(positive, ip, user, password, netPath, benchmark, type, timeoutMin):
    '''
    Execute Phoronix benchmark on VM
    Parameters:
        * ip - VM ip
        * user - VM user for remote access
        * password - VM password for remote access
        * netPath - network path of the benchmark
        * benchmark - benchmark script path
        * type - benchmark type
        * timeoutMin - waiting for benchmark termination timeout
    Return value:
        * status
    '''
    try:
        vm = Machine(ip, user, password).util('linux')
        cmd = ['python', netPath + benchmark, netPath + settings.opts['results'], type]
        rc, pid = vm.runCmd(cmd, bg=True)
        if not rc:
            logger.error("execute benchmark on VM %s" % ip)
            return False
        logger.info("wait for benchmark (pid=%s) termination on VM %s" % (pid, ip))
        return vm.waitForProcessTermination(pid=pid, attempts=int(timeoutMin), sleepTime=60)
    except:
        logger.error("run benchmark on VM: %s" % format_exc())
        return False


