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

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import logging
from lxml import etree
import random
import re
import time
from traceback import format_exc
import os
import shlex
import shutil
from socket import gethostname
import string

from functools import wraps
import art.test_handler.settings as settings
from art.core_api.validator import compareCollectionSize
from art.core_api.apis_utils import TimeoutingSampler
from utilities.utils import readConfFile, calculateTemplateUuid, \
convertMacToIp, pingToVms, getIpAddressByHostName, createDirTree
from utilities.machine import Machine, eServiceAction, LINUX
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from utilities.tools import updateGuestTools, isToolsInstalledOnGuest, \
    removeToolsFromGuest, waitForGuestReboot, installAutoUpgraderCD, \
    installToolsFromDir, verifyToolsFilesExist
#from upgradeSetup.prepSetup import Rhevm
from art.rhevm_api.utils.threads import CreateThread, ThreadSafeDict
from art.core_api import is_action

logger = logging.getLogger('test_utils')

#The location of all supported elements
#The name of section in the element configuration file
elementConfSection = 'elements'
#The location of all supported os

api = None

IFCFG_NETWORK_SCRIPTS_DIR = '/etc/sysconfig/network-scripts'
SYS_CLASS_NET_DIR = '/sys/class/net'
MTU_DEFAULT_VALUE = 1500
TASK_TIMEOUT = 300
TASK_POLL = 5
ENGINE_HEALTH_URL = "http://localhost/OvirtEngineWeb/HealthStatus"
ENGINE_SERVICE = "ovirt-engine"
SUPERVDSMD = "supervdsmd"

RHEVM_UTILS_ENUMS = settings.opts['elements_conf']['RHEVM Utilities']


class PSQLException(Exception):
    pass


def get_api(element, collection):
    '''
    Fetch proper API instance based on engine type
    '''

    engine = settings.opts.get('engine')
    if engine == 'rest':
        from art.core_api.rest_utils import RestUtil
        api = RestUtil(element, collection)
    if engine == 'sdk':
        from art.core_api.ovirtsdk_utils import SdkUtil
        api = SdkUtil(element, collection)
    if engine == 'cli':
        from art.core_api.ovirtcli_utils import CliUtil
        api = CliUtil(element, collection)
    if engine == 'java':
        from art.core_api.ovirtsdk_java_utils import JavaSdkUtil
        api = JavaSdkUtil(element, collection)
    return api


def split(s):
    '''
    Split `s` by comma and/or by whitespace.

    Parameters: s -- A string-like object to split.
    Return: A sequence of strings-like objects.
    '''
    return s.replace(',', ' ').split()


@is_action()
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
            datum = stat.get_values().get_value()[0].get_datum()
            if stat.get_values().get_type() == "INTEGER":
                values[stat.get_name()] = int(float(datum))
                #return int(stat.values.value.datum)
            elif stat.get_values().get_type() == "DECIMAL":
                values[stat.get_name()] = float(datum)
    return values


def lookingForIpAdressByEntityName(entity, ipVar="ip", nameVar="vmName", expTime=60*10, cache=ThreadSafeDict()):
    '''
    Description: Decorator replaces non-defined ipVar parameter.
                 Result is cached until expTime, for continuous calling
    Parameters:
     * entity - name of entity (vms, hosts)
     * ipVar - name of variable represents IP for specific entity
     * nameVar - name of variable used to define entity name
     * expTime - expiration time (seconds)
    '''
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


@is_action('validateEntityStatus')
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
    util = get_api(element, collection)

    try:
        supportedElements = settings.opts['elements_conf'][elementConfSection]
    except Exception as err:
        util.logger.error(err)
        return False

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
            util.logger.error(MSG.format(elementName, element, err))
            return False

        if not hasattr(elementObj.get_status(), attribute):
            msg = "Element {0} doesn't have attribute \'{1}\'"
            util.logger.error(msg.format(element, attribute))
            return False

    expectedStatuses = [status.strip().upper() for status in expectedStatus.split(',')]
    result = elementObj.get_status().get_state().upper() in expectedStatuses

    if not result:
        MSG = "Status of element {0} is \'{1}\' expected statuses are {2}"
        util.logger.warning(MSG.format(elementName,
            elementObj.get_status().get_state().upper(), expectedStatuses))

    return result


@is_action('randomString')
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


@is_action()
def startVdsmd(vds, password):
    '''
    Start vdsmd on the given host
    Author: jvorcak
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Machine(vds, 'root', password).util(LINUX)
    return machine.startService('vdsmd')

@is_action()
def restartVdsmd(vds, password, supervdsm=False):
    '''
    **Description**:Restart vdsmd on the given host
    **Author**: gcheresh
    Parameters:
       *  *vds* - name of the host
       *  *password* - ssh password for the host
       *  *supervdsm* - flag to stop supervdsm service (start vdsm also start
           supervdsm)
    '''
    machine = Machine(vds, 'root', password).util(LINUX)
    if supervdsm:
        if not machine.stopService(SUPERVDSMD):
            logger.error("Stop supervdsm service failed")
            return False

    return machine.restartService('vdsmd')

@is_action()
def stopVdsmd(vds, password):
    '''
    Stop vdsmd on the given host
    Author: jvorcak
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Machine(vds, 'root', password).util(LINUX)
    return machine.stopService('vdsmd')

