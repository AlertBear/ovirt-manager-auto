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
import threading
import logging
import os
import re
import shutil
import time

import art.test_handler.settings as settings
from art.core_api.apis_exceptions import (
    EntityNotFound,
    TestCaseError,
)
from art.core_api.apis_utils import TimeoutingSampler
from art.core_api.validator import compareCollectionSize
from art.rhevm_api.resources import Host, RootUser
from utilities.machine import Machine, LINUX
from utilities.rhevm_tools.base import Setup
from utilities.utils import (
    convertMacToIp,
    createDirTree,
)
import art.core_api.apis_exceptions as exceptions

logger = logging.getLogger('test_utils')

# The name of section in the element configuration file
elementConfSection = 'elements'

SYS_CLASS_NET_DIR = '/sys/class/net'
TASK_TIMEOUT = 300
TASK_POLL = 5
ENGINE_HEALTH_URL = "http://localhost/OvirtEngineWeb/HealthStatus"
ENGINE_SERVICE = "ovirt-engine"
SUPERVDSMD = "supervdsmd"
VDSMD = "vdsmd"

RESTART_INTERVAL = 5
RESTART_TIMEOUT = 70

RHEVM_UTILS_ENUMS = settings.ART_CONFIG['elements_conf']['RHEVM Utilities']


class GetApi(object):

    _util_cache = {}
    rlock = threading.RLock()

    def __init__(self, element, collection):
        self._element = element
        self._collection = collection

    # setter is not needed since _util_cache.__setitem__ is doing all the job
    @property
    def util_cache(self):
        return self.__class__._util_cache

    def update_util_cache(self, key, value):
        with self.rlock:
            self.util_cache[key] = value

    @classmethod
    def clear_util_cache(cls):
        with cls.rlock:
            cls._util_cache.clear()

    @classmethod
    def logoff_api(cls):
        with cls.rlock:
            for api in set([api.__class__ for api in
                            cls._util_cache.values()]):
                api.logout()
            # cleaning all apis since we doing the setup and teardown by
            # rest so it will be good to do logoff by api just with scenarios
            # which all the steps in the test otherwise if login in setup or
            # teardown the logoff will be from rest
            cls.clear_util_cache()

    def __getattr__(self, opcode):
        with self.rlock:
            engine = settings.ART_CONFIG.get('RUN').get('engine')
            key = (self._element, self._collection, engine)
            # checking in cache
            if key in self.util_cache:
                api = self.util_cache[key]
            else:
                if engine == 'rest':
                    from art.core_api.rest_utils import RestUtil
                    api = RestUtil(self._element, self._collection)
                elif engine == 'sdk':
                    from art.core_api.ovirtsdk_utils import SdkUtil
                    api = SdkUtil(self._element, self._collection)
                elif engine == 'cli':
                    from art.core_api.ovirtcli_utils import CliUtil
                    api = CliUtil(self._element, self._collection)
                elif engine == 'java':
                    from art.core_api.ovirtsdk_java_utils import JavaSdkUtil
                    api = JavaSdkUtil(self._element, self._collection)
                # adding to cache
                self.update_util_cache(key, api)
            return getattr(api, opcode)


get_api = GetApi


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
    """
    Get statistic data from given element

    Args:
        name (str): Object name
        elm_name (str): Element name
        collection_name: Collection name
        stat_types: Statistics types(for example memory.used)

    Returns:
        dict: Statistic data
    """
    util = get_api(elm_name, collection_name)
    elm_obj = util.find(name)
    statistics = util.getElemFromLink(
        elm_obj, link_name='statistics', attr='statistic'
    )
    values = {}
    for stat in statistics:
        if stat.get_name() in stat_types:
            datum = stat.get_values().get_value()[0].get_datum()
            values[stat.get_name()] = float(datum)
    return values


