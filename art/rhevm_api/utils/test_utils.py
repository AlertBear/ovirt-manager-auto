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

from contextlib import contextmanager
import logging
from lxml import etree
import random
import re
import time
import os
import shutil
from socket import gethostname

from art.test_handler.exceptions import QueryNotFoundException
import art.test_handler.settings as settings
from utilities.rhevm_tools.base import Setup
from art.core_api.validator import compareCollectionSize
from art.core_api.apis_utils import TimeoutingSampler
from utilities.utils import (
    convertMacToIp,
    pingToVms,
    createDirTree,
)
from utilities.machine import Machine, eServiceAction, LINUX
from art.core_api.apis_exceptions import (
    APITimeout,
    EntityNotFound,
    TestCaseError,
)
from utilities.tools import (
    GuestToolsMachine,
)
from art.rhevm_api.resources import Host, RootUser

logger = logging.getLogger('test_utils')

# The name of section in the element configuration file
elementConfSection = 'elements'

IFCFG_NETWORK_SCRIPTS_DIR = '/etc/sysconfig/network-scripts'
SYS_CLASS_NET_DIR = '/sys/class/net'
MTU_DEFAULT_VALUE = 1500
TASK_TIMEOUT = 300
TASK_POLL = 5
ENGINE_HEALTH_URL = "http://localhost/OvirtEngineWeb/HealthStatus"
ENGINE_SERVICE = "ovirt-engine"
SUPERVDSMD = "supervdsmd"
VDSMD = "vdsmd"
TCDUMP_TIMEOUT = "60"
RESTART_INTERVAL = 5
RESTART_TIMEOUT = 70

RHEVM_UTILS_ENUMS = settings.opts['elements_conf']['RHEVM Utilities']


class PSQLException(Exception):
    pass


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
            engine = settings.opts.get('engine')
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
    machine = Machine(vds, 'root', password).util(LINUX)
    return machine.startService('vdsmd')


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
        supportedElements = settings.opts['elements_conf'][elementConfSection]
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


def checkHostConnectivity(positive, ip, user, password, osType, attempt=1,
                          interval=1, remoteAgent=None):
    '''
    wrapper function check if windows server up and running
    indication to server up and running if wmi query return SystemArchitecture
    and elapsed time
    '''
    try:
        t1 = time.time()
        logger.debug("Checking %s %s host connectivity", ip, osType)
        machine = Machine(ip, user, password).util(osType)
        if remoteAgent == 'staf':
            status = machine.isConnective(attempt, interval, remoteAgent)
        else:
            status = machine.isConnective(attempt, interval, True)
        t2 = time.time()
        logger.info(
            'Host: %s, Connectivity Status: %s, Elapsed Time: %d', ip, status,
            int(t2 - t1),
        )
        return status, {'elapsedTime': int(t2 - t1)}
    except Exception as err:
        logger.error(str(err))
        return False, {'elapsedTime': -1}


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
        objs = util.get(absLink=False)

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


def runSQLQueryOnSetup(vdc, vdc_pass, query,
                       psql_username='postgres', psql_db='engine'):
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
    setup = Setup(vdc, 'root', vdc_pass, dbuser=psql_username)
    return setup.psql(query, psql_db=psql_db)


def get_running_tasks(vdc, vdc_pass, sp_id, db_name, db_user):
    """
    Description: Gets taks_id for all tasks running in rhevm
    Parameters:
        * vdc - ip or hostname of rhevm
        * vdc_pass - root password for rhevm machine
        * sp_id - storage pool id
        * db_name - name of the rhevm database
        * db_user - name of the user of database
    """
    query = "select task_id, action_type, status, vdsm_task_id from " \
            "async_tasks where storage_pool_id = '%s'" % sp_id
    tasks = runSQLQueryOnSetup(vdc, vdc_pass, query, db_user, db_name)
    logger.debug("Query %s returned list: %s", query, tasks)
    return tasks


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


def wait_for_vds_tasks(vds_resource):
    """
    Wait for VDS tasks (vdsClient -s 0 getAllTasks)

    Args:
        vds_resource (VDS): VDS resource
    """
    sampler = TimeoutingSampler(
        TASK_TIMEOUT, TASK_POLL, vds_resource.vds_client, "getAllTasks"
    )
    for tasks in sampler:
        task = tasks["tasks"]
        if not task:
            logger.info("All VDSM tasks are gone")
            return
        logger.info(task)


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


