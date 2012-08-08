#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
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

from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api, split, getStat, searchElement
import os
import time
from lxml import etree
from utilities import machine
from art.core_api.apis_utils import TimeoutingSampler, data_st
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
import utilities.ssh_session as ssh_session
import re
from utilities.utils import getIpAddressByHostName, getHostName, readConfFile
# TODO: remove both compareCollectionSize, dump_entity is not needed
from art.core_api.validator import compareCollectionSize, dump_entity
from art.rhevm_api.tests_lib.networks import getClusterNetwork
from art.rhevm_api.tests_lib.vms import startVm, stopVm, stopVms, startVms
from art.rhevm_api.utils.xpath_utils import XPathMatch, XPathLinks
from art.rhevm_api.utils.test_utils import searchForObj
from art.test_handler import settings

ELEMENT = 'host'
COLLECTION = 'hosts'
HOST_API = get_api(ELEMENT, COLLECTION)
CL_API = get_api('cluster', 'clusters')
DC_API = get_api('data_center', 'datacenters')
TAG_API = get_api('tag', 'tags')
HOST_NICS_API = get_api('host_nic', 'host_nics')

xpathMatch = XPathMatch(HOST_API)
xpathHostsLinks = XPathLinks(HOST_API)

Host = getDS('Host')
Options = getDS('Options')
Option = getDS('Option')
PowerManagement = getDS('PowerManagement')
Tag = getDS('Tag')
StorageManager = getDS('StorageManager')