def validateElementStatus(positive, element, collection, elementName,
                          expectedStatus, dcName=None):
    '''
    The function validateElementStatus compare the status of given element with
    expected status.
        element = specific element (host,datacenter...)
        elementName = the name of element (<host name> in case of given element
                      is a host)
        expectedStatus = expected status(es) of element (The status of element
                        that we are expecting)
        dcName = the name of Data Center (to retrieve the status of storage
                 domain entity, None by default)
    return values : Boolean value (True/False ) True in case of success
                    otherwise False
    '''
    attribute = "state"
    util = get_api(element, collection)

    try:
        supportedElements = (
            settings.ART_CONFIG['elements_conf'][elementConfSection]
        )
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

        try:  # Fetch Data Center object in order to get storage domain status
            dcUtil = get_api('data_center', 'datacenters')
            dcObj = dcUtil.find(dcName)
        except EntityNotFound:
            ERR = (
                "Data Center object is needed in order to get storage domain "
                "status"
            )
            util.logger.warning(MSG.format(dcName, "datacenter", ERR))
            return False

        elementObj = util.getElemFromElemColl(
            dcObj, elementName, 'storagedomains', 'storage_domain',
        )
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

    expectedStatuses = [
        status.strip().upper() for status in expectedStatus.split(',')
        ]
    result = elementObj.get_status().upper() in expectedStatuses

    if not result:
        MSG = "Status of element {0} is \'{1}\' expected statuses are {2}"
        util.logger.warning(
            MSG.format(
                elementName, elementObj.get_status().upper(), expectedStatuses
            )
        )

    return result


def startVdsmd(vds, password):
    '''
    Start vdsmd on the given host
    Author: jvorcak
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Host(vds)
    machine.users.append(RootUser(password))
    return machine.service(VDSMD).start()


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
    machine = Host(vds)
    machine.users.append(RootUser(password))
    if supervdsm:
        if not machine.service(SUPERVDSMD).stop():
            logger.error("Stop supervdsm service failed")
            return False

    return machine.service(VDSMD).restart()


def stopVdsmd(vds, password):
    '''
    Stop vdsmd on the given host
    Author: jvorcak
    Parameters:
       * vds - name of the host
       * password - ssh password for the host
    '''
    machine = Host(vds)
    machine.users.append(RootUser(password))
    return machine.service(VDSMD).stop()


def update_vm_status_in_database(vm_name, status, vdc, vdc_pass,
                                 psql_username=RHEVM_UTILS_ENUMS[
                                     'RHEVM_DB_USER'],
                                 psql_db=RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
                                 psql_password=RHEVM_UTILS_ENUMS[
                                     'RHEVM_DB_PASSWORD']):
    """
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
    Return: (True if sql command has been executed successfully,
             False otherwise)
    """
    util = get_api('vm', 'vms')
    vm = util.find(vm_name)
    setup = Setup(vdc, 'root', vdc_pass,
                  dbuser=psql_username,
                  dbpassw=psql_password)
    query = ("UPDATE vm_dynamic SET status=%d WHERE vm_guid=\'%s\';"
             % (status, vm.get_id()))
    return setup.psql(query, psql_db=psql_db)


def cleanupData(path):
    if path and os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    return True


def prepareDataForVm(root_dir='/tmp', root_name_prefix='', dir_cnt=1,
                     file_cnt=1):
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
        data_path = createDirTree(
            root_dir=root_dir, name_prefix=root_name_prefix,
            dir_cnt=int(dir_cnt), file_cnt=int(file_cnt),
        )
    except Exception as err:
        logger.error('failed to prepare data for VM: %s', err)
        rc = False
    return rc, {'data_path': data_path}


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


def convertOsNameToOsTypeElement(positive, osName):
    '''
    function convert Os Name from ATOM to OS Type Element compatible with
    Rest-Api
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


def isVdsmdRunning(host, user, password):
    """
    Check if vdsmd is running on host.
    """
    return isServiceRunning(True, host, user, password, VDSMD)


