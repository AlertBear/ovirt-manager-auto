#!/usr/bin/env python


# Copyright (C) 2011 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

from framework_utils.rest_utils import RestUtil
from framework_utils.sdk_utils import SdkUtil
import framework_utils.settings as settings
from utilities.utils import readConfFile
import logging
import time
import re
import random
from contextlib import contextmanager
from traceback import format_exc
import os
import shlex
import framework_utils.settings as settings
from utilities.utils import readConfFile, calculateTemplateUuid,\
convertMacToIp, pingToVms, getIpAddressByHostName, createDirTree
from utilities.machine import Machine, eServiceAction
from utilities.cobblerApi import Cobbler
from framework_utils.apis_exceptions import APITimeout, EntityNotFound
from utilities.tools import updateGuestTools, isToolsInstalledOnGuest, \
    removeToolsFromGuest, waitForGuestReboot,installAutoUpgraderCD, \
    installToolsFromDir, verifyToolsFilesExist
#from upgradeSetup.prepSetup import Rhevm
from rhevm_api.threads import CreateThread, ThreadSafeDict
import shutil
import string
from functools import wraps

logger = logging.getLogger('test_utils')

#The location of all supported elements
elementsConf = "conf/elements.conf"
#The name of section in the element configuration file
elementConfSection = 'elements'
#The location of all supported os

api = None

def get_api(element, collection):
    '''
    Fetch proper API instance based on engine type
    '''

    engine = settings.opts.get('engine', 'rest')
    if engine == 'rest':
        api = RestUtil(element, collection)
    if engine == 'sdk':
        api = SdkUtil(element, collection)

    return api


def split(s):
    '''
    Split `s` by comma and/or by whitespace.

    Parameters: s -- A string-like object to split.
    Return: A sequence of strings-like objects.
    '''
    return s.replace(',', ' ').split()


def sleep(seconds):
    """
        Suspend execution for the given number of seconds.
        Author: egerman
        Parameters:
         * seconds - time to sleep in seconds
        Return: True
    """
    time.sleep(seconds)
    return True


def getStat(name, elm_name, collection_name, stat_types):
    '''
    Description: gets the given statistic from a host
    Parameters:
      * name - name of a host or vm
      * obj_type - "hosts" or "vms"
      * stat_type - a list of any stat that REST API gives back,
        for example 'memory.used', 'swap.total', etc.
    Return: a dictionary with the requested and found stats
    '''
    util = get_api(elm_name, collection_name)
    elm_obj = util.find(name)
    statistics = util.getElemFromLink(elm_obj, link_name='statistics', attr='statistic')
    values = {}
    for stat in statistics:
        if stat.get_name() in stat_types:
            datum =  stat.get_values().get_value()[0].get_datum()
            if stat.get_values().get_type() == "INTEGER":
                values[stat.get_name()] = int(float(datum))
                #return int(stat.values.value.datum)
            elif stat.get_values().get_type() == "DECIMAL":
                values[stat.get_name()] = float(datum)
    return values


def lookingForIpAdressByEntityName(entity, ipVar="ip", nameVar="vmName", expTime=60*10, cache=ThreadSafeDict()):
    """
    Description: Decorator replaces non-defined ipVar parameter.
                 Result is cached until expTime, for continuous calling
    Parameters:
     * entity - name of entity (vms, hosts)
     * ipVar - name of variable represents IP for specific entity
     * nameVar - name of variable used to define entity name
     * expTime - expiration time (seconds)
    """
    def wrapper(f):
        if entity not in ('vms', 'hosts'):
            raise AttributeError("entity='%s' is not supported now" % entity)

        try:
            sub = re.compile('^((.*)%s\s*([=-]).*)$' % ipVar, re.M)
            f.func_doc = sub.sub(r'\1\n\2%s \3 name of entity (can supply %s)' % \
                    (nameVar, ipVar), f.func_doc, 1)
        except Exception as ex:
            logger.warn("failed to add '%s' into doc-string of '%s': %s", nameVar, f.func_name, ex)

        @wraps(f)
        def wrappered_call(*args, **kwargs):
            if kwargs.get(ipVar, None) is None and nameVar in kwargs:
                if kwargs[nameVar] is None:
                    raise AttributeError("missing target machine: %s or %s" % (ipVar, nameVar))

                cEntry = "%s-%s" % (entity, kwargs[nameVar])
                with cache:
                    cRecord = cache.get(cEntry, {'ip': None, 'exp': 0})
                    if cRecord['exp'] < time.time():

                        cRecord['ip'] = getIpByEntityName(entity, kwargs[nameVar], varName='ip')[1]['ip']

                        if cRecord['ip'] is None:
                            raise AttributeError("failed to retrieve IP by %s='%s'" % (nameVar, kwargs[nameVar]))

                        cRecord['exp'] = time.time() + expTime
                        cache[cEntry] = cRecord

                    kwargs[ipVar] = cRecord['ip']
                del kwargs[nameVar]

            return f(*args, **kwargs)
        return wrappered_call
    return wrapper