SED = '/bin/sed'
SERVICE = '/sbin/service'
ELEMENTS = os.path.join(os.path.dirname(__file__), '../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
KSM_STATUSFILE = '/sys/kernel/mm/ksm/run'


def isKSMRunning(positive, host, host_user, host_passwd):
    '''
    Description: checks the Kernel Shared Memory daemon status on the host
    Author: adarazs
    Parameters:
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
    Return: True if KSM daemon is running & positive is True or KSM is
    not running and positive is False, returns False otherwise
    '''
    host_obj = machine.Machine(host, host_user, host_passwd).util('linux')
    output = host_obj.runCmd(['cat', KSM_STATUSFILE])
    if not output[0]:
        HOST_API.logger.error("Can't read '/sys/kernel/mm/ksm/run' on %s", host)
        return False
    # check if there's a 1 or a 0 in the file
    match_obj = re.search('([01])[\n\r]*$', output[1])
    status = match_obj.group(1) == '1'
    return status == positive


def calcVMNum(positive, host, vm_mem, cluster):
    '''
    Description: calculates the number or VMs a host can run
    Author: adarazs
    Parameters:
      * host - name of a host
      * vm_mem - the amount of memory a guest will have
      * cluster - the name of the cluster where the VMs will be created
    Return: True and the estimated number of VMs that can run on the
    host, False on error
    '''
    stats = getStat(host, ELEMENT, COLLECTION, ['memory.total', 'memory.used'])
    total_mem = stats['memory.total']
    base_mem_usage = stats['memory.used']
    cluster_obj = CL_API.find(cluster)
    overcommit_rate = float(cluster_obj.get_memory_policy().get_overcommit().get_percent()) / 100
    if not (total_mem and overcommit_rate):
        HOST_API.logger.error("Error while getting stats.")
        return False
    vm_num = int(((total_mem - base_mem_usage) * overcommit_rate) / vm_mem) + 1
    return True, {'vm_num': vm_num}


def calcKSMThreshold(host, host_user, host_passwd, vm_mem):
    '''
    Description: calculates the number of VMs that turn the KSM daemon on
    Author: adarazs
    Parameters:
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
      * vm_mem - the memory in bytes that an individual VM gets
    Return: True and the number of VMs that makes the KSM daemon on the
    host start searching for duplicate pages, False on error reading
    the config file
    '''
    stats = getStat(host, ELEMENT, COLLECTION, ['memory.total', 'memory.used'])
    total_mem = stats['memory.total']
    base_mem_usage = stats['memory.used']
    # let's find out the thresholds for KSM on the host and default to
    # the known defaults if there are no custom settings
    host_obj = machine.Machine(host, host_user, host_passwd).util('linux')
    ksmtuned_output = host_obj.runCmd(['cat', '/etc/ksmtuned.conf'])
    if ksmtuned_output[0] is False:
        HOST_API.logger.error("Can't read '/etc/ksmtuned.conf'")
        return False
    match_obj = re.search('[^#]*\W*KSM_THRES_COEF=([0-9]+)', ksmtuned_output[1])
    if match_obj is not None:
        ksm_thres_coeff = int(match_obj.group(1))
    else:
        ksm_thres_coeff = 20
    match_obj = re.search('[^#]*\W*KSM_THRES_CONST=([0-9]+)', ksmtuned_output[1])
    if match_obj is not None:
        ksm_thres_const = int(match_obj.group(1)) * 1024 ** 2
    else:
        ksm_thres_const = 2048 * 1024 ** 2
    ksm_byte_threshold = total_mem - max(ksm_thres_coeff / 100 * total_mem,
                                         ksm_thres_const)
    ksm_threshold_num = int((ksm_byte_threshold - base_mem_usage) / vm_mem) + 1
    return ksm_threshold_num


def measureKSMThreshold(positive, poolname, vm_total, host, host_user,
                        host_passwd, guest_user, guest_passwd, vm_mem,
                        loadType, port, load=None, allocationSize=None,
                        protocol=None, clientVMs=None, extra=None):
    '''
    Description: starts VMs until the KSM daemon starts on the host.
    After the KSM is engaged, it shuts down all the started VMs.
    Author: adarazs
    Parameters:
      * poolname - the basename of the pool
      * vm_total - how many VMs are in the pool
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
      * guest_user - username for the guest
      * guest_passwd - password for the guest user
      * vm_mem - the memory in bytes that an individual VM gets
      * rest of the parameters - according to vms.runLoadOnGuest function
    Return: True if the calculated and measured VM number equals,
    False on error or otherwise
    '''

    calc_threshold = calcKSMThreshold(host, host_user, host_passwd, vm_mem)
    if not calc_threshold:
        HOST_API.logger.error("Can't calculate the expected threshold")
        return False
    HOST_API.logger.info("Expected threshold calculated to be %d", calc_threshold)
    if isKSMRunning(True, host, host_user, host_passwd):
        HOST_API.logger.error('KSM is running at the start of the test')
        return False
    status = True
    vm_decimal_places = len(str(vm_total))
    for vm_index in range(vm_total):
        vm_name = "%s-%s" % (poolname,
                             str(vm_index + 1).zfill(vm_decimal_places))
        HOST_API.logger.debug('Starting VM: %s', vm_name)
        if not startVm(True, vm_name, wait_for_status=None):
            HOST_API.logger.error('Failed to start VM: %s', vm_name)
        HOST_API.logger.debug("Waiting for the guest %s to get IP address", vm_name)
        xpath_cmd = '0=count(/vms/vm[(./status/state="%s" or \
                     ./status/state="%s") and not(./guest_info/ips/ip)])' % (
                     ENUMS['vm_state_up'], ENUMS['vm_state_powering_up'])
        waitForXPath(link='vms', xpath=xpath_cmd, timeout=600, sleep=10)
        runLoadOnGuest(True, targetVM=vm_name, osType='linux',
                       username=guest_user, password=guest_passwd,
                       loadType=loadType, duration=0, port=port, load=load,
                       allocationSize=allocationSize,
                       protocol=protocol, clientVMs=clientVMs, extra=extra,
                       stopLG=False)
        # time for stats to refresh in the REST API
        HOST_API.logger.debug("Checking if KSM is running on the host")
        if isKSMRunning(True, host, host_user, host_passwd):
            started_count = vm_index + 1
            HOST_API.logger.info("KSM threshold found at %d guests", started_count)
            break
    if calc_threshold == started_count:
        HOST_API.logger.info("Calculated and real threshold equals")
    else:
        status = False
        HOST_API.logger.error("Calculated and real threshold differs")
    HOST_API.logger.debug("Stopping the previously started VMs")
    for vm_index in range(started_count):
        vm_name = "%s-%s" % (poolname,
                        str(vm_index + 1).zfill(vm_decimal_places))
        if not stopVm(True, vm_name):
            status = False
    return status


def verifyKSMThreshold(positive, poolname, vm_total, host, host_user,
                       host_passwd, guest_user, guest_passwd, vm_mem,
                       loadType, port, load=None, allocationSize=None,
                       protocol=None, clientVMs=None, extra=None):
    '''
    Description: starts all of the calculated VMs at once and check if
    it was enough to trigger the KSM routines. Shuts down the started
    VMs after that.
    Author: adarazs
    Parameters:
      * poolname - the basename of the pool
      * vm_total - how many VMs are in the pool
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
      * guest_user - username for the guest
      * guest_passwd - password for the guest user
      * vm_mem - the memory in bytes that an individual VM gets
      * rest of the parameters - according to vms.runLoadOnGuest function
    Return: True if the calculated and measured VM number equals,
    False on error or otherwise
    '''
    # wait for host to settle down before previous test
    time.sleep(10)
    calc_threshold = calcKSMThreshold(host, host_user, host_passwd, vm_mem)
    if not calc_threshold:
        HOST_API.logger.error("Can't calculate the expected threshold")
        return False
    HOST_API.logger.info("Expected threshold calculated to be %d", calc_threshold)
    if isKSMRunning(True, host, host_user, host_passwd):
        HOST_API.logger.error('KSM is running at the start of the test')
        return False
    status = True
    vm_decimal_places = len(str(vm_total))
    vm_list = []
    for vm_index in range(calc_threshold):
        vm_name = "%s-%s" % (poolname,
                             str(vm_index + 1).zfill(vm_decimal_places))
        vm_list.append(vm_name)
    HOST_API.logger.debug('Starting VMs')
    if not startVms(','.join(vm_list)):
        HOST_API.logger.error('Failed to start VMs')
        return False
    HOST_API.logger.debug("Waiting for the guests to get IP addresses")
    xpath_cmd = '0=count(/vms/vm[(./status/state="%s" or \
                    ./status/state="%s") and not(./guest_info/ips/ip)])' % (
                    ENUMS['vm_state_up'], ENUMS['vm_state_powering_up'])
    waitForXPath(link='vms', xpath=xpath_cmd, timeout=600, sleep=10)
    for vm_name in vm_list:
        runLoadOnGuest(True, targetVM=vm_name, osType='linux',
                        username=guest_user, password=guest_passwd,
                        loadType=loadType, duration=0, port=port, load=load,
                        allocationSize=allocationSize,
                        protocol=protocol, clientVMs=clientVMs, extra=extra,
                        stopLG=False)
        # time for stats to refresh in the REST API
    HOST_API.logger.debug("Checking if KSM is running on the host")
    if isKSMRunning(True, host, host_user, host_passwd):
        HOST_API.logger.info("Calculated threshold triggered KSM")
    else:
        status = False
        HOST_API.logger.error("Calculated threshold not triggered KSM")
    HOST_API.logger.debug("Stopping the previously started VMs")
    if not stopVms(','.join(vm_list)):
        HOST_API.logger.error('Failed to stop VMs')
        return False
    return status


def isHostSaturated(host, max_cpu=95, max_mem=95):
    '''
    Description: checks if the host if saturated with VMs
    Author: adarazs
    Parameters:
      * host - name of a host
    Return: status (True if the host is saturated, False otherwise)
    '''
    hostObj = HOST_API.find(host)
    stats = getStat(host, ELEMENT, COLLECTION, ["memory.used", "memory.total",
                     "cpu.current.system", "cpu.current.user"])
    cpu_sum = stats["cpu.current.system"] + stats["cpu.current.user"]
    mem_percent = stats["memory.used"] / float(stats["memory.total"]) * 100.0
    if cpu_sum > max_cpu or mem_percent > max_mem:
        if cpu_sum > max_cpu:
            HOST_API.logger.info("Host %s reached the CPU saturation point", host)
        else:
            HOST_API.logger.info("Host %s reached the memory saturation point", host)
        return True
    return False


def saturateHost(positive, poolname, vm_total, host, host_user,
                 host_passwd, guest_user, guest_passwd, loadType, port,
                 load=None, allocationSize=None, protocol=None,
                 clientVMs=None, extra=None):
    '''
    Description: starts VMs until the host gets saturated
    when that happens, it shuts down all the started VMs
    Author: adarazs
    Parameters:
      * poolname - the basename of the pool
      * vm_total - how many VMs are in the pool
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
      * guest_user - username for the guest
      * guest_passwd - password for the guest user
      * rest of the parameters - according to vms.runLoadOnGuest function
    Return: False on error, True otherwise
    '''
    if isHostSaturated(host):
        HOST_API.logger.error('Host is already saturated at the start of the test')
        return False
    status = True
    vm_decimal_places = len(str(vm_total))
    for vm_index in range(vm_total):
        vm_name = "%s-%s" % (poolname,
                        str(vm_index + 1).zfill(vm_decimal_places))
        HOST_API.logger.debug('Starting VM: %s', vm_name)
        if not startVm(True, vm_name, wait_for_status=None):
            HOST_API.logger.error('Failed to start VM: %s', vm_name)
        HOST_API.logger.debug("Waiting for the guest %s to get IP address", vm_name)
        xpath_cmd = '0=count(/vms/vm[(./status/state="%s" or \
                     ./status/state="%s") and not(./guest_info/ips/ip)])' % (
                     ENUMS['vm_state_up'], ENUMS['vm_state_powering_up'])
        waitForXPath(link='vms', xpath=xpath_cmd, timeout=600, sleep=10)
        runLoadOnGuest(True, targetVM=vm_name, osType='linux',
                       username=guest_user, password=guest_passwd,
                       loadType=loadType, duration=0, port=port, load=load,
                       allocationSize=allocationSize, protocol=protocol,
                       clientVMs=clientVMs, extra=extra, stopLG=False)
        # time for stats to refresh in the REST API
        time.sleep(10)
        HOST_API.logger.debug("Checking for host saturation")
        if isHostSaturated(host):
            started_count = vm_index + 1
            HOST_API.logger.info("Saturation point found at %d guests", started_count)
            break
    HOST_API.logger.debug("Stopping the previously started VMs")
    for vm_index in range(started_count):
        vm_name = "%s-%s" % (poolname,
                        str(vm_index + 1).zfill(vm_decimal_places))
        stopVm(True, vm_name)
    return status, {"satnum": started_count}


def waitForOvirtAppearance(positive, host, attempts=10, interval=3):
    '''
    Wait till ovirt host appears in rhevm.
    Author: atal
    parameters:
    host - name of the host
    attempts - number of tries
    interval - wait between tries
    return True/False
    '''
    while attempts:
        try:
            HOST_API.find(host)
            return True
        except EntityNotFound:
            attempts -= 1
            time.sleep(interval)
    return False


def waitForHostsStates(positive, names, states='up'):
    '''
    Wait until all of the hosts identified by names exist and have the desired
    status.
    Parameters:
        * names - A comma separated names of the hosts with status to wait for.
        * states - A state of the hosts to wait for.
    Author: jhenner
    '''
    names = split(names)
    for host in names:
        HOST_API.find(host)
        query_host = "name={0} and status={1}".format(host, states)

        if not HOST_API.waitForQuery(query_host, timeout=1000):
            return False

    return True


def addHost(positive, name, wait=True, vdcPort=None, **kwargs):
    '''
    Description: add new host
    Author: edolinin, jhenner
    Parameters:
       * name - name of a new host
       * root_password - password of root user (required, can be empty only for negative tests)
       * address - host IP address, if not provided - fetched automatically from name
       * port - port number
       * cluster - name of the cluster where to attach a new host
       * wait - True if test should wait until timeout or the host state to be "UP".
       * vdcPort - vdc port (default = port parameter, located at settings.conf)
       * override_iptables - override iptables. gets true/false strings.
    Return: True if host     added and test is    positive,
            True if host not added and test isn't positive,
            False otherwise.
    '''

    address = kwargs.get('address')
    if not address:
        host_address = getIpAddressByHostName(name)
    else:
        host_address = kwargs.pop('address')

    cluster = kwargs.pop('cluster', 'Default')
    hostCl = CL_API.find(cluster)

    osType = 'rhel'
    root_password = kwargs.get('root_password')
    if root_password and positive:
        hostObj = machine.Machine(host_address, 'root', root_password).util('linux')
        hostObj.isConnective(attempt=5, interval=5, remoteCmd=False)
        osType = hostObj.getOsInfo()
        if not osType:
            HOST_API.logger.error("Can't get host %s os info" % name)
            return False

    if osType.lower().find('hypervisor') == -1:
        host = Host(name=name, cluster=hostCl, address=host_address, **kwargs)
        host, status = HOST_API.create(host, positive)

        if not wait:
            return status and positive
        if hasattr(host, 'href'):
            return status and HOST_API.waitForElemStatus(host, "up", 800)
        else:
            return status and not positive

    if vdcPort is None:
        vdcPort = settings.opts['port']

    if not installOvirtHost(positive, name, 'root', root_password, settings.opts['host'], vdcPort):
        return False

    return approveHost(positive, name, cluster)


def updateHost(positive, host, **kwargs):
    '''
    Description: update properties of existed host (provided in parameters)
    Author: edolinin
    Parameters:
       * host - name of a target host
       * name - host name to change to
       * address - host address to change to
       * root_password - host password to change to
       * cluster - host cluster to change to
       * pm - host power management to change to
       * pm_type - host pm type to change to
       * pm_address - host pm address to change to
       * pm_username - host pm username to change to
       * pm_password - host pm password to change to
       * pm_port - host pm port to change to
       * pm_secure - host pm security to change to
    Return: status (True if host was updated properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    hostUpd = Host()

    if 'name' in kwargs:
        hostUpd.set_name(kwargs.pop('name'))
    if 'address' in kwargs:
        hostUpd.set_address(kwargs.pop('address'))
    if 'root_password' in kwargs:
        hostUpd.set_root_password(kwargs.pop('root_password'))

    if 'cluster' in kwargs:
        cl = CL_API.find(kwargs.pop('cluster', 'Default'))
        hostUpd.set_cluster(cl)

    if 'storage_manager_priority' or 'storage_manager' in kwargs:
        value = kwargs.pop('storage_manager', hostObj.storage_manager.valueOf_)
        priority_ = kwargs.pop('storage_manager_priority', hostObj.storage_manager.priority)
        sm = StorageManager(priority=priority_, valueOf_=value)
        hostUpd.set_storage_manager(sm)

    if 'pm' in kwargs:
        pm_address = kwargs.get('pm_address')
        pm_username = kwargs.get('pm_username')
        pm_password = kwargs.get('pm_password')
        pm_port = kwargs.get('pm_port')
        pm_slot = kwargs.get('pm_slot')
        pm_secure = kwargs.get('pm_secure')

        pmOptions = None

        if pm_port or pm_secure:
            pmOptions = Options()
            if pm_port and pm_port.strip():
                op = Option(name='port', value=pm_port)
                pmOptions.add_option(op)
            if pm_secure:
                op = Option(name='secure', value=pm_secure)
                pmOptions.add_option(op)
            if pm_slot:
                op = Option(name='slot', value=pm_slot)
                pmOptions.add_option(op)

        hostPm = PowerManagement(type_=kwargs.get('pm_type'), address=pm_address,
            enabled=kwargs.get('pm'), username=pm_username, password=pm_password,
            options=pmOptions)

        hostUpd.set_power_management(hostPm)

    hostObj, status = HOST_API.update(hostObj, hostUpd, positive)

    return status


def removeHost(positive, host):
    '''
    Description: remove existed host
    Author: edolinin
    Parameters:
       * host - name of a host to be removed
    Return: status (True if host was removed properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    return HOST_API.delete(hostObj, positive)


def activateHost(positive, host, wait=True):
    '''
    Description: activate host (set status to UP)
    Author: edolinin
    Parameters:
       * host - name of a host to be activated
    Return: status (True if host was activated properly, False otherwise)
    '''
    hostObj = HOST_API.find(host)
    status = HOST_API.syncAction(hostObj, "activate", positive)

    if status and wait and positive:
        testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 200)
    else:
        testHostStatus = True

    return status and testHostStatus


def deactivateHost(positive, host, expected_status=ENUMS['host_state_maintenance']):
    '''
    Description: deactivate host (set status to MAINTENANCE)
    Author: jhenner
    Parameters:
       * host - the name of a host to be deactivated.
       * host_state_maintenance - the state to expect the host to remain in.
    Return: status (True if host was deactivated properly and postive,
                    False otherwise)
    '''

    hostObj = HOST_API.find(host)
    if not HOST_API.syncAction(hostObj, "deactivate", positive):
        return False

    # If state got changed, it may be transitional state so we may want to wait
    # for the final one. If it didn't, we certainly may return immediately.
    hostState = hostObj.get_status().get_state()
    getHostStateAgain = HOST_API.find(host).get_status().get_state()
    state_changed = hostState != getHostStateAgain
    if state_changed:
        testHostStatus = HOST_API.waitForElemStatus(hostObj, expected_status, 180)
        return testHostStatus and positive
    else:
        return not positive


def installHost(positive, host, root_password, override_iptables='false'):
    '''
    Description: run host installation
    Author: edolinin, atal
    Parameters:
       * host - name of a host to be installed
       * root_password - password of root user
       * override_iptables - override iptables. gets true/false strings.
    Return: status (True if host was installed properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    status = HOST_API.syncAction(hostObj, "install", positive,
                             root_password=root_password,
                             override_iptables=override_iptables.lower())
    if not status:
        return False

    return HOST_API.waitForElemStatus(hostObj, "up", 800)


def approveHost(positive, host, cluster='Default'):
    '''
    Description: approve host (for ovirt hosts)
    Author: edolinin
    Parameters:
       * host - name of a host to be approved
       * cluster - name of cluster
    Return: status (True if host was approved properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    clusterObj = HOST_API.find(cluster)

    kwargs = {'cluster': clusterObj}
    status = HOST_API.syncAction(hostObj, "approve", positive, **kwargs)
    testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 120)

    return status and testHostStatus


# FIXME: need to rewrite this def because new ovirt approval has been changed
def installOvirtHost(positive, host, user_name, password, vdc, port=443, timeout=60):
    '''
    Description: installation of ovirt host
    Author: edolinin
    Parameters:
       * host - name of a host to be installed
       * user_name - user name to open ssh session
       * password - password to open ssh session
       * vdc - name of vdc where host should be installed
       * port - port number
       * timeout - How maximum time wait [sec] after service restart
       * waitTime - wait between iteration [sec]
    Return: status (True if host was installed properly, False otherwise)
    '''
    if waitForHostsStates(positive, host, 'PENDING_APPROVAL'):
        return True

    vdcHostName = getHostName(vdc)
    if not vdcHostName:
        HOST_API.logger.error("Can't get hostname from %s" % vdc)

    hostObj = machine.Machine(host, user_name, password).util('linux')
    if not hostObj.isConnective():
        HOST_API.logger.error("No connectivity to the host %s" % host)
        return False
    commands = []
    commands.append([SED, '-i', "'s/vdc_host_name=.*/vdc_host_name=" + vdcHostName + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SED, '-i', "'s/nc_host_name=.*/nc_host_name=" + vdc + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SED, '-i', "'s/vdc_host_port=.*/vdc_host_port=" + str(port) + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SERVICE, 'vdsm-reg', "restart"])
    for command in commands:
        res, out = hostObj.runCmd(command)
        if not res:
            HOST_API.logger.error("command %s" % " ".join(command))
            HOST_API.logger.error(str(out))
            return False

    if not waitForOvirtAppearance(positive, host, attempts=20, interval=3):
        HOST_API.logger.error("Host %s doesn't appear!" % host)
        return False

    if not waitForHostsStates(positive, host, states='pending_approval'):
        HOST_API.logger.error("Host %s isn't in PENDING_APPROVAL state" % host)
        return False

    return True


def commitNetConfig(positive, host):
    '''
    Description: save host network configuration
    Author: edolinin
    Parameters:
       * host - name of a host to be committed
    Return: status (True if host network configuration was saved properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    return HOST_API.syncAction(hostObj, "commitnetconfig", positive)


def fenceHost(positive, host, fence_type):
    '''
    Description: host fencing
    Author: edolinin
    Parameters:
       * host - name of a host to be fenced
       * fence_type - fence action (start/stop/restart/status)
    Return: status (True if host was fenced properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    status = HOST_API.syncAction(hostObj, "fence", positive,
                             fence_type=fence_type.upper())

    # if test type is negative, we don't have to wait for element status,
    # since host state will not be changed
    if status and not positive:
        return True
    testHostStatus = True
    if fence_type == "restart" or fence_type == "start":
        testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 500)
    if fence_type == "stop":
        testHostStatus = HOST_API.waitForElemStatus(hostObj, "down", 300)
    return (testHostStatus and status) == positive


def _prepareHostNicObject(**kwargs):
    '''
    preparing Host Nic object
    Author: atal
    return: Host Nic data structure object
    '''

    add = True
    if 'nic' in kwargs:
        nic_obj = kwargs.get('nic')
        add = False
    else:
        nic_obj = data_st.HostNIC()

    if 'name' in kwargs:
        nic_obj.set_name(kwargs.get('name'))

    if 'network' in kwargs:
        nic_obj.set_network(data_st.Network(name=kwargs.get('network')))

    if 'boot_protocol'in kwargs:
        nic_obj.set_boot_protocol(kwargs.get('boot_protocol'))

    address = kwargs.get('address')
    netmask = kwargs.get('netmask')
    gateway = kwargs.get('gateway')
    if (address or netmask or gateway) is not None:
        ip_obj = data_st.IP() if add else nic_obj.get_ip()
        if 'address' in kwargs:
            ip_obj.set_address(kwargs.get('address'))
        if 'netmask' in kwargs:
            ip_obj.set_netmask(kwargs.get('netmask'))
        if 'gateway' in kwargs:
            ip_obj.set_gateway(kwargs.get('gateway'))
        nic_obj.set_ip(ip_obj)

    slave_list = kwargs.get('slaves')
    mode = kwargs.get('mode')
    miimon = kwargs.get('miimon')

    if (slave_list or mode or miimon) is not None:
        bond_obj = data_st.Bonding()
        if slave_list is not None:
            slaves = data_st.Slaves()
            for nic in slave_list.split(','):
                slaves.add_host_nic(data_st.HostNIC(name=nic.strip()))

            bond_obj.set_slaves(slaves)

        if (mode or miimon) is not None:
            options = data_st.Options()
            if mode is not None:
                options.add_option(data_st.Option(name='mode', value=mode))

            if miimon is not None:
                options.add_option(data_st.Option(name='miimon', value=miimon))
            bond_obj.set_options(options)

        nic_obj.set_bonding(bond_obj)

    if 'check_connectivity' in kwargs:
        nic_obj.set_check_connectivity(kwargs.get('check_connectivity'))

    return nic_obj


def getHostNic(host, nic):

    host_obj = HOST_API.find(host)
    return HOST_API.getElemFromElemColl(host_obj, nic, 'nics', 'host_nic')


def getHostNics(host):

    host_obj = HOST_API.find(host)
    return HOST_API.getElemFromLink(host_obj, 'nics', 'host_nic', get_href=True)


def getHostNicsList(host):

    host_obj = HOST_API.find(host)
    return HOST_API.getElemFromLink(host_obj, 'nics', 'host_nic', get_href=False)


def hostNicsNetworksMapper(host):
    '''
    Description: creates mapping between host's NICs and networks
    Author: pdufek
    Parameters:
        * host - the name of the host
    Returns: dictionary (key: NIC name, value: assigned network)
    '''
    nic_objs = getHostNicsList(host)
    nics_to_networks = {}

    for nic in nic_objs:
        nics_to_networks[nic.name] = getattr(nic, 'network', None)

    return nics_to_networks


# FIXME: remove "positive" if not in use!
def getFreeInterface(positive, host):
    '''
    Description: get host's free interface (not assigned to any network)
    Author: pdufek
    Parameters:
        * host - the name of the host
    Returns: NIC name or EntityNotFound exception
    '''
    for nic, network in hostNicsNetworksMapper(host).iteritems():
        if network is None:
            return True, {'freeNic': nic}
    return False, {'freeNic': None}


def attachHostNic(positive, host, nic, network):
    '''
    Description: attach network interface card to host
    Author: edolinin
    Parameters:
        * host - name of a host to attach nic to
        * nic - nic name to be attached
        * network - network name
    Return: status (True if nic was attached properly to host, False otherwise)
    '''

    host_obj = HOST_API.find(host)
    cluster = CL_API.find(host_obj.cluster.id, 'id').get_name()

    host_nic = getHostNic(host, nic)
    cl_net = getClusterNetwork(cluster, network)

    return HOST_API.syncAction(host_nic, "attach", positive, network=cl_net)


def attachMultiNicsToHost(positive, host, nic, networks):
    '''
    Attaching multiple nics to single host
    Author: atal
    Parameters:
        * host - host name
        * nic - nic name
        * networks - network name list
    return True/False
    '''
    for net in networks:
        if not attachHostNic(positive, host, nic, net):
            return False
    return True


def updateHostNic(positive, host, nic, **kwargs):
    '''
    Description: update nic of host
    Author: atal
    Parameters:
        * host - host where nic should be updated
        * nic - nic name that should be updated
        * network - network name
        * boot_protocol - static, none or dhcp
        * address - ip address incase of static protocol
        * netmask - netmask incase of static protocol
        * gateway - gateway address incase of static protocol
        * slaves - bonding slaves list as a string with commas
        * mode - bonding mode (int), added as option
        * miimon - another int for bonding options
        * check_connectivity - boolean and working only for management int.
    Return: status (True if nic was updated properly, False otherwise)
    '''

    nic_obj = getHostNic(host, nic)
    kwargs.update([('nic', nic_obj)])
    nic_new = _prepareHostNicObject(**kwargs)
    nic, status = HOST_NICS_API.update(nic_obj, nic_new, positive)

    return status


# FIXME: network param is deprecated.
def detachHostNic(positive, host, nic, network=None):
    '''
    Description: detach network interface card from host
    Author: edolinin
    Parameters:
       * host - name of a host to attach nic to
       * nic - nic name to be detached
    Return: status (True if nic was detach properly from host, False otherwise)
    '''
    nicObj = getHostNic(host, nic)

    return HOST_API.syncAction(nicObj, "detach", positive, network=nicObj.get_network())


def detachMultiVlansFromBond(positive, host, nic, networks):
    '''
    Detaching multiple networks from bonded host nic
    Author: atal
    Parameters:
        * host - host name
        * nic - nic name
        * networks - networks name list'
    return True/False
    '''
    regex = re.compile('\w(\d+)', re.I)
    for net in networks:
        match = regex.search(net)
        if not match:
            return False
        if not detachHostNic(positive, host, nic + '.' + match.group(1), net):
            return False
    return True


def addBond(positive, host, name, **kwargs):
    '''
    Description: add bond to a host
    Author: edolinin (maintain by atal)
    Parameters:
        * name - bond name
        * network - network name
        * boot_protocol - static, none or dhcp
        * address - ip address incase of static protocol
        * netmask - netmask incase of static protocol
        * gateway - gateway address incase of static protocol
        * slaves - bonding slaves list as a string with commas
        * mode - bonding mode (int), added as option
        * miimon - another int for bonding options
        * check_connectivity - boolean and working only for management int.
         supported modes are: 1,2,4,5. using underscore due to XML syntax limitations
    Return: status (True if bond was attached properly to host, False otherwise)
    '''
    kwargs.update([('name', name)])

    nic_obj = _prepareHostNicObject(**kwargs)
    host_nics = getHostNics(host)
    res, status = HOST_NICS_API.create(nic_obj, positive, collection=host_nics)

    return status


def genSNNic(nic, **kwargs):
    '''
    generate a host_nic element of types regular or vlaned
    Author: atal
    params:
        * host - host where nic should be updated
        * nic - nic name that should be updated
        * network - network name
        * boot_protocol - static, none or dhcp
        * address - ip address incase of static protocol
        * netmask - netmask incase of static protocol
        * gateway - gateway address incase of static protocol
    return True, dict with host nic element.
    '''
    kwargs.update([('name', nic)])
    nic_obj = _prepareHostNicObject(**kwargs)

    return True, {'host_nic': nic_obj}


def genSNBond(name, **kwargs):
    '''
    generate a host_nic element of type bond.
    Author: atal
    params:
        * name - bond name
        * network - network name
        * boot_protocol - static, none or dhcp
        * address - ip address incase of static protocol
        * netmask - netmask incase of static protocol
        * gateway - gateway address incase of static protocol
        * slaves - bonding slaves list as a string with commas
        * mode - bonding mode (int), added as option
        * miimon - another int for bonding options
        * check_connectivity - boolean and working only for management int.
         supported modes are: 1,2,4,5. using underscore due to XML syntax limitations
    return True, dict with host nic element.
    '''
    kwargs.update([('name', name)])
    nic_obj = _prepareHostNicObject(**kwargs)

    return True, {'host_nic': nic_obj}


def sendSNRequest(positive, host, nics=None, auto_nics=None, **kwargs):
    '''
    send a POST request for <action> after attaching all host_nic
    Author: atal
    params:
        * host - a name of the host
        * nics - list of 'host_nic' values returned by genSN... functions.
        * auto_nics - a list of nics to collect automatically from the element.
        * kwargs - a dictionary of supported options:
            check_connectivity=boolean, connectivity_timeout=int, force=boolean
    '''
    nics = nics or []
    auto_nics = auto_nics or []

    nics_obj = data_st.HostNics()

    for nic in nics:
        nics_obj.add_host_nic(nic)

    for nic in auto_nics:
        nics_obj.add_host_nic(getHostNic(host, nic))

    return HOST_NICS_API.syncAction(nics_obj, "setupnetworks", positive, **kwargs)


def searchForHost(positive, query_key, query_val, key_name=None, **kwargs):
    '''
    Description: search for a host by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in host object equivalent to query_key
    Return: status (True if expected number of hosts equal to found by search,
    False otherwise)
    '''

    return searchForObj(HOST_API, query_key, query_val, key_name, **kwargs)


def rebootHost(positive, host, username, password):
    '''
    Description: rebooting host via ssh session
    Author: edolinin
    Parameters:
       * host - name of a host to be rebooted
       * username - user name for ssh session
       * password - password for ssh session
    Return: status (True if host was rebooted properly, False otherwise)
    '''
    hostObj = HOST_API.find(host)
    ssh = ssh_session.ssh_session(username, host, password)
    ssh.ssh("reboot")
    return HOST_API.waitForElemStatus(hostObj, "non_responsive", 180)


def runDelayedControlService(positive, host, host_user, host_passwd, service,
                          command='restart', delay=0):
    '''
    Description: Restarts a service on the host after a delay
    Author: adarazs
    Parameters:
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
      * service - the name of the service (eg. vdsmd)
      * command - command to issue (eg. start/stop/restart)
      * delay - the required delay in seconds
    Return: True if the command is sent successfully, False otherwise,
    or inverted in case of negative test
    '''
    cmd = '( sleep %d; service %s %s 1>/dev/null; echo $? )' \
               % (delay, service, command)
    host_obj = machine.Machine(host, host_user, host_passwd).util('linux')
    output = host_obj.runCmd(cmd.split(), bg=('/tmp/delayed-stdout',
                                                 '/tmp/delayed-stderr'))
    if not output[0]:
        HOST_API.logger.error("Sending delayed service control command failed. Output: %s",
                     output[1])
    return output[0] == positive


def checkDelayedControlService(positive, host, host_user, host_passwd):
    '''
    Description: Check if a previous service command succeeded or not
    Tester is responsible to wait enough before checking the result.
    Author: adarazs
    Parameters:
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
    Return: True if the command ran successfully, False otherwise,
    inverted in case of negative test
    '''
    cmd = ('cat /tmp/delayed-stdout')
    host_obj = machine.Machine(host, host_user, host_passwd).util('linux')
    output = host_obj.runCmd(cmd.split())
    if not output[0]:
        HOST_API.logger.error("Failed to check for service control command result.")
    if int(output[1]) != 0:
        HOST_API.logger.error("Last service control command failed.")
    return output[0] == positive


def addTagToHost(positive, host, tag):
    '''
    Description: add tag to a host
    Author: edolinin
    Parameters:
       * host - name of a host to add a tag to
       * tag - tag name that should be added
    Return: status (True if tag was added properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    tagObj = Tag(name=tag)
    hostTags = HOST_API.getElemFromLink(hostObj, link_name='tags', attr='tag', get_href=True)
    tagObj, status = TAG_API.create(tagObj, positive, collection=hostTags)
    return status


def removeTagFromHost(positive, host, tag):
    '''
    Description: remove tag from a host
    Author: edolinin
    Parameters:
       * host - name of a host to remove a tag from
       * tag - tag name that should be removed
    Return: status (True if tag was removed properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    tagObj = HOST_API.getElemFromElemColl(hostObj, tag, 'tags', 'tag')
    if tagObj:
        return HOST_API.delete(tagObj, positive)
    else:
        HOST_API.logger.error("Tag {0} is not found at host {1}".format(tag, host))
        return False


def checkHostStatistics(positive, host):
    '''
    Description: check hosts statistics (existence and format)
    Author: edolinin
    Parameters:
    * host - name of a host
    Return: status (True if all statistics were a success, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    expectedStatistics = ['memory.total', 'memory.used', 'memory.free',
            'memory.buffers', 'memory.cached', 'swap.total', 'swap.free',
            'swap.used', 'swap.cached', 'ksm.cpu.current', 'cpu.current.user',
            'cpu.current.system', 'cpu.current.idle', 'cpu.load.avg.5m']

    numOfExpStat = len(expectedStatistics)
    status = True
    statistics = HOST_API.getElemFromLink(hostObj, link_name='statistics', attr='statistic')

    for stat in statistics:
        datum = str(stat.get_values().get_value()[0].get_datum())
        if not re.match('(\d+\.\d+)|(\d+)', datum):
            HOST_API.logger.error('Wrong value for ' + stat.get_name() + ': ' + datum)
            status = False
        else:
            HOST_API.logger.info('Correct value for ' + stat.get_name() + ': ' + datum)

        if stat.get_name() in expectedStatistics:
            expectedStatistics.remove(stat.get_name())

    if len(expectedStatistics) == 0:
        HOST_API.logger.info('All ' + str(numOfExpStat) + ' statistics appear')
    else:
        HOST_API.logger.error('The following statistics are missing: ' + str(expectedStatistics))
        status = False

    return status


def checkHostSpmStatus(positive, hostName):
    '''
    The function checkHostSpmStatus checking Storage Pool Manager (SPM) status of the host.
        hostName - the host name
    return value : 1) True when the host is SPM and positive also True ,otherwise return False
                   2) True when host is not SPM and positive equal to False ,otherwise return False
    '''
    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host" + hostName + " doesn't have attribute " + attribute)
        return False

    spmStatus = hostObj.get_storage_manager().valueOf_
    HOST_API.logger.info("checkHostSpmStatus - SPM Status of host " + hostName + \
                    " is: " + spmStatus)

    return (spmStatus == 'true') == positive


def checkSPMPriority(positive, hostName, expectedPriority):
    '''
    Description: check SPM priority of host
    Author: imeerovi
    Parameters:
    * hostName - name/ip of host
    * expectedPriority - expecded value of SPM priority on host
    Return: True if SPM priority value is equal to expected value.
            False in other case.
    '''

    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                           hostName, attribute)
        return False

    spmPriority = hostObj.get_storage_manager().get_priority()
    HOST_API.logger.info("checkSPMPriority - SPM Value of host %s is %s",
                     hostName, spmPriority)
    return (str(spmPriority) == expectedPriority)


def setSPMPriority(positive, hostName, spmPriority):
    '''
    Description: set SPM priority on host
    Author: imeerovi
    Parameters:
    * hostName - name/ip of host
    * spmPriority - expecded value of SPM priority on host
    Return: True if spm value is set OK.
            False in other case.
    '''

    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                          hostName, attribute)
        return False

    # Update host
    HOST_API.logger.info("Updating Host %s priority to %s", hostName, spmPriority)
    updateStat = updateHost(positive=positive, host=hostName,
                            storage_manager_priority=spmPriority)
    if not updateStat:
        return False

    hostObj = HOST_API.find(hostName)
    new_priority = hostObj.get_storage_manager().get_priority()
    HOST_API.logger.info("setSPMPriority - SPM Value of host %s is set to %s",
                     hostName, new_priority)

    return  new_priority == int(spmPriority)


def setSPMStatus(positive, hostName, spmStatus):
    '''
    Description: set SPM status on host
    Author: imeerovi
    Parameters:
    * hostName - name/ip of host
    * spmPriority - expected value of SPM status on host
    Return: True if spm value is set OK.
            False in other case.
    '''

    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                          hostName, attribute)
        return False

    HOST_API.logger.info("setSPMStatus - SPM Value of host is set to %s is %s",
                     hostName, spmStatus)

    # Update host
    HOST_API.logger.info("Updating Host %s", hostName)
    updateStat = updateHost(positive=positive, host=hostName,
                            storage_manager=spmStatus)
    if not updateStat:
        return False

    return hostObj.get_storage_manager().get_valueOf_() == spmStatus


def checkHostSubelementPresence(positive, host, element_path):
    '''
    Checks the presence of element specified by element_path.
    return: True if the host has the tags in path, False otherwise.
    '''

    hostObj = HOST_API.find(host)
    actual_tag = hostObj
    path = []
    for subelem_name in element_path.split('.'):
        if not hasattr(actual_tag, subelem_name):
            msg = "Element host %s doesn't have any subelement '%s' at path '%s'."
            HOST_API.logger.error(msg % (host, subelem_name, '.'.join(path)))
            return False
        path += (subelem_name,)
        actual_tag = getattr(actual_tag, subelem_name)
    HOST_API.logger.info("checkHostAttribute - tag %s in host %s has value '%s'"
        % ('.'.join(path), host, actual_tag))
    return True


def getHost(positive, dataCenter='Default', spm=True, hostName=None):
    '''
    Locate and return SPM or HSM host from specific data center (given by name)
        dataCenter  - The data center name
        spm      - When true return SPM host, false locate and return the HSM host
        hostName - Optionally, when the host name exist, the function locates
                   the specific HSM host. When such host doesn't exist, the
                   first HSM found will be returned.
    return: True and located host name in case of success, otherwise false and None
    '''

    try:
        clusters = CL_API.get(absLink=False)
        dataCenterObj = DC_API.find(dataCenter)
    except EntityNotFound:
        return False, {'hostName': None}

    clusters = (cl for cl in clusters if hasattr(cl, 'data_center') \
        and cl.get_data_center() and cl.get_data_center().id == dataCenterObj.id)
    for cluster in clusters:
        elementStatus, hosts = searchElement(positive, ELEMENT, COLLECTION, 'cluster', cluster.name)
        if not elementStatus:
            return False, {'hostName': None}
        for host in hosts:
            spmStatus = checkHostSpmStatus(positive, host.name)
            if spm and spmStatus:
                return True, {'hostName': host.name}
            elif not spm and not spmStatus and (not hostName or hostName == host.name):
                return True, {'hostName': host.name}
    return False, {'hostName': None}


def waitForSPM(datacenter, timeout, sleep):
    '''
    Description: waits until SPM gets elected in DataCenter
    Author: jhenner
    Parameters:
      * datacenter - the name of the datacenter
      * timeout - how much seconds to wait until it fails
      * sleep - how much to sleep between checks
    Return: True if an SPM gets elected before timeout. It rises
    RESTTimeout exception on timeout.
    '''
    sampler = TimeoutingSampler(timeout, sleep,
                                getHost, True, datacenter, True)
    sampler.timeout_exc_args = \
            "Timeout when waiting for SPM to appear in DC %s." % datacenter,
    for s in sampler:
        if s[0]:
            return True


def getHostNicAttr(host, nic, attr):
    '''
    get host's nic attribute value
    Author: atal
    Parameters:
       * host - name of a host
       * nic - name of nic we'd like to check
       * attr - attribute of nic we would like to recive. attr can dive deeper as a string with DOTS ('.').
    return: True if the function succeeded, otherwise False
    '''
    try:
        nic_obj = getHostNic(host, nic)
    except EntityNotFound:
        return False, {'attrValue': None}

    for tag in attr.split('.'):
        try:
            nic_obj = getattr(nic_obj, tag)
        except AttributeError as err:
            HOST_API.logger.error(str(err))
            return False, {'attrValue': None}

    return True, {'attrValue': nic_obj}


def countHostNics(host):
    '''
    Count the number of a Host network interfaces
    Author: atal
    Parameters:
       * host - name of a host
    return: True and counter if the function succeeded, otherwise False and None
    '''
    nics = getHostNicsList(host)
    return True, {'nicsNumber': len(nics)}


# FIXME: remove this function - not being used at all, even not in actions.conf
def validateHostExist(positive, host):
    '''
    Description: Validate host if exists in the setup
    Author: egerman
    Parameters:
       * host - host name
    Return:
        1) When positive equals True and given host exists in the setup - return true,otherwise return false
        2) When positive equals False and given host does not exists in the setup  - return true,otherwise return false
    '''
    hosts = HOST_API.get(absLink=False)
    hosts = filter(lambda x: x.get_name().lower() == host.lower(), hosts)
    return bool(hosts) == positive


def getHostCompatibilityVersion(positive, host):
    '''
    Description: Get Host compatibility version
    Author: istein
    Parameters:
       * host - host name
    Return: True and compatibilty version or False and None
    '''

    try:
        hostObj = HOST_API.find(host)
    except EntityNotFound:
        return False, {'hostCompatibilityVersion': None}

    clId = hostObj.get_cluster().get_id()
    try:
        clObj = CL_API.find(clId, 'id')
    except EntityNotFound:
        return False, {'hostCompatibilityVersion': None}

    cluster = clObj.get_name()
    status, clCompVer = getClusterCompatibilityVersion(positive, cluster)
    if not status:
        return False, {'hostCompatibilityVersion': None}
    hostCompatibilityVersion = clCompVer['clusterCompatibilityVersion']
    return True, {'hostCompatibilityVersion': hostCompatibilityVersion}


def waitForHostNicState(host, nic, state, interval=1, attempts=1):
    '''
    Waiting for Host's nic state
    Author: atal
    params:
        * host - host name
        * nic - nic name
        * state - state we would like to achive
        * interval - time between checks
        * attempts - number of attempts before returning False
    return True/False
    '''
    regex = re.compile(state, re.I)
    while attempts:
        res, out = getHostNicAttr(host, nic, 'status.state')
        if res and regex.match(out['attrValue']):
            return True
        time.sleep(interval)
        attempts -= 1
    return False


def ifdownNic(host, root_password, nic, wait=True):
    '''
    Turning remote machine interface down
    Author: atal
    Parameters:
        * host - host name
        * ip - ip of remote machine
        * user/password - to login remote machine
        * nic - interface name. make sure you're not trying to disable rhevm network!
    return True/False
    '''
    # must always run as a root in order to run ifdown
    host_obj = machine.Machine(getIpAddressByHostName(host), 'root', root_password).util('linux')
    if not host_obj.ifdown(nic):
        return False
    if wait:
        return waitForHostNicState(host, nic, 'down', interval=5, attempts=10)
    return True


def ifupNic(host, root_password, nic, wait=True):
    '''
    Turning remote machine interface up
    Author: atal
    Parameters:
        * host - host name
        * ip - ip of remote machine
        * user/password - to login remote machine
        * nic - interface name.
    return True/False
    '''
    # must always run as a root in order to run ifup
    host_obj = machine.Machine(getIpAddressByHostName(host), 'root', root_password).util('linux')
    if not host_obj.ifup(nic):
        return False
    if wait:
        return waitForHostNicState(host, nic, 'up', interval=5, attempts=10)
    return True


def checkIfNicStateIs(host, user, password, nic, state):
    '''
    Check if given nic state same as given state
    Author: atal
    Parameters:
        * ip - ip of remote machine
        * user/password - to login remote machine
        * nic - interface name.
        * state - state user like to check (up|down)
    return True/False
    '''
    host_obj = machine.Machine(getIpAddressByHostName(host), user, password).util('linux')
    regex = re.compile(state, re.I)
    if regex.match(host_obj.getNicState(nic)) is not None:
        return True
    return False


def getOsInfo(host, root_password=''):
    '''
    Description: get OS info wrapper.
    Author: atal
    Parameters:
       * host - name of a new host
       * root_password - password of root user (required, can be empty only for negative tests)
    Return: True with OS info string if succeeded, False and None otherwise
    '''
    host_obj = machine.Machine(host, 'root', root_password).util('linux')
    if not host_obj.isAlive():
        HOST_API.logger.error("No connectivity to the host %s" % host)
        return False, {'osName': None}
    osName = host_obj.getOsInfo()
    if not osName:
        return False, {'osName': None}

    return True, {'osName': osName}


def reinstallOvirt(positive, host, image='rhev-hypervisor.iso'):
    '''
    Description: get OS info wrapper.
    Author: atal
    Parameters:
        * host - host name
        * image - ovirt iso under /usr/share/rhev-hypervisor/
    Return: True if success, False otherwise
    '''
    host_obj = HOST_API.find(host)
    status = HOST_API.syncAction(host_obj, "install", positive, image=image)

    testHostStatus = HOST_API.waitForElemStatus(host_obj, "up", 800)
    return status and testHostStatus


def getClusterCompatibilityVersion(positive, cluster):
    '''
    Description: Get Cluster compatibility version
    Author: istein
    Parameters:
       * cluster - cluster name
    Return: True and compatibilty version or False and None
    '''
    try:
        clusterObj = CL_API.find(cluster)
    except EntityNotFound as err:
        HOST_API.logger.error(err)
        return False, {'clusterCompatibilityVersion': None}
    clVersion = '{0}.{1}'.format(clusterObj.get_version().get_major(),
                                clusterObj.get_version().get_minor())
    return True, {'clusterCompatibilityVersion': clVersion}