def convertMacToIpAddress(positive, mac, subnetClassB='10.35', vlan=0):
    """Wrapper for convertMacToIp"""
    ip = convertMacToIp(mac, subnetClassB, vlan)
    logger.info('MAC: %s with VLAN: %s converted to IP: %s', mac, vlan, ip)
    if ip:
        return True, {'ip': ip}
    return False, {'ip': None}


def searchElement(positive, element, collection, keyName, searchValue):
    '''
    The function searchElement search specific element by key name and value.
        element = specific element (host,datacenter...)
        keyName = the key name (element name or element status ...)
        searchValue = the value what we want
        find(Example: key name = ip,search value = 1.1.1.1)
    return values : True and list of elements or False and None
    '''
    util = get_api(element, collection)
    try:
        supportedElements = (
            settings.ART_CONFIG['elements_conf'][elementConfSection]
        )
    except Exception as err:
        util.logger.error(err)
        return False, None
    if element not in supportedElements:
        util.logger.error(
            "Unknown element %s , supported elements: %s",
            element, ",".join(supportedElements.keys()),
        )
        return False, None

    elements = util.query(keyName + "=" + searchValue)
    if elements:
        return True, elements

    return False, None


def removeDirOnHost(
    positive, ip, dirname, user='root', password='qum5net', osType=LINUX,
):
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
    if machine is None:
        return False
    if osType == LINUX:
        return machine.removeFile(dirname)
    elif osType == 'windows':
        return machine.removeDir(dirname)


def searchForObj(
    util, query_key, query_val, key_name, max=None, case_sensitive=True,
    expected_count=None
):
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
        objs = util.get(abs_link=False)

        pattern = query_val

        if not case_sensitive:
            pattern = "(?i)%s" % pattern

        if re.match(r'(.*)\*$', query_val):
            pattern = r'^%s' % pattern

        logger.warning("searchForObj: pattern='%s'", pattern)

        for obj in objs:
            objProperty = getattr(obj, key_name)
            if objProperty is None:
                msg = (
                    "searchForObj: '{0}.{1}' returns '{2}', "
                    "It can happen if you are passing wrong property '{1}' to"
                    " '{0}' or it is a bug in product".format(
                        obj, key_name, objProperty,
                    )
                )
                raise TestCaseError(msg)

            if re.match(pattern, objProperty):
                expected_count += 1

        if max > 0:
            expected_count = min(expected_count, max)

    contsraint = "{0}={1}".format(query_key, query_val)
    query_objs = util.query(
        contsraint, max=max, case_sensitive=str(case_sensitive).lower(),
    )
    status = compareCollectionSize(query_objs, expected_count, util.logger)

    return status


def setPersistentNetwork(host, password):
    """
    Ensure that Network configurations are persistent

    __author__: 'atal'

    :param host: Remove machine IP address or FQDN
    :type host: str
    :param password: Password for the root user
    :type password: str
    :return: True if the set persistent network command executed successfully,
        False otherwise
    :rtype: bool
    """
    logger.info("Set persistent network")
    vm_obj = Host(host)
    vm_obj.users.append(RootUser(password))

    # Files
    persistent_rule = '/etc/udev/rules.d/70-persistent-net.rules'
    net_scripts_dir = '/etc/sysconfig/network-scripts'
    network_configuration = '/etc/sysconfig/network'

    if not vm_obj.fs.unlink(persistent_rule):
        logger.error('Failed to erase %s', persistent_rule)
        return False
    logger.debug(
        "Does persistent udev rules exist? : %s",
        vm_obj.fs.exists(persistent_rule),
    )

    ifcfg_files = [
        i for i in vm_obj.fs.listdir(net_scripts_dir)
        if 'ifcfg-' in i and '-lo' not in i
    ]

    if not ifcfg_files:
        logger.error('PCI network interfaces do not exist on %s', host)
        return False

    remove_ifcfg_attrs_cmd = [
        'sed', '-i', '-e', '/HWADDR/d', '-e', '/HOSTNAME/d',
        '-e', '/DHCP_HOSTNAME/d', '-e', '/UUID/d',
    ]  # Missing target file, adding it in loop bellow
    with vm_obj.executor().session() as ss:
        for ifcfg in ifcfg_files:
            ifcfg_path = os.path.join(net_scripts_dir, ifcfg)
            if vm_obj.fs.isfile(ifcfg_path):
                cmd = remove_ifcfg_attrs_cmd + [ifcfg_path]

                rc, out, err = ss.run_cmd(cmd)
                if rc:
                    logger.error(
                        "Failed to remove relevant attrs from %s: %s, %s",
                        ifcfg_path, out, err,
                    )
                    return False

                with ss.open_file(ifcfg_path) as fd:
                    logger.debug(
                        '%s Final configurations: \n%s',
                        ifcfg, fd.read()
                    )

    vm_obj.network.hostname = "localhost.localdomain"

    # TODO: This is not relevant for el7, but I don't want to remove it
    with vm_obj.executor().session() as ss:
        with ss.open_file(network_configuration) as fd:
            logger.debug('Final network configurations: \n%s', fd.read())

    # Flush FS buffers
    vm_obj.executor().run_cmd(['sync'])
    return True