@is_action()
def restartNetwork(vds, password):
    '''
    Restart network on the given host
    Author: gcheresh
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Machine(vds, 'root', password).util(LINUX)
    return machine.restartService('network')

@is_action()
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
    machine = Machine(vdc, 'root', vdc_pass).util(LINUX)
    cmd = ["psql", "-U", psql_username, psql_db, "-c",
            r'"UPDATE vm_dynamic SET status=%d WHERE vm_guid=\'%s\'"' %
            (status, vm.get_id())]

    return machine.runCmd(cmd)


@is_action()
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
    machine = Machine(address, 'root', password).util(LINUX)
    return machine.setSELinuxEnforce(enforce)


@is_action()
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
    ROOT = 'root'
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


@is_action()
def removeRhevm(host_fqdn, root_pass):
    '''
    Remove RHEMVM wrapper
    Author: atal
    Parameters:
        * host_fqdn - full remote machine fqdn
        * root_pass - login as root so need a root password
    Retuen: True in case of success, False otherwise.
    '''
    ROOT = 'root'
    address = getIpAddressByHostName(host_fqdn)
    if not address:
        logger.error('%s is not resolvable' % host_fqdn)
        return False
    rhevm = Rhevm(addr=address, user=ROOT, passwd=root_pass)
    return rhevm.remove()


@is_action()
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
    ROOT = 'root'
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


@is_action()
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
    machine = Machine(address, 'root', password).util(LINUX)
    return machine.yum(package, action)


@is_action()
def cleanupData(path):
    if path and os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    return True

@is_action()
def rhevmConfig(positive, setup, user, passwd, dbuser, dbpasswd, dbname, \
                jbossRestart, **kwargs):
    """
    Wrapper for rhevmConfig
    """
    try:
        machine = Machine(setup, user, passwd).util(LINUX)
        return machine.rhevmConfig(dbname=dbname, dbuser=dbuser, dbpasswd=dbpasswd, \
                                    jbossRestart=jbossRestart, **kwargs)
    except Exception:
        logger.error("failed to change rhevm capabilities %s:" % setup, \
                                                            exc_info=True)
    return False


@is_action()
def isToolsOnGuest(positive, ip, user, password, packs, toolsVersion, attempts=1):
    '''Wrapper for isToolsInstalledOnGuest'''
    return isToolsInstalledOnGuest(ip, user, password, toolsVersion, packs, attempts)


@is_action()
def removeTools(positive, ip, user, password, toolsVersion, packs='desktop', attempts=1):
    ''''Wrapper for removeToolsFromGuest'''
    try:
        toolsFound = removeToolsFromGuest(ip, user, password, toolsVersion, packs=packs, attempts=attempts)
    except Exception as err:
        return False, {'packagesFound' : err}

    if toolsFound:
        toolsFound = ' '.join(toolsFound)
        return False, {'packagesFound' : toolsFound}
    return  True, {'packagesFound' : 'NONE'}


@is_action()
def waitForReboot(positive, ip, user, password, attempts):
    '''
    'Wrapper for waitForGuestReboot
    '''
    return waitForGuestReboot(ip, user, password, attempts)


@is_action()
def installAPT(positive, server, ip, user, password, toolsVersion, clusterVersion, wait=True, attempts=0):
    '''
    wrapper for installAutoUpgraderCD
    '''
    return installAutoUpgraderCD(getIpAddressByHostName(server), ip, user, password, toolsVersion, buildName=clusterVersion, wait=wait, attempts=attempts)


@is_action()
def installGuestToolsFromDir(positive, ip, user, password, build, onlyExtract=False):
    '''
    wrapper for installToolsFromDir
    '''
    return installToolsFromDir(ip, user, password, build, onlyExtract)


@is_action()
def verifyGuestToolsFilesExist(ip, packs='desktop'):
    '''
    wrapper for verifyToolsFilesExist
    '''
    return verifyToolsFilesExist(ip, packs=packs)


@is_action()
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


@is_action()
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


@is_action()
def updateTools(positive, server, ip, toolsVersion, clusterVersion, attempts=1):
    '''Wrapper for updateGuestTools'''
    return updateGuestTools(getIpAddressByHostName(server), ip, toolsVersion, clusterVersion, attempts)


@is_action()
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


@is_action()
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


@is_action()
def convertOsListToOsTypeDict(positive, osList):
    '''
    Desciption:associate osType to os name.
    Author: Tomer
    Parameters:
    * osList = list of os name
    Return Value: Dictionary osName->osType and True if all params are valid, otherwise False,
    '''
    if not isinstance(osList, str):
        # FIXME: what util shold be here?
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
            osTypeDict[res['osTypeElement']] = LINUX
        else:
            logger.error("Only windows or linux os supported")
            return False, osTypeDict
    return True, {'osTypeDict':osTypeDict}


@is_action()
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


@is_action()
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
    return reportDB(positive, status, 'os', osList[index], 'missingTools', resultsAfterInstall[index], 'packageFoundAferUninstall', resultsAfterUninstall[index][1]['packagesFound'], 'missingToolsAfterAPT', resultsAfterAPT[index], 'missingOldTools', resultsOldTools[index], 'missingToolsAfterAptUpgrade', resultsAptUpgrade[index], 'missingToolsAfterManualUpgrade', resultsManualUpgrade[index])