def validateElementStatus(positive, element, collection, elementName,
                                        expectedStatus, dcName=None):
    '''
    The function validateElementStatus compare the status of given element with expected status.
        element = specific element (host,datacenter...)
        elementName = the name of element (<host name> in case of given element is a host)
        expectedStatus = expected status(es) of element (The status of element that we are expecting)
        dcName = the name of Data Center (to retrieve the status of storage domain entity, None by default)
    return values : Boolean value (True/False ) True in case of succes otherwise False
    '''
    attribute = "state"
    try:
        supportedElements = readConfFile(elementsConf, elementConfSection)
    except Exception as err:
        util.logger.error(err)
        return False

    util = get_api(element, collection)

    if element not in supportedElements:
        msg = "Unknown element {0}, supported elements are {1}"
        util.logger.error(msg.format(element, supportedElements.keys()))
        return False

    elementObj = None
    MSG = "Can't find element {0} of type {1} - {2}"

    if element.lower() == "storagedomain":
        if dcName is None:
            ERR = "name of Data Center is missing"
            util.logger.warning(MSG.format(elementName, element, ERR))
            return False

        try:    # Fetch Data Center object in order to get storage domain status
            dcUtil = get_api('data_center', 'datacenters')
            dcObj = dcUtil.find(dcName)
        except EntityNotFound:
            ERR = "Data Center object is needed in order to get storage domain status"
            util.logger.warning(MSG.format(dcName, "datacenter", ERR))
            return False

        elementObj = util.getElemFromElemColl(dcObj, elementName,
                             'storagedomains', 'storage_domain')
    else:
        try:
            elementObj = util.find(elementName)
        except Exception as err:
            util.logger.error(MSG.format(elementName, elementToFind, err))
            return False

        if not hasattr(elementObj.get_status(), attribute):
            msg = "Element {0} doesn't have attribute \'{1}\'"
            util.logger.error(msg.format(element, attribute))
            return False

    expectedStatuses = [status.strip().upper() for status in expectedStatus.split(',')]
    result = elementObj.get_status().get_state().upper() in expectedStatuses

    MSG = "Status of element {0} is \'{1}\' expected statuses are {2}"
    util.logger.warning(MSG.format(elementName,
        elementObj.get_status().get_state().upper(), expectedStatuses))

    return result


def randomStringGeneration(length):
    """
    Description: Generates random strings of required length
    Author: edolinin
    Parameters:
     * length - string length
    Returns: dictionary with generated random string
    """
    randomStrings = {}
    randomStrings['randomString'] = ''.join([random.choice(string.ascii_uppercase + string.digits) \
                                    for x in range(int(length))])

    return True, randomStrings


def startVdsmd(vds, password):
    '''
    Start vdsmd on the given host
    Author: jvorcak
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Machine(vds, 'root', password).util('linux')
    return machine.startService('vdsmd')


def stopVdsmd(vds, password):
    '''
    Stop vdsmd on the given host
    Author: jvorcak
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Machine(vds, 'root', password).util('linux')
    return machine.stopService('vdsmd')


