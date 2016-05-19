import os
import shlex
import logging
from utilities.machine import Machine
from art.rhevm_api.utils.test_utils import cleanupData
from art.rhevm_api.utils.name2ip import name2ip, LookUpVMIpByName

logger = logging.getLogger('test_utils')


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
        res = machine.copyTo(src, dest, 300)
        machine.runCmd(['sync'])  # sync FS
        return res
    except Exception as err:
        logger.error("copy data to %s: %s", ip, err)
    return False


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
            logger.error("copy data from %s", ip)
            return False == positive
        logger.info("compare: %s to %s", srcLocal, destToCompare)
        res = machine.compareDirs(srcLocal, destToCompare)
        cleanupData(srcLocal)
        return res == positive
    except Exception as ex:
        logger.error("can not verify data on %s: %s", ip, ex)
    return False == positive