@is_action()
def calculateElapsedTime(positive, state='start', measureUnit='sec', startTime=1):
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
    elif state == 'end':
        measureDict = {'sec' : 1 , 'min' : 60 , 'hour' : 3600}
        if not measureDict.has_key(measureUnit):
            logger.error('Invalid parameter measureUnit, Should be sec/min/hour')
            return False, {'calculateTime' :-1}
        return True, {'calculateTime' : int((time.time() - (startTime)) / measureDict[measureUnit])}
    else:
        logger.error('Invalid state param, should be start/end')
        return False, {'calculateTime' :-1}


@is_action()
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


@is_action()
def convertOsNameToOsTypeElement(positive, osName):
    '''
    function convert Os Name from ATOM to OS Type Element compatible with Rest-Api
    '''
    if re.search('win', osName, re.I):
        return True, {'osTypeElement': osName.replace(' ', '')}
    elif re.search('Linux', osName, re.I):
        version = re.search('Linux\s+(\d+)', osName, re.I)
        newOsName = 'RHEL' + version.group(1)
        if re.search('x64', osName, re.I):
            newOsName = newOsName + 'x64'
        if re.search('rhevm', osName, re.I):
            newOsName = newOsName + '_RHEVM'
        return True, {'osTypeElement': newOsName}
    else:
        return False, {'osTypeElement': None}


@is_action()
def getImageByOsType(positive, osType, slim=False):
    '''
    Function get osTypeElement and return image from action.conf file.
    in case os windows: return cdrom_image and unattended floppy.
    in case os rhel: return os profile compatible with cobbler.
    Author: Tomer
    '''
    if slim:
        if re.search('rhel', osType, re.I):
            # Following line should be removed once RHEL5_SLIM, and RHEL6_SLIM
            # will be added.
            if ((osType != 'RHEL5') and (osType != 'RHEL6')):
                osType = osType + '_SLIM'
    try:
        supportedOs = settings.opts['elements_conf'][osType]
    except Exception as err:
        logger.error(err)
        return False, {'osBoot': None, 'floppy': None}

    if re.search('rhel', osType, re.I):
        return True, {'osBoot': supportedOs['profile'], 'floppy': None}
    elif re.search('win', osType, re.I):
        return True, {'osBoot': supportedOs['cdrom_image'],
                      'floppy': supportedOs['floppy_image']}


@is_action()
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
        supportedOs = settings.opts['elements_conf'][osType]
    except Exception as err:
        logger.error(err)
        return False, {'name' : None, 'arch' : None, 'release' : None, 'type' : None}
    if not supportedOs.has_key('release'):
        supportedOs['release'] = None
    return True, {'osName' : supportedOs['name'], 'osArch' : supportedOs['arch'], 'osRelease' : supportedOs['release'], 'type' : supportedOs['type']}