def updateVmStatusInDatabase(vmName, status, vdc, vdc_pass,
        psql_username='postgres', psql_db='rhevm'):
    '''
    Update vm status in the database
    Author: jvorcak
    Parameters:
       * vmName - name of the vm to be modified in the database
       * status - status to be set to the vm
         0-down, 1-up, 2-powering up, 15-locked
       * vdc - address of the setup
       * vdc_pass - password for the vdc
       * psql_username - psql username
       * psql_db - name of the DB
    Return: (True if sql command has been executed successfuly,
             False otherwise)
    '''
    util = get_api('vm', 'vms')
    vm = util.find(vmName)
    machine = Machine(vdc, 'root', vdc_pass).util('linux')
    cmd = ["psql", "-U", psql_username, psql_db, "-c",
            r'"UPDATE vm_dynamic SET status=%d WHERE vm_guid=\'%s\'"' %
            (status,vm.get_id())]

    return machine.runCmd(cmd)


def setSELinuxEnforce(address, password, enforce):
    '''
    Disables SELinux on the machine
    Author: jvorcak
    Parameters:
       * address - ip address of machine
       * password - ssh password for root user
       * enforce - value which should be placed in /selinux/enforce
              should be 0/1
    Return: (True if command executed successfuly, False otherwise)
    '''
    machine = Machine(address, 'root', password).util('linux')
    return machine.setSELinuxEnforce(enforce)


def installRhevm(host_fqdn, root_pass, mac_range, override_iptables='yes',
                 http_port='8080', https_port='8443', auth_pass='123456',
                 db_pass='123456', org_name='redhat', dc_type='NFS',
                 config_nfs='no', nfs_mp='', iso_domain_name='', **kwargs):
    '''
    Install RHEMVM wrapper
    Author: atal
    Parameters:
        * host_fqdn - full remote machine fqdn
        * root_pass - login as root so need a root password
        * dc_type - default datacenter type
        * config_nfs - configure default nfs
        * nfs_mp - in case of configure NFS, provide mount point
        * iso_domain_name - default iso domain name
    Retuen: True in case of success, False otherwise.
    '''
    ROOT='root'
    address = getIpAddressByHostName(host_fqdn)
    if not address:
        logger.error('%s is not resolvable' % host_fqdn)
        return False

    set_params = {'OVERRIDE_IPTABLES'  : override_iptables,
                  'HTTP_PORT'          : http_port,
                  'HTTPS_PORT'         : https_port,
                  'MAC_RANGE'          : mac_range,
                  'HOST_FQDN'          : host_fqdn,
                  'AUTH_PASS'          : auth_pass,
                  'DB_PASS'            : db_pass,
                  'ORG_NAME'           : org_name,
                  'DC_TYPE'            : dc_type,
                  'CONFIG_NFS'         : config_nfs,
                  'NFS_MP'             : nfs_mp,
                  'ISO_DOMAIN_NAME'    : iso_domain_name
                  }
    rhevm = Rhevm(addr=address, user=ROOT, passwd=root_pass)
    return rhevm.install(set_params, addRemoteAD=False, **kwargs)


def removeRhevm(host_fqdn, root_pass):
    '''
    Remove RHEMVM wrapper
    Author: atal
    Parameters:
        * host_fqdn - full remote machine fqdn
        * root_pass - login as root so need a root password
    Retuen: True in case of success, False otherwise.
    '''
    ROOT='root'
    address = getIpAddressByHostName(host_fqdn)
    if not address:
        logger.error('%s is not resolvable' % host_fqdn)
        return False
    rhevm = Rhevm(addr=address, user=ROOT, passwd=root_pass)
    return rhevm.remove()


def upgradeRhevm(host_fqdn, root_pass, rollback=True):
    '''
    Upgrade RHEMVM wrapper
    Author: atal
    Parameters:
        * host_fqdn - full remote machine fqdn
        * root_pass - login as root so need a root password
        * rollback - whether supporting upgrade rollback or not
    Retuen: True in case of success, False otherwise.
    '''
    ROOT='root'
    address = getIpAddressByHostName(host_fqdn)
    if not address:
        logger.error('%s is not resolvable' % host_fqdn)
        return False
    rhevm = Rhevm(addr=address, user=ROOT, passwd=root_pass)
    return rhevm.upgrade(rollback)