def configure_temp_static_ip(
    vds_resource, ip, nic="eth1", netmask="255.255.255.0"
):
    """
    Configure temporary static IP on specific interface

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param ip: temporary IP to configure on NIC
    :type ip: string
    :param nic: specific NIC to configure ip/netmask on
    :type nic: string
    :param netmask: netmask to configure on NIC (full or CIDR)
    :type netmask: string
    :return: True if command executed successfully, False otherwise
    :rtype: bool
    """
    cmd = ["ip", "address", "add", "%s/%s" % (ip, netmask), "dev", nic]
    rc, _, _ = vds_resource.run_command(cmd)
    if rc:
        return False
    return True


def build_list_files_mtu(
    physical_layer=True, network=None, nic=None, vlan=None, bond=None,
    bond_nic1='eth3', bond_nic2='eth2', bridged=True
):
    """
    Builds a list of file names to check MTU value

    :param network: network name to build ifcfg-network name
    :type network: str
    :param physical_layer: flag to create file names for physical or logical
    layer
    :type physical_layer: bool
    :param nic: nic name to build ifcfg-nic name
    :type nic: str
    :param vlan: vlan name to build ifcfg-* files names for
    :type vlan: str
    :param bond: bond name to create ifcfg-* files names for
    :type bond: str
    :param bond_nic1: name of the first nic of the bond
    :type bond_nic1: str
    :param bond_nic2: name of the second nic of the bond
    :type bond_nic2: str
    :param bridged: flag, to differentiate bridged and non_bridged network
    :type bridged: bool
    :return: 2 lists of ifcfg files names
    :rtype: tuple
    """
    ifcfg_script_list = []
    sys_class_net_list = []
    temp_name_list = []
    if not physical_layer:
        if bridged:
            temp_name_list.append("%s" % network)
        if vlan and bond:
            temp_name_list.append("%s.%s" % (bond, vlan))
        if vlan and not bond:
            temp_name_list.append("%s.%s" % (nic, vlan))
    else:
        if bond:
            for if_name in [bond_nic1, bond_nic2, bond]:
                temp_name_list.append("%s" % if_name)

        elif vlan or nic:
            temp_name_list.append("%s" % nic)

    for script_name in temp_name_list:
        ifcfg_script_list.append(os.path.join(
            IFCFG_NETWORK_SCRIPTS_DIR, "ifcfg-%s" % script_name)
        )
        sys_class_net_list.append(os.path.join(
            SYS_CLASS_NET_DIR, script_name, "mtu")
        )
    return ifcfg_script_list, sys_class_net_list


def check_configured_mtu(vds_resource, mtu, inter_or_net):
    """
    Checks if the configured MTU on an interface or network match
    provided MTU using ip command

    Args:
        vds_resource (VDS): VDS resource
        mtu (str): expected MTU for the network/interface
        inter_or_net (str): interface name or network name

    Returns:
        bool: True if MTU on host is equal to "mtu", False otherwise.
    """
    logger.info(
        "Checking if %s is configured correctly with MTU %s", inter_or_net, mtu
    )
    cmd = ["ip", "link", "list", inter_or_net, "|", "grep", mtu]
    rc, out, _ = vds_resource.run_command(cmd)
    if rc:
        return False

    if out.find(mtu) == -1:
        logger.error(
            "MTU is not configured correctly on %s: %s", inter_or_net, out
        )
        return False
    return True


def check_mtu(
    vds_resource, mtu, physical_layer=True, network=None, nic=None,
    vlan=None, bond=None, bond_nic1='eth3', bond_nic2='eth2', bridged=True
):
    """
    Check MTU for all files provided from build_list_files_mtu function
    Uses helper test_mtu_in_script_list function to do it

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param mtu: the value to test against
    :type mtu: int
    :param network: the network name to test the MTU value
    :type network: str
    :param physical_layer: flag to test MTU for physical or logical layer
    :type physical_layer: bool
    :param nic: interface name to test the MTU value for
    :type nic: str
    :param vlan: vlan number to test the MTU value for nic.vlan
    :type vlan: str
    :param bond: bond name to test the MTU value for
    :type bond: str
    :param bond_nic1: name of the first nic of the bond
    :type bond_nic1: str
    :param bond_nic2: name of the second nic of the bond
    :type bond_nic2: str
    :param bridged: flag, to differentiate bridged and non_bridged network
    :type bridged: bool
    :return: True value if MTU in script files is correct
    :rtype: bool
    """
    ifcfg_script_list, sys_class_net_list = build_list_files_mtu(
        physical_layer=physical_layer, network=network, nic=nic, vlan=vlan,
        bond=bond, bond_nic1=bond_nic1, bond_nic2=bond_nic2, bridged=bridged
    )
    if not ifcfg_script_list or not sys_class_net_list:
        if not physical_layer and not bridged and not vlan:
            return True
        else:
            logger.error("The file with MTU parameter is empty")
            return False
    return test_mtu_in_script_list(
        vds_resource=vds_resource, script_list=ifcfg_script_list, mtu=mtu,
        flag_for_ifcfg=1) and test_mtu_in_script_list(
        vds_resource=vds_resource, script_list=sys_class_net_list, mtu=mtu
    )