@is_action()
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
                if action is "status" then True is returned if
                service is running, false otherwise
    """
    result = False
    machine = Machine(host, user, password).util(LINUX)
    if machine is not None:
        if action == "status":
            return machine.isServiceRunning(service)

        force = force.lower() == "true"
        action_enum = eServiceAction.parse(action.upper())
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
    machine = Machine(host, user, password).util(LINUX)
    if machine is not None:
        result = machine.isServiceRunning(service)

    return result == positive


@is_action()
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
    if len(args) >= 3 and (args[0] == True or args[0] == False) and len(args) % 2 == 1:
        for i in range(1, len(args), 2):
            dict[args[i]] = str(args[i + 1])
        return args[0], dict
    else:
        logger.error('invalid params')
        return False, dict


@is_action()
def calculateTemplateGuid(positive, storageDomainType, os, architecture, templateType, osRelease=None, driverType=None):
    """Wrapper for CalculateTemplateUuid"""
    uuid = calculateTemplateUuid(storageDomainType, os, architecture, templateType, osRelease, driverType)
    if uuid:
        return True, {'uuid' : uuid}
    return False, {'uuid' : None}


@is_action()
def convertMacToIpAddress(positive, mac, subnetClassB='10.35', vlan=0):
    """Wrapper for convertMacToIp"""
    ip = convertMacToIp(mac, subnetClassB, vlan)
    logger.info('MAC: %s with VLAN: %s converted to IP: %s' % (mac, vlan, str(ip)))
    if ip:
        return True, {'ip' :ip}
    return False, {'ip' : None}


@is_action()
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
        supportedElements = settings.opts['elements_conf'][elementConfSection]
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


@is_action()
def checkHostConnectivity(positive, ip, user, password, osType, attempt=1, interval=1, remoteAgent=None):
    '''wrapper function check if windows server up and running
       indication to server up and running if wmi query return SystemArchitecture and elapsed time'''
    try:
        t1 = time.time()
        logger.debug("Checking %s %s host connectivity", ip, osType)
        machine = Machine(ip, user, password).util(osType)
        if remoteAgent == 'staf':
            status = machine.isConnective(attempt, interval, remoteAgent)
        else:
            status = machine.isConnective(attempt, interval, True)
        t2 = time.time()
        logger.info('Host: %s, Connectivity Status: %s, Elapsed Time: %d' % (ip, status, int(t2 - t1)))
        return status, {'elapsedTime' : int(t2 - t1)}
    except Exception as err:
        logger.error(str(err))
        return False, {'elapsedTime' :-1}


@is_action()
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


@is_action()
def removeFileOnHost(positive, ip, filename, user='root',
                     password='qum5net', osType=LINUX):
    '''
    Description: remov file on remote host
    Author: imeerovi
    Parameters:
    * ip - name/ip of host
    * user - username
    * password - password
    * filename - file to erase
    * osType - type os OS on remote machine (linux, windows) [linux]
    Return: True remove operation sucseeded
            False in other case.
    '''
    machine = Machine(ip, user, password).util(osType)
    if machine == None:
        return False
    return machine.removeFile(filename)


@is_action()
def removeDirOnHost(positive, ip, dirname, user='root',
                     password='qum5net', osType=LINUX):
    """
    Description: Removes file on remote machine
    Author: imeerovi
    Parameters:
     * ip - ip of remote machine
     * user - username
     * password - password
     * direname - name of directory that will be removed
     * osType - type os OS on remote machine (linux, windows) [linux]
     Return: True remove operation sucseeded
            False in other case.
    """
    machine = Machine(ip, user, password).util(osType)
    if machine == None:
        return False
    if osType == LINUX:
        return machine.removeFile(dirname)
    elif osType == 'windows':
        return machine.removeDir(dirname)


def searchForObj(util, query_key, query_val, key_name,
                        max= -1, case_sensitive=True,
                        expected_count=None):
    '''
    Description: search for an object by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in the object equivalent to query_key
       * max - maximum number of objects to return
       * case_sensitive - case sensitive or not
    Return: status (True if expected number of objects equal to
                    found by search, False otherwise)
    '''
    if expected_count is None:
        expected_count = 0
        objs = util.get(absLink=False)

        pattern = query_val

        if not case_sensitive:
            pattern = "(?i)%s" % pattern

        if re.match(r'(.*)\*$', query_val):
            pattern = r'^%s' % pattern

        for obj in objs:
            objProperty = getattr(obj, key_name)

            if re.match(pattern, objProperty):
                expected_count += 1

        if max > 0:
            expected_count = min(expected_count, max)

    contsraint = "{0}={1}".format(query_key, query_val)
    query_objs = util.query(contsraint, max=max,
                    case_sensitive=str(case_sensitive).lower())
    status = compareCollectionSize(query_objs, expected_count, util.logger)

    return status


def getImageAndVolumeID(vds, vds_username, vds_password, spool_id, domain_id,
                        object_id, idx):
    """
    Description: Searches for volumes and images on storage domain
    Parameters:
        * vds - host that has mounted storage domain below
        * vds_username - username of root on vds
        * vds_password - password for root account on vds
        * spool_id - storage pool ID containing storage domain below
        * domain_id - storage domain ID that has template or vm on it
        * object_id - id of template/vm
        * idx - index of disk
    Author: jlibosva
    Return: Tuple (volume_id, image_id) if found, (None, None) otherwise
    """
    path_to_ovf = '/rhev/data-center/%s/%s/master/vms/%s/%s.ovf' % \
                  (spool_id, domain_id, object_id, object_id)

    logger.debug("Checking file %s on host %s", path_to_ovf, vds)

    namespace_dict = {
        'ovf' : "http://schemas.dmtf.org/ovf/envelope/1/",
        'xsi' : "http://www.w3.org/2001/XMLSchema-instance"
    }

    host = Machine(vds, vds_username, vds_password).util(LINUX)
    with host.ssh as ssession:
        ovf_hnd = ssession.getFileHandler().open(path_to_ovf)
        root_elem = etree.parse(ovf_hnd).getroot()
        ovf_hnd.close()

    disks_elements = root_elem.xpath('Section[@xsi:type="ovf:DiskSection_Type"]/Disk',
                                 namespaces=namespace_dict)


    attrib = '{' + namespace_dict['ovf'] + '}fileRef'
    try:
        image_and_volume = disks_elements[idx].attrib[attrib].split('/', 1)
    except IndexError:
        return (None, None)

    return tuple(image_and_volume)


@is_action()
def setPersistentNetwork(host, password):
    '''
    Ensure that Network configurations are persistent
    Author: atal
    Parameters:
       * host - remote machine ip address or fqdn
       * password - password for root user
    Return: (True if command executed successfuly, False otherwise)
    '''
    vm_obj = Machine(host, 'root', password).util(LINUX)

    persistent_rule = "/etc/udev/rules.d/70-persistent-net.rules"
    cmd = ["cat", "/dev/null", ">", persistent_rule]
    rc, out = vm_obj.runCmd(cmd)
    logger.debug('Running command %s : result %s' % (cmd, rc))
    if not rc:
        logger.error('Failed to erase %s. %s' % (persistent_rule, out))
        return False

    nics = set()
    rc, out = vm_obj.runCmd(['ls', '-la', '/sys/class/net', '|', \
                             'grep', "'pci'", '|', \
                             'grep', '-o', "'[^/]*$'"])
    out = out.strip()
    if not rc or not out:
        logger.error('PCI interfaces do not exist in %s' % host)
        return False
    nics |= set(out.splitlines())

    for nic in nics:
        nic = 'ifcfg-%s' % nic
        ifcfg_tmp = os.path.join('/tmp', nic)
        ifcfg_path = os.path.join('/etc/sysconfig/network-scripts', nic)

        cmd = ["sed", "/HWADDR/d", ifcfg_path, ">", ifcfg_tmp, ";", "mv",
               ifcfg_tmp, ifcfg_path, "-f"]
        logger.debug('Running command %s' % cmd)
        rc, out = vm_obj.runCmd(cmd)
        if not rc:
            logger.error("Failed to remove HWADDR. %s" % out)
            return False

        rc, out = vm_obj.runCmd(['cat', ifcfg_path])
        logger.debug('%s Final configurations: \n%s' % (nic, out))

    return True


@is_action()
def getSetupHostname(vdc):
    """
    Description: Gets the hostname of setup based on vdc, if vdc is not
                 running on localhost then vdc parameter is returned
    Author: jlibosva
    Parameters: vdc - vdc hostname or IP
    Return: True and hostname of setup
    """
    is_local = vdc == "localhost" or vdc == "127.0.0.1"
    hostname = gethostname() if is_local else vdc

    return True, { 'hostname' : hostname }


def runSQLQueryOnSetup(vdc, vdc_pass, query,
                       psql_username='postgres', psql_db='engine', timeout=10):
    """
    Runs a SQL query on the setup database.
    Parameters:
      * vdc - setup hostname or IP address
      * vdc_pass - password of setup's root account
      * query - the SQL query to run
      * psql_username - username of postgres
      * psql_db - the database to run the query on
    Returns True and a list of the records in the query output on success
            False and an empty list on failure
    """
    setup = Machine(vdc, 'root', vdc_pass).util(LINUX)
    sep = '__RECORD_SEPARATOR__'
    cmd = ['psql', '-d', psql_db, '-U', psql_username, '-R', sep, '-t', '-A', '-c', query]
    passed, out = setup.runCmd(cmd, timeout=timeout, conn_timeout=timeout)
    if not passed:
        logger.error("Query %s failed with an output: %s", query, out)
        return False, []
    return True, [a.strip().split('|') for a in out.strip().split(sep) if a.strip()]


def get_running_tasks(vdc, vdc_pass, sp_id, db_name, db_user):
    """
    Description: Gets tuple (task_id, storage_pool_id) for all tasks running
                 in rhevm
    Parameters:
        * vdc - ip or hostname of rhevm
        * vdc_pass - root password for rhevm machine
        * sp_id - storage pool id
        * db_name - name of the rhevm database
        * db_user - name of the user of database
    """
    query = "select task_id, vdsm_task_id, task_params_class from " \
            "async_tasks where storage_pool_id = '%s'" % sp_id
    status, tasks = runSQLQueryOnSetup(vdc, vdc_pass, query, db_user, db_name)
    if not status:
        raise PSQLException("runSQLQueryOnSetup returned False")
    logger.debug("Query %s returned list: %s", query, tasks)
    return tasks


@is_action("waitForTasks")
def wait_for_tasks(
        vdc, vdc_password, datacenter,
        db_name=RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
        db_user=RHEVM_UTILS_ENUMS['RHEVM_DB_USER'], timeout=TASK_TIMEOUT,
        sleep=TASK_POLL):
    """
    Description: Waits until all tasks in data-center are finished
    Parameters:
        * vdc - ip or hostname of rhevm
        * vdc_password - root password for rhevm machine
        * datacenter - name of the datacenter that has running tasks
        * db_name - name of the rhevm database
        * db_user - name of the user of database
        * timeout - max seconds to wait
        * sleep - polling interval
    """
    dc_util = get_api('data_center', 'datacenters')
    sp_id = dc_util.find(datacenter).id
    sampler = TimeoutingSampler(
        timeout, sleep, get_running_tasks, vdc, vdc_password, sp_id, db_name,
        db_user)
    for tasks in sampler:
        if not tasks:
            logger.info("All tasks are gone")
            return


def getAllImages(vds, vds_username, vds_password, spool_id, domain_id,
                 object_id):
    """
    Description: Searches for volumes and images on storage domain
    Parameters:
        * vds - host that has mounted storage domain below
        * vds_username - username of root on vds
        * vds_password - password for root account on vds
        * spool_id - storage pool ID containing storage domain below
        * domain_id - storage domain ID that has template or vm on it
        * object_id - id of template/vm
    Author: jlibosva
    Return: List of images id
    """
    path_to_ovf = '/rhev/data-center/%s/%s/master/vms/%s/%s.ovf' % \
                  (spool_id, domain_id, object_id, object_id)

    logger.debug("Checking file %s on host %s", path_to_ovf, vds)

    namespace_dict = {
        'ovf' : "http://schemas.dmtf.org/ovf/envelope/1/",
        'xsi' : "http://www.w3.org/2001/XMLSchema-instance"
    }

    host = Machine(vds, vds_username, vds_password).util(LINUX)
    with host.ssh as ssession:
        ovf_hnd = ssession.getFileHandler().open(path_to_ovf)
        root_elem = etree.parse(ovf_hnd).getroot()
        ovf_hnd.close()

    disks_elements = root_elem.xpath(
                        'Section[@xsi:type="ovf:DiskSection_Type"]/Disk',
                        namespaces=namespace_dict)

    attrib = '{' + namespace_dict['ovf'] + '}fileRef'
    return [disk.attrib[attrib].split('/', 1)[0] for disk in disks_elements]

@is_action()
def checkSpoofingFilterRuleByVer(host, user, passwd, target_version='3.2'):
    '''
    Description: Check if NetworkFilter (nwfilter) rule is enabled/disabled for a requested
    version
    Author: myakove
    Parameters:
      * host - name of the rhevm
      * user - user name for the rhevm
      * passwd - password for the user
      * target_version - the lower veriosn that nwfilter is enabled
    Return True for version >= 3.2 and False for <=3.1
     '''

    host_obj = Machine(host,user,passwd).util(LINUX)
    cmd = ['engine-config', '-g', 'EnableMACAntiSpoofingFilterRules']
    rc, output = host_obj.runCmd(cmd)
    ERR_MSG = 'Version {0} has incorrect nwfilter value: {1}'

    logger.info(output)
    for line in output.splitlines():
        data = line.split()
        version = data[3]
        status = data[1].lower()
        ver_status = version >= target_version
        test_status = status == str(ver_status).lower()
        if not test_status:
            logger.error(ERR_MSG.format(version, status))
            return False
    return True


@is_action()
def setNetworkFilterStatus(enable, host, user, passwd, version):
    '''
    Description: Disabling or enabling network filtering.
    Author: awinter
    Parameters:
      * enable - True for enabling, False for disabling
      * host - name of the rhevm
      * user - user name for the rhevm
      * passwd - password for the user
      * version - Data center's version
    return: True if network filtering is disabled, False otherwise
    '''
    cmd = ["rhevm-config", "-s", "EnableMACAntiSpoofingFilterRules=%s" \
           % enable.lower(), "--cver=%s" % version]

    host_obj = Machine(host,user,passwd).util(LINUX)
    if not host_obj.runCmd(cmd)[0]:
        logger.error("Operation failed")
        return False
    return restartOvirtEngine(host_obj, 5, 25, 70)


@is_action()
def restartOvirtEngine(host_obj, interval, attempts, timeout,
                       engine_service=ENGINE_SERVICE,
                       health_url=ENGINE_HEALTH_URL):
    '''
    Description: Restarting Ovirt engine
    Author: awinter
    Parameters:
      * host_obj - host object
      * interval - Checking in "interval" time, sampling every "interval"
                   seconds
      * attempts - number of attempts to check that ovirt is UP
      * timeout - the amount of time to sleep after HealthPage is UP
    return: True if Ovirt engine was successfully restarted, False otherwise
    '''
    if not host_obj.restartService(engine_service):
        logger.error("restarting %s failed", engine_service)
        return False

    for attempt in range(1, attempts):
        sleep(int(interval))
        if host_obj.runCmd(["curl", health_url])[1].count("Welcome") == 1:
            sleep(int(timeout))
            logger.info("HealthPage is UP")
            return True
    logger.error("HealthPage was not up after %s attempts", attempts)
    return False


@is_action()
def configureTempStaticIp(host, user, password, ip, nic='eth1',
                          netmask='255.255.255.0'):
    '''
    Configure static IP on specific interface
    Author: gcheresh
    Parameters:
       * host - remote machine ip address or fqdn
       * user - user name for the machine
       * password - password for root user
       * nic - specific NIC to configure ip/netmask on
       * ip - IP to configure on NIC
       * netmask - Netmask to configure on NIC
    Return: (True if command executed successfuly, False otherwise)
    '''
    machine_obj = Machine(host, user, password).util(LINUX)
    cmd = ["ifconfig", nic, ip, "netmask", netmask]
    rc, output = machine_obj.runCmd(cmd)
    if not rc:
        logger.error("Failed to configure ip '%s' on machine '%s' and nic"
                     "'%s'", ip, host, nic)
        logger.error(output)
        return False
    return True


def buildListFilesMtu(physical_layer=True, network=None, nic=None,
                      vlan=None, bond=None, bond_nic1='eth3',
                      bond_nic2='eth2', bridged=True):
    '''
    Builds a list of file names to check MTU value
    Author: gcheresh
    Parameters:
    * network - network name to build ifcfg-network name
    * physical_layer - flag to create file names for physical or logical layer
    * nic - nic name to build ifcfg-nic name
    * vlan - vlan name to build ifcfg-* files names for
    * bond - bond name to create ifcfg-* files names for
    * bond_nic1 - name of the first nic of the bond
    * bond_nic2 - name of the second nic of the bond
    * bridged - flag, to differentiate bridged and non_bridged network
    Return: 2 lists of ifcfg files names
    '''
    ifcfg_script_list = []
    sys_class_net_list = []
    temp_name_list = []
    if not physical_layer:
        if bridged:
            temp_name_list.append('%s' % network)
        if vlan and bond:
            temp_name_list.append('%s.%s' % (bond, vlan))
        if vlan and not bond:
            temp_name_list.append('%s.%s' % (nic, vlan))
    else:
        if bond:
            for if_name in [bond_nic1, bond_nic2, bond]:
                temp_name_list.append('%s' % if_name)
        elif vlan or nic:
            temp_name_list.append('%s' % nic)
    for script_name in temp_name_list:
        ifcfg_script_list.append(os.path.join(IFCFG_NETWORK_SCRIPTS_DIR,
                                              'ifcfg-%s' % script_name))
        sys_class_net_list.append(os.path.join(SYS_CLASS_NET_DIR,
                                               script_name, 'mtu'))
    return ifcfg_script_list, sys_class_net_list


@is_action()
def checkMTU(host, user, password, mtu, physical_layer=True, network=None,
             nic=None, vlan=None, bond=None, bond_nic1='eth3',
             bond_nic2='eth2', bridged=True):
    '''
        Check MTU for all files provided from buildListFilesMtu function
        Uses helper testMTUInScriptList function to do it
        Author: gcheresh
        Parameters:
        * host - remote machine ip address or fqdn
        * user - root user on the machine
        * password - password for root user
        * mtu - the value to test against
        * network - the network name to test the MTU value
        * physical_layer - flag to test MTU for physical or logical layer
        * nic - interface name to test the MTU value for
        * vlan - vlan number to test the MTU value for nic.vlan
        * bond - bond name to test the MTU value for
        * bond_nic1 - name of the first nic of the bond
        * bond_nic2 - name of the second nic of the bond
        * bridged - flag, to differentiate bridged and non_bridged network
        Return: True value if MTU in script files is correct
    '''
    ifcfg_script_list, sys_class_net_list = buildListFilesMtu(physical_layer,
                                                              network, nic,
                                                              vlan, bond,
                                                              bond_nic1,
                                                              bond_nic2,
                                                              bridged)
    if not ifcfg_script_list or not sys_class_net_list:
        if not physical_layer and not bridged and not vlan:
            return True
        else:
            logger.error("The file with MTU parameter is empty")
            return False
    return testMTUInScriptList(host, user, password, ifcfg_script_list, mtu,
                               1) and testMTUInScriptList(host, user, password,
                                                          sys_class_net_list,
                                                          mtu)


def testMTUInScriptList(host, user, password, script_list, mtu,
                        flag_for_ifcfg=0):
    '''
        Helper function for checkMTU to test specific list of files
        Author: gcheresh
        Parameters:
        * host - remote machine ip address or fqdn
        * user - root user on the machine
        * password - password for root user
        * script_list - list with names of files to test MTU in
        * mtu - the value to test against
        * flag_for_ifcfg - flag if this file is ifcfg or not
        Return: True value if MTU in script list is correct
    '''
    ERR_MSG = '"MTU in {0} is {1} when the expected is {2}"'
    machine_obj = Machine(host, user, password).util(LINUX)
    for script_name in script_list:
        rc, output = machine_obj.runCmd(['cat', script_name])
        if not rc:
            logger.error("Can't read {0}".format(script_name))
            return False
        if flag_for_ifcfg:
            match_obj = re.search('MTU=([0-9]+)', output)
            if match_obj:
                mtu_script = int(match_obj.group(1))
            else:
                mtu_script = MTU_DEFAULT_VALUE
            if mtu_script != mtu:
                logger.error(ERR_MSG.format(script_name, mtu_script, mtu))
                return False
        else:
            if int(output) != mtu:
                logger.error(ERR_MSG.format(script_name, output, mtu))
                return False
    return True


@is_action()
def configureTempMTU(host, user, password, mtu, nic='eth1'):
    '''
    Configure static IP on specific interface
    Author: gcheresh
    Parameters:
       * host - remote machine ip address or fqdn
       * user - user name for the machine
       * password - password for root user
       * mtu - MTU value we want to configure on machine
       * nic - specific NIC to configure mtu on
    Return: (True if command executed successfuly, False otherwise)
    '''
    machine_obj = Machine(host, user, password).util(LINUX)
    cmd = ["ifconfig", nic, "mtu", mtu]
    rc, output = machine_obj.runCmd(cmd)
    if not rc:
        logger.error("Failed to configure mtu '%s' on machine '%s'",
                     mtu, host)
        logger.error(output)
        return False
    return True


@is_action()
def sendICMP(host, user, password, ip='', count=5, packet_size=None):
    '''
    Send or stop sending ICMP traffic from host to given ip
    **Author**: gcheresh
        **Parameters**:
        *  *host* - machine ip address or fqdn of the source machine
        *  *user* - root user on the source machine
        *  *password* - password for the source root user
        *  *ip* - ip of the remote machine where we send ICMP traffic to
        *  *count* - number of packets to send
        *  *packet_size* - testing for MTU different than default
    **Return**: True value if the function execution succeeded
    '''
    machine_obj = Machine(host, user, password).util(LINUX)
    if packet_size:
        logger.info("Sending ping with -M do parameter")
        cmd = ["ping", "-s", str(packet_size), "-M", "do", ip,
               "-c", str(count)]
        logger.info(cmd)
    else:
        logger.info("Sending ping command with count number of packets")
        cmd = ["ping", ip, "-c", str(count)]
        logger.info(cmd)
    rc, output = machine_obj.runCmd(cmd)
    if not rc:
        logger.error('Failed to start sending ICMP traffic: %s', output)
        return False
    return True


def runTcpDumpCmd(machine, user, password, nic, **kwargs):
    '''
    Desciption: Runs tcpdump on the given machine and returns its output.
    **Author**: tgeft
        **Parameters**:
        *  *machine* - machine ip address or fqdn
        *  *user* - root user on the machine
        *  *password* - password for the root user
        *  *nic* - interface on which traffic will be monitored
        *  *src* - source IP by which to filter packets
        *  *dst* - destination IP by which to filter packets
        *  *srcPort* - source port by which to filter packets, should be
                       numeric (e.g. 80 instead of 'HTTP')
        *  *dstPort* - destination port by which to filter packets, should
                       be numeric like 'srcPort'
        *  *protocol* - protocol by which traffic will be received
        *  *numPackets* - number of packets to be received (10 by default)
    **Return**: Returns tcpdump's output and return code.
    '''
    paramPrefix = {'src': 'src', 'srcPort': 'src port', 'dst': 'dst',
                   'dstPort': 'dst port', 'protocol': ''}

    cmd = ['tcpdump', '-i', nic, '-c', str(kwargs.pop('numPackets', '10')),
           '-nn']

    if kwargs:
        for k, v in kwargs.iteritems():
            cmd.extend([paramPrefix[k], str(v), 'and'])

        cmd.pop()  # Removes unneccesary 'and'

    logger.info('TcpDump command to be sent: %s', cmd)

    machineObj = Machine(machine, user, password).util('linux')
    rc, output = machineObj.runCmd(cmd)

    logger.debug('TcpDump output: ' + output)

    if not rc:
        if 'timeout' in output:
            logger.info('Tcpdump timed out (no packets passed the filter).')
            rc = True  # Getting a timeout is considered to be a successful run
        else:
            logger.error('Failed to run tcpdump command. Output: %s', output)

    return rc, output


def checkTraffic(machine, user, password, nic, src, dst, **kwargs):
    '''
    Desciption: Runs tcpdump on the given machine and verifies its output to
                check if traffic was received according to the parameters.
    **Author**: tgeft
        **Parameters**:
        *  *machine* - machine ip address or fqdn
        *  *user* - root user on the machine
        *  *password* - password for the root user
        *  *nic* - interface on which traffic will be monitored
        *  *src* - source IP by which to filter packets
        *  *dst* - destination IP by which to filter packets
        *  *srcPort* - source port by which to filter packets, should be
                       numeric (e.g. 80 instead of 'HTTP')
        *  *dstPort* - destination port by which to filter packets, should
                       be numeric like 'srcPort'
        *  *protocol* - protocol by which traffic will be received
        *  *numPackets* - number of packets to be received (10 by default)
    **Return**: Returns True if traffic according to the parameters was
                received, False otherwise.
    '''
    rc, tcpDumpOutput = runTcpDumpCmd(machine, user, password, nic,
                                      src=src, dst=dst, **kwargs)

    if not rc:
        raise Exception('Can\'t analyze traffic as running tcpdump failed.')

    pattern = '(.*)'.join([src, str(kwargs.get('srcPort', '')), dst,
                           str(kwargs.get('dstPort', ''))])

    logger.info('Checking TcpDump output. RE Pattern: ' + pattern)

    '''
    If the protocol is ICMP, we check that 'ICMP' shows up in the output. For
    other protocols, the protocol name is displayed on a different line from
    the source and destination IP's, so the check is not done for them.
    '''
    for line in tcpDumpOutput.splitlines():
        if re.search(pattern, line) and ('ICMP' in line.upper() or
                                         kwargs.get('protocol', '') != 'icmp'):
            logger.info('Found match in tcpdump output in the following '
                        'line: ' + line)
            return True

    logger.warning('The traffic that was searched for was not found in tcpdump'
                   ' output')
    return False


def waitUntilGone(positive, names, api, timeout, samplingPeriod):
    '''
    Wait for objects to disappear from the setup. This function will block up
    to `timeout` seconds, sampling the given API every `samplingPeriod`
    seconds, until no object specified by names in `names` exists.

    Parameters:
        * names - comma (and no space) separated string of names
        * timeout - Time in seconds for the objects to disappear
        * samplingPeriod - Time in seconds for sampling the objects list
        * api - API to query (get with get_api(ELEMENT, COLLECTION))
    '''
    query = ' or '.join(['name="%s"' % templ for templ in split(names)])
    sampler = TimeoutingSampler(timeout, samplingPeriod, api.query, query)

    sampler.timeout_exc_args = "Objects didn't disappear in %d secs" % timeout,

    for sample in sampler:
        if not sample:
            logger.info("All %s are gone.", names)
            return positive


def raise_if_exception(results):
    """
    Description: Raises exception if any of Future object in results has
    exception
    Parameters:
        * results - list of Future objects
    """
    for result in results:
        if result.exception():
            logger.error(result.exception())
            raise result.exception()


def process_collection_parallel(collection, func, func_args, max_workers,
                                exc=Exception, need_result=False):
    """
    Description: Calls func for each item in collection in parallel
    Parameters:
        * collection - collection to process
        * func - function that processes items
        * func_args - arguments for function
        * exc - exception to raise
        * max_workers - how many threads in parallel will run
        * need_result - if this is True, every result of called function is
                        checked and if the result is False, exception is raised
    """
    results = list()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for item in collection:
            results.append(executor.submit(func, item, *func_args))
    for index, result in enumerate(results):
        if result.exception():
            logger.error(result.exception())
            raise result.exception()
        if need_result and not result.result():
            raise exc("Result %d from parallel process failed" % index)