def runMultiThreadTaskOnVMs(task, vmNamesList, paramsList):
    '''
    Description: run Multi Thread Task.
    Author: Tomer
    Parameters:
       * task - function to run
       * vmNamesList - list of VMs
       * paramsList - params to function
    Return: task results,
    '''
    threads = []
    for i in range(len(vmNamesList)):
        t = CreateThread(eval(task), **(paramsList[i]))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    results = []
    for t in threads:
        results.append(t.retValue)
    return results


def yum(address, password, package, action):
    """
    Description: wraper for yum functionality
    Parameters:
     * address - target machine
     * password - password for user root
     * package - name of package
     * action - yum action; install/remove/update ...
    Return: True/False
    """
    machine = Machine(address, 'root', password).util('linux')
    return machine.yum(package, action)


@lookingForIpAdressByEntityName("vms", "ip", "vmName")
def runMachineCommand(positive, ip=None, user=None, password=None, type='linux', cmd='', **kwargs):
    '''
    wrapper for runCmd
    '''
    cmd = shlex.split(cmd)
    try:
        if not ip:
            machine = Machine().util()
        else:
            machine = Machine(ip, user, password).util(type)
        ecode, out = machine.runCmd(cmd, **kwargs)
        logger.debug('%s: runcmd : %s, result: %s, out: %s',\
                machine.host, cmd, ecode, out)
        return ecode, {'out': out}
    except Exception as ex:
        logger.error("Failed to run command : %s : %s", cmd, ex)
    return False, {'out': None}


def cleanupData(path):
    if path and os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)

@lookingForIpAdressByEntityName("vms", "ip", "vmName")
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

@lookingForIpAdressByEntityName("vms", "ip", "vmName")
def verifyDataOnVm(ip, user, password, osType, dest, destToCompare):
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
        if not machine.copyFrom(srcLocal, dest, 300):
            logger.error("copy data from %s" % ip)
            return False
        logger.info("compare: %s to %s" % (srcLocal, destToCompare))
        res = machine.compareDirs(srcLocal, destToCompare)
        cleanupData(srcLocal)
        return res
    except Exception as err:
        logger.error("verify data on %s: %s" % (ip, err))
    return False


def rhevmConfig(positive, setup, user, passwd, dbuser, dbpasswd, dbname, \
                jbossRestart, **kwargs):
    """
    Wrapper for rhevmConfig
    """
    try:
        machine = Machine(setup, user, passwd).util('linux')
        return machine.rhevmConfig(dbname=dbname, dbuser=dbuser, dbpasswd=dbpasswd, \
                                    jbossRestart=jbossRestart, **kwargs)
    except Exception:
        logger.error("failed to change rhevm capabilities %s:" % setup, \
                                                            exc_info=True)
    return False


def isToolsOnGuest(positive, ip, user, password, packs, toolsVersion, attempts=1):
    '''Wrapper for isToolsInstalledOnGuest'''
    return isToolsInstalledOnGuest( ip, user, password, toolsVersion,  packs, attempts)


def removeTools(positive, ip, user, password,toolsVersion,packs='desktop', attempts=1):
    ''''Wrapper for removeToolsFromGuest'''
    try:
        toolsFound = removeToolsFromGuest(ip, user, password, toolsVersion, packs=packs, attempts=attempts)
    except Exception as err:
        return False,{'packagesFound' : err}

    if toolsFound:
        toolsFound = ' '.join(toolsFound)
        return False,{'packagesFound' : toolsFound}
    return  True,{'packagesFound' : 'NONE'}


def waitForReboot(positive, ip, user, password, attempts):
    '''
    'Wrapper for waitForGuestReboot
    '''
    return waitForGuestReboot(ip, user, password, attempts)


def installAPT(positive, server, ip, user, password, toolsVersion, clusterVersion, wait=True, attempts=0):
    '''
    wrapper for installAutoUpgraderCD
    '''
    return installAutoUpgraderCD(getIpAddressByHostName(server), ip, user, password, toolsVersion, buildName=clusterVersion, wait=wait, attempts=attempts)