def test_mtu_in_script_list(vds_resource, script_list, mtu, flag_for_ifcfg=0):
    """
    Helper function for check_mtu to test specific list of files

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param script_list: list with names of files to test MTU in
    :type script_list: list
    :param mtu: the value to test against
    :type mtu: int
    :param flag_for_ifcfg: flag if this file is ifcfg or not
    :type flag_for_ifcfg: int
    :return: True value if MTU in script list is correct
    :type: bool
    """
    err_msg = '"MTU in {0} is {1} when the expected is {2}"'
    for script_name in script_list:
        logger.info("Check if MTU for %s is %s", script_name, mtu)
        rc, out, _ = vds_resource.run_command(['cat', script_name])
        if rc:
            return False
        if flag_for_ifcfg:
            match_obj = re.search('MTU=([0-9]+)', out)
            if match_obj:
                mtu_script = int(match_obj.group(1))
            else:
                mtu_script = MTU_DEFAULT_VALUE
            if mtu_script != mtu:
                logger.error(err_msg.format(script_name, mtu_script, mtu))
                return False
        else:
            if int(out) != mtu:
                logger.error(err_msg.format(script_name, out, mtu))
                return False
    return True


def configure_temp_mtu(vds_resource, mtu, nic="eth1"):
    """
    Configure MTU temporarily on specific host interface

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param mtu: MTU to be configured on the host interface
    :type mtu: string
    :param nic: specific interface to configure MTU on
    :type nic: string
    :return: True if command executed successfully, False otherwise
    :rtype: bool
    """
    cmd = ["ip", "link", "set", "dev", nic, "mtu", mtu]
    rc, _, _ = vds_resource.run_command(cmd)
    if rc:
        return False
    return True


def run_tcp_dump(host_obj, nic, **kwargs):
    """
    Runs tcpdump on the given machine and returns its output.

    :param host_obj: Host resource
    :type host_obj: resources.VDS object
    :param nic: interface on which traffic will be monitored
    :type nic: str
    :param kwargs: Extra kwargs
    :type kwargs: dict
        :param src: source IP by which to filter packets
        :type src: str
        :param dst: destination IP by which to filter packets
        :type dst: str
        :param srcPort: source port by which to filter packets, should be
                       numeric (e.g. 80 instead of 'HTTP')
        :type srcPort: str
        :param dstPort: destination port by which to filter packets, should
                       be numeric like 'srcPort'
        :type dstPort: str
        :param protocol: protocol by which traffic will be received
        :type protocol: str
        :param numPackets: number of packets to be received (10 by default)
        :type numPackets: str
    :return: Returns tcpdump's output and return code.
    :rtype: tuple
    """
    cmd = [
        "timeout", kwargs.pop("timeout", TCDUMP_TIMEOUT), "tcpdump", "-i",
        nic, "-c", str(kwargs.pop("numPackets", "10")), "-nn"
    ]
    if kwargs:
        for k, v in kwargs.iteritems():
            cmd.extend([k, str(v), "and"])
        cmd.pop()  # Removes unnecessary "and"

    logger.info("TcpDump command to be sent: %s", cmd)
    host_exec = host_obj.executor()
    rc, output, err = host_exec.run_cmd(cmd)
    logger.debug("TcpDump output:\n%s", output)
    if rc:
        logger.error(
            "Failed to run tcpdump command or no packets were captured by "
            "filter. Output: %s ERR: %s", output, err
        )
        return False
    return True


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


def raise_if_exception(results):
    """
    Raises exception if any of Future object in results has exception

    :param results: list of Future objects
    :type results: list
    """
    for result in results:
        if result.exception():
            logger.error(result.exception())
            raise result.exception()