def get_running_tasks(engine, sp_id):
    """
    Gets taks_id for all tasks running in rhevm

    Args:
        engine - instance of resources.Engine
        sp_id - storage pool id

    Returns:
        list of running tasks
    """
    query = (
        "select task_id, action_type, status, vdsm_task_id from "
        "async_tasks where storage_pool_id = '%s'" % sp_id
    )
    tasks = engine.db.psql(query)
    logger.debug("Query %s returned list: %s", query, tasks)
    return tasks


def wait_for_tasks(engine, datacenter, timeout=TASK_TIMEOUT, sleep=TASK_POLL):
    """
    Waits until all tasks in data-center are finished

    Args:
        engine - instance of resources.Engine
        datacenter - name of the datacenter that has running tasks
        timeout - max seconds to wait
        sleep - polling interval

    Returns:
        None when success

    Raises:
        APITimeout in case of timeout is reached
    """
    dc_util = get_api('data_center', 'datacenters')
    sp_id = dc_util.find(datacenter).id
    try:
        sampler = TimeoutingSampler(
            timeout, sleep, get_running_tasks, engine, sp_id,
        )
        for tasks in sampler:
            if not tasks:
                logger.info("All tasks are gone")
                return
    except exceptions.APITimeout:
        logger.error("APITimeout failure")
    finally:
        tasks = get_running_tasks(engine, sp_id)
        logger.info("Tasks %s are still running", tasks)


def restart_engine(engine, interval, timeout):
    """
    Function restart engine and waits for Health Status.

    :param engine: engine object
    :type engine: instance of resources.Engine
    :param interval: sampling interval
    :type interval: int
    :param timeout: limit to wait
    :type timeout: int
    :raises: APITimeout in case timeout exceed
    """
    engine.restart()
    for status in TimeoutingSampler(
        timeout, interval, lambda: engine.health_page_status
    ):
        if status:
            break


def waitUntilGone(positive, names, api, timeout,
                  samplingPeriod, search_by='name'):
    '''
    Wait for objects to disappear from the setup. This function will block up
    to `timeout` seconds, sampling the given API every `samplingPeriod`
    seconds, until no object specified by names in `names` exists.

    Parameters:
        * names - comma (and no space) separated string or list of names
        * timeout - Time in seconds for the objects to disappear
        * samplingPeriod - Time in seconds for sampling the objects list
        * api - API to query (get with get_api(ELEMENT, COLLECTION))
    '''
    if isinstance(names, basestring):
        objlist = split(names)
    else:
        objlist = names
    query = ' or '.join(['%s="%s"' % (search_by, templ) for templ in objlist])
    sampler = TimeoutingSampler(timeout, samplingPeriod, api.query, query)

    sampler.timeout_exc_args = "Objects didn't disappear in %d secs" % timeout,

    for sample in sampler:
        if not sample:
            logger.info("All %s are gone.", names)
            return positive