def installGuestToolsFromDir(positive, ip, user, password, build, onlyExtract=False):
    '''
    wrapper for installToolsFromDir
    '''
    return installToolsFromDir(ip, user, password, build, onlyExtract)


def verifyGuestToolsFilesExist(ip, packs='desktop'):
    '''
    wrapper for verifyToolsFilesExist
    '''
    return verifyToolsFilesExist(ip, packs=packs)


def prepareDataForVm(root_dir='/tmp', root_name_prefix='', dir_cnt=1, file_cnt=1):
    '''
    Create local fs tree (directories&files)
    Parameters:
     * root_dir - path to root dir of tree
     * name_prefix - root dir name prefix
     * dir_cnt - count of dirs in tree
     * file_cnt - count of files in tree (files will be randomly distributed
        in dirs)
    Return:
        the absolute pathname of the created directory
    '''
    data_path = None
    rc = True
    try:
        data_path = createDirTree(root_dir=root_dir,
            name_prefix=root_name_prefix, dir_cnt=int(dir_cnt),
            file_cnt=int(file_cnt))
    except Exception as err:
        logger.error('failed to prepare data for VM', err)
        rc = False
    return rc, {'data_path' : data_path}


@contextmanager
def restoringRandomState(seed=None):
    '''
    Saves the state of the random generator if seed is not None, restores that
    after if it was saved.
    '''
    try:
        if seed is not None:
            randState = random.getstate()
            random.seed(seed)
            yield
    finally:
        if randState is not None:
            random.setstate(randState)


def waitUntilPingable(IPs, timeout=180):
    startTime = time.time()
    while True:
        pingResult = pingToVms(IPs)
        dead_machines = [ip for ip, alive in pingResult.iteritems()
                if not alive]
        if not dead_machines:
            break
        if timeout < time.time() - startTime:
            MSG = "Timeouted when waiting for IPs {0} to be pingable."
            raise APITimeout(MSG.format(dead_machines))
        MSG = "IPs {0} are still not responding on ping."
        logger.info(MSG.format(dead_machines))
        time.sleep(10)
    logger.info("All IP's are pingable now.")


@lookingForIpAdressByEntityName("vms", "ip", "vmName")
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


def updateTools(positive, server, ip, toolsVersion, clusterVersion, attempts=1):
    '''Wrapper for updateGuestTools'''
    return updateGuestTools(getIpAddressByHostName(server), ip, toolsVersion, clusterVersion, attempts)


def rebootMachine(positive, ip, user, password, osType):
    '''
    Desciption: wrapper function reboot host.
    Author: Tomer
    Parameters:
     * ip = VM's ip.
     * osType - linux or windows
    Return Value: status True or False
    '''
    try:
        machine = Machine(ip, user, password).util(osType)
        return machine.reboot()
    except Exception as err:
        logger.error(str(err))
        return False


def convertStrToList(positive, string):
    '''
    Desciption: utils to convert string to list that seprated by commas.
    Author: Tomer
    Parameters:
    * string = any string that separated by commas.
    Return Value: status True and list or False with empty list,
    '''
    if not positive:
        logger.error('Invalid value for positive')
        return False, {'list' : []}
    if not isinstance(string, str):
        logger.error(' parameter error, Only string is accepted ')
        return False, {'list' : []}
    return True, {'list' : string.split(',')}


def convertOsListToOsTypeDict(positive, osList):
    '''
    Desciption:associate osType to os name.
    Author: Tomer
    Parameters:
    * osList = list of os name
    Return Value: Dictionary osName->osType and True if all params are valid, otherwise False,
    '''
    if not isinstance(osList, str):
        util.logger.error('VMs parameter error, Only string is accepted ')
        return False

    osTypeDict = {}
    for os in osList.split(','):
        (status, res) = convertOsNameToOsTypeElement(positive, os)
        if not status:
            logger.error("os params error, failed to convert os %s to element" % os)
            return status, osTypeDict
        if re.search('win', os, re.I):
            osTypeDict[res['osTypeElement']] = 'windows'
        elif re.search('Linux', os, re.I):
            osTypeDict[res['osTypeElement']] = 'linux'
        else:
            logger.error("Only windows or linux os supported")
            return False, osTypeDict
    return True, {'osTypeDict':osTypeDict}


def reportParallelVMsConnectivity(positive, timeOut, dictResult, osList, index):
    '''
    Description: Parameters report to Atom DB for ParallelVMsConnectivity:
    Author: Tomer
    Parameters:
        * timeOut - time out to to connect to vm
        * dictResult - dictionary vmName->timeToLoad
        * osList - list of vms
        * index - loop_index report to atom Db
    Return Values status and Dictionary to reportDB func
    '''
    status = True
    if dictResult[osList[index]] > timeOut or dictResult[osList[index]] < 10 :
        status = False
    return reportDB(positive, status, 'totalInstallTime', dictResult[osList[index]], 'os', osList[index])


def reportParallelGuestTools(positive, resultsAfterInstall, resultsAfterUninstall, resultsAfterAPT, resultsOldTools, resultsAptUpgrade, resultsManualUpgrade, osList, index):
    '''
    Description: Parameters report to Atom DB for GuestTools test:
    Author: Tomer
    Parameters:
        * results* - guest tools results for each test case
        * osList - list of vms
        * index - loop_index report to atom Db
    Return Values status and results to reportDB func
    '''
    status = True
    for statusResult in resultsAfterInstall[index], resultsAfterUninstall[index][0], resultsAfterAPT[index], resultsOldTools[index], resultsAptUpgrade[index], resultsManualUpgrade[index]:
        if statusResult is False:
            status = False
            break;
    return reportDB(positive, status, 'os', osList[index],'missingTools',resultsAfterInstall[index],'packageFoundAferUninstall',resultsAfterUninstall[index][1]['packagesFound'],'missingToolsAfterAPT',resultsAfterAPT[index],'missingOldTools',resultsOldTools[index],'missingToolsAfterAptUpgrade',resultsAptUpgrade[index],'missingToolsAfterManualUpgrade',resultsManualUpgrade[index])


def calculateElapsedTime(positive, state='start', measureUnit='sec',startTime=1):
    '''
    Description: function calculate elapsed time, need to call to func twice: start time and end time.
    Author: Tomer
    Parameters:
     * state = status start or end.
     * measureUnit = sec/min/hour
     * startTime = relevant when state equal to end(sec)
    Return Values:
     * status True/False
     * if state = start -> start time
     * if state = end -> calculate elapsed time
    '''
    if state == 'start':
        return True, {'calculateTime' : time.time()}
    elif state =='end':
        measureDict ={'sec' : 1 ,'min' : 60 ,'hour' : 3600}
        if not measureDict.has_key(measureUnit):
            logger.error('Invalid parameter measureUnit, Should be sec/min/hour')
            return False, {'calculateTime' : -1}
        return True, {'calculateTime' : int((time.time() - (startTime))/measureDict[measureUnit])}
    else:
        logger.error('Invalid state param, should be start/end')
        return False, {'calculateTime' : -1}


def shutdownHost(positive, ip, user, password, osType):
    '''
    Desciption: wrapper function shutdown host.
    Author: Tomer
    Parameters:
     * ip = VM's ip.
     * osType - linux or windows
    Return Value: status True or False
    '''
    try:
        machine = Machine(ip, user, password).util(osType)
        return machine.shutdown()
    except Exception as err:
        logger.error(str(err))
        return False
    

def convertOsNameToOsTypeElement(positive, osName):
    '''
    function convert Os Name from ATOM to OS Type Element compatible with Rest-Api
    '''
    if re.search('win', osName, re.I):
        return True, {'osTypeElement': osName.replace(' ', '')}
    elif re.search('Linux',osName,re.I):
        version = re.search('Linux\s+(\d+)',osName,re.I)
        newOsName = 'RHEL' +version.group(1)
        if re.search('x64',osName,re.I):
            newOsName = newOsName + 'x64'
        if re.search('rhevm',osName,re.I):
            newOsName = newOsName + '_RHEVM'
        return True, {'osTypeElement': newOsName}
    else:
        return False, {'osTypeElement': None}
    

def cobblerAddNewSystem(cobblerAddress, cobblerUser, cobblerPasswd, mac, osName):
    '''Create new system with specific MAC address
       mac = MAC address of system (it will be name of system)
       osName = profile of system
       return True/False
    '''
    try:
        api = Cobbler(host=cobblerAddress, user=cobblerUser, passwd=cobblerPasswd)
        return api.addNewSystem(mac, osName)
    except Exception as err:
        logger.error(str(err))
        return False


def cobblerRemoveSystem(cobblerAddress, cobblerUser, cobblerPasswd, mac):
    '''
    Function removes item acorging name
    mac = name of system
    return True/False
    '''
    try:
        api = Cobbler(host=cobblerAddress, user=cobblerUser, passwd=cobblerPasswd)
        return api.removeSystem(mac)
    except Exception as err:
        logger.error(str(err))
        return False


def cobblerSetLinuxHostName(cobblerAddress, cobblerUser, cobblerPasswd, name, hostname):
    '''Set linux system hostname
        name = system name
        hostname = New system hostname
        return True/False
    '''
    try:
        api = Cobbler(host=cobblerAddress, user=cobblerUser, passwd=cobblerPasswd)
        return api.setSystemHostName(name=name, hostname=hostname)
    except Exception as err:
        logger.error(str(err))
        return False
    

def getImageByOsType(positive, osType, slim = False):
    '''
    Function get osTypeElement and return image from action.conf file.
    in case os windows: return cdrom_image and unattended floppy.
    in case os rhel: return os profile compatible with cobbler.
    Author: Tomer
    '''
    if slim:
        if re.search('rhel', osType, re.I):
            # Following line should be removed once RHEL5_SLIM, and RHEL6_SLIM will be added.
            if ((osType != 'RHEL5') and (osType != 'RHEL6')):
                osType = osType + '_SLIM'
    try:
        supportedOs = readConfFile(elementsConf, osType)
    except Exception as err:
        logger.error(err)
        return False, {'osBoot' : None,'floppy' : None}

    if re.search('rhel', osType, re.I):
        return True, {'osBoot' : supportedOs['profile'],'floppy' : None}
    elif re.search('win', osType, re.I):
        return True, {'osBoot' : supportedOs['cdrom_image'], 'floppy' : supportedOs['floppy_image']}
    

def getOsParamsByOsType(positive, osType):
    '''
    Function get osTypeElement and return os params from element.conf file.
    Author : Tomer
    Parameters:
    * osType - os type as writthen in rest API
    Return Values:
    True if found os type in element conf and return in dictionary: osName, osArch, osRelease
    False if not found and return None to all params
    '''
    try:
        supportedOs = readConfFile(elementsConf, osType)
    except Exception as err:
        logger.error(err)
        return False, {'name' : None, 'arch' : None, 'release' : None, 'type' : None}
    if not supportedOs.has_key('release'):
        supportedOs['release'] = None
    return True, {'osName' : supportedOs['name'], 'osArch' : supportedOs['arch'], 'osRelease' : supportedOs['release'], 'type' : supportedOs['type']}


def toggleServiceOnHost(positive, host, user, password, service, action, force="false"):
    """
        Toggle service on host with specified action.
        Author: mbenenso
        Parameters:
         * positive - test type (positive/negative)
         * host - IP address of host
         * user - user name
         * password - user password
         * service - the name of the service
         * action - desired action as string, supported actions:
                     (START, STOP, RESTART, RELOAD, STATUS)
         * force - indicates force action ("false" by default)
        Return: a boolean result of the action,
                if action is "status" then the status output is returned
    """
    result = False
    action_enum = eServiceAction.parse(action.upper())
    machine = Machine(host, user, password).util("linux")
    if machine is not None:
        if action == "status":
            status = machine.getServiceStatus(service)
            msg = "status of service \"{0}\" is: {1}"
            logger.info(msg.format(service, status))
            return True

        force = force.lower() == "true"
        machine.enableServiceSupport()
        result = machine.service.toggleService(service, action_enum, force)

    return result == positive


def isServiceRunning(positive, host, user, password, service):
    """
        Check if service is running on host.
        Author: mbenenso
        Parameters:
         * positive - test type (positive/negative)
         * host - IP address of host
         * user - user name
         * password - user password
         * service - the name of the service
        Return: a boolean value which indicates whether
                the service is running on host or not
    """
    result = False
    machine = Machine(host, user, password).util("linux")
    if machine is not None:
        result = machine.isServiceRunning(service)

    return result == positive


def reportDB(positive, *args):
    '''
    Description: Parameters report to Atom DB:
    Author: Tomer
    Parameters:
     * args[0] =status True/False
     * args = odd parameters keys.
              even parameters values
    Return Values status and Dictionary to report
    '''
    dict = {}
    if len(args) >= 3 and (args[0] == True or args[0] == False) and len(args)%2 == 1:
        for i in range(1, len(args), 2):
            dict[args[i]] = str(args[i+1])
        return args[0], dict
    else:
        logger.error('invalid params')
        return False, dict


def calculateTemplateGuid(positive, storageDomainType, os, architecture, templateType, osRelease = None, driverType = None):
    """Wrapper for CalculateTemplateUuid"""
    uuid = calculateTemplateUuid(storageDomainType, os, architecture, templateType, osRelease, driverType)
    if uuid:
        return True, {'uuid' : uuid}
    return False, {'uuid' : None}


def convertMacToIpAddress(positive, mac, subnetClassB = '10.35', vlan=0):
    """Wrapper for convertMacToIp"""
    ip = convertMacToIp(mac, subnetClassB, vlan)
    logger.info('MAC: %s with VLAN: %s converted to IP: %s' % (mac,vlan,str(ip)))
    if ip:
        return True, {'ip' :ip}
    return False, {'ip' : None}


def searchElement(positive, element, collection, keyName, searchValue):
    '''
    The function searchElement search specific element by key name and value.
        element = specific element (host,datacenter...)
        keyName = the key name (element name or element status ...)
        searchValue = the value what we want find(Example: key name = ip,search value = 1.1.1.1)
    return values : True and list of elements or False and None
    '''
    util = get_api(element, collection)
    try:
        supportedElements = readConfFile(elementsConf, elementConfSection)
    except Exception as err:
        util.logger.error(err)
        return False, None
    if not element in supportedElements:
        util.logger.error ("Unknown element %s , supported elements: %s" % (element, ",".join(supportedElements.keys())))
        return False, None

    elements = util.query(keyName + "=" + searchValue)
    if elements:
        return True, elements

    return False, None


def checkHostConnectivity(positive, ip, user, password,osType, attempt=1, interval=1, remoteAgent=None):
    '''wrapper function check if windows server up and running
       indication to server up and running if wmi query return SystemArchitecture and elapsed time'''
    try:
        t1 = time.time()
        machine = Machine(ip, user, password).util(osType)
        if remoteAgent == 'staf':
            status = machine.isConnective(attempt, interval, remoteAgent)
        else:
            status = machine.isConnective(attempt, interval, True)
        t2 = time.time()
        logger.info('Host: %s, Connectivity Status: %s, Elapsed Time: %d' % (ip,status,int(t2-t1)))
        return status, {'elapsedTime' : int(t2 - t1)}
    except Exception as err:
        logger.error(str(err))
        return False, {'elapsedTime' : -1}


def resetMapperEntityNamesToIpAddress(entity='.+', entityName='.+', expTime=None):
    """
    Description: Removes all/specific record (entityName -> ip-address) from cache
    Parameters:
     * entity - type of entity (e.g.: vms), you can use regexpr
     * entityName - name of entity, you can use regexpr
     * expTime - sets expiration time for cached records (seconds)
    """
    ipVar, nameVar, oldExpTime, cache = lookingForIpAdressByEntityName.func_defaults
    with cache:
        reg = re.compile('^%s-%s$' % (entity, entityName))
        elms = [x for x in cache.keys() if reg.match(x)]
        for elm in elms:
            del cache[elm]

    if expTime is None:
        expTime = oldExpTime
    lookingForIpAdressByEntityName.func_defaults = (ipVar, nameVar, expTime, cache)
    return True