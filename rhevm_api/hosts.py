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

from framework_utils.apis_utils import getDS
from rhevm_api.test_utils import get_api, split, getStat
import os
import time
from lxml import etree
from utilities import machine
from framework_utils.apis_utils import TimeoutingSampler
from framework_utils.apis_exceptions import APITimeout, EntityNotFound
import utilities.ssh_session as ssh_session
import re
from utilities.utils import getIpAddressByHostName, getHostName, readConfFile
from framework_utils.validator import compareCollectionSize
from rhevm_api.networks import getClusterNetwork

ELEMENT = 'host'
COLLECTION = 'hosts'
util = get_api(ELEMENT, COLLECTION)
clUtil = get_api('cluster', 'clusters')
dcUtil = get_api('data_center', 'datacenters')
tagUtil = get_api('tag', 'tags')

Host = getDS('Host')
Options = getDS('Options')
Option = getDS('Option')
IP = getDS('IP')
PowerManagement = getDS('PowerManagement')
Tag = getDS('Tag')

SED = '/bin/sed'
SERVICE = '/sbin/service'
ELEMENTS=os.path.join(os.path.dirname(__file__), '../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
KSM_STATUSFILE='/sys/kernel/mm/ksm/run'


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
        logger.error("Can't read '/sys/kernel/mm/ksm/run' on %s", host)
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
    cluster_obj = clUtil.find(cluster)
    overcommit_rate = float(cluster_obj.get_memory_policy().get_overcommit().get_percent()) / 100
    if not (total_mem and overcommit_rate):
        util.logger.error("Error while getting stats.")
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
        logger.error("Can't read '/etc/ksmtuned.conf'")
        return False
    match_obj = re.search('[^#]*\W*KSM_THRES_COEF=([0-9]+)', ksmtuned_output[1])
    if match_obj is not None:
        ksm_thres_coeff = int(match_obj.group(1))
    else:
        ksm_thres_coeff = 20
    match_obj = re.search('[^#]*\W*KSM_THRES_CONST=([0-9]+)', ksmtuned_output[1])
    if match_obj is not None:
        ksm_thres_const = int(match_obj.group(1)) * 1024**2
    else:
        ksm_thres_const = 2048 * 1024**2
    ksm_byte_threshold = total_mem - max(ksm_thres_coeff/100 * total_mem,
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
        util.logger.error("Can't calculate the expected threshold")
        return False
    logger.info("Expected threshold calculated to be %d", calc_threshold)
    if isKSMRunning(True, host, host_user, host_passwd):
        util.logger.error('KSM is running at the start of the test')
        return False
    status = True
    vm_decimal_places = len(str(vm_total))
    for vm_index in range(vm_total):
        vm_name = "%s-%s" % (poolname,
                             str(vm_index + 1).zfill(vm_decimal_places))
        util.logger.debug('Starting VM: %s', vm_name)
        if not startVm(True, vm_name, wait_for_status=None):
            logger.error('Failed to start VM: %s', vm_name)
        util.logger.debug("Waiting for the guest %s to get IP address", vm_name)
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
        util.logger.debug("Checking if KSM is running on the host")
        if isKSMRunning(True, host, host_user, host_passwd):
            started_count = vm_index + 1
            logger.info("KSM threshold found at %d guests", started_count)
            break
    if calc_threshold == started_count:
        util.logger.info("Calculated and real threshold equals")
    else:
        status = False
        util.logger.error("Calculated and real threshold differs")
    logger.debug("Stopping the previously started VMs")
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
        logger.error("Can't calculate the expected threshold")
        return False
    logger.info("Expected threshold calculated to be %d", calc_threshold)
    if isKSMRunning(True, host, host_user, host_passwd):
        logger.error('KSM is running at the start of the test')
        return False
    status = True
    vm_decimal_places = len(str(vm_total))
    vm_list = []
    for vm_index in range(calc_threshold):
        vm_name = "%s-%s" % (poolname,
                             str(vm_index + 1).zfill(vm_decimal_places))
        vm_list.append(vm_name)
    logger.debug('Starting VMs')
    if not startVms(','.join(vm_list)):
        logger.error('Failed to start VMs')
        return False
    logger.debug("Waiting for the guests to get IP addresses")
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
    logger.debug("Checking if KSM is running on the host")
    if isKSMRunning(True, host, host_user, host_passwd):
        logger.info("Calculated threshold triggered KSM")
    else:
        status = False
        logger.error("Calculated threshold not triggered KSM")
    logger.debug("Stopping the previously started VMs")
    if not stopVms(','.join(vm_list)):
        logger.error('Failed to stop VMs')
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
    hostObj = util.find(host)
    stats = getStat(host, ELEMENT, COLLECTION, ["memory.used", "memory.total",
                     "cpu.current.system", "cpu.current.user"])
    cpu_sum = stats["cpu.current.system"] + stats["cpu.current.user"]
    mem_percent = stats["memory.used"] / float(stats["memory.total"]) * 100.0
    if cpu_sum > max_cpu or mem_percent > max_mem:
        if cpu_sum > max_cpu:
            util.logger.info("Host %s reached the CPU saturation point", host)
        else:
            util.logger.info("Host %s reached the memory saturation point", host)
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
        util.logger.error('Host is already saturated at the start of the test')
        return False
    status = True
    vm_decimal_places = len(str(vm_total))
    for vm_index in range(vm_total):
        vm_name = "%s-%s" % (poolname,
                        str(vm_index + 1).zfill(vm_decimal_places))
        util.logger.debug('Starting VM: %s', vm_name)
        if not startVm(True, vm_name, wait_for_status=None):
            util.logger.error('Failed to start VM: %s', vm_name)
        util.logger.debug("Waiting for the guest %s to get IP address", vm_name)
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
        util.logger.debug("Checking for host saturation")
        if isHostSaturated(host):
            started_count = vm_index + 1
            logger.info("Saturation point found at %d guests", started_count)
            break
    util.logger.debug("Stopping the previously started VMs")
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
            util.find(host)
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
    query_hosts = ''
    names = split(names)
    host_count = 0
    for host in names:
        host_count +=1
        util.find(host)
        if host_count == 1:
            query_hosts += "name={0} and status={1}".format(host, states)
        else:
            query_hosts += " or name={0} and status={1}".format(host, states)
  
    try:
        util.waitForQuery(query_hosts, timeout=1200)
    except APITimeout as e:
        logger.error(e)
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

    hostCl = clUtil.find(kwargs.pop('cluster', 'Default'))

    osType ='rhel'
    root_password = kwargs.get('root_password')
    if root_password and positive:
        hostObj = machine.Machine(host_address, 'root', root_password).util('linux')
        hostObj.isConnective(attempt=5, interval=5, remoteCmd=False)
        osType = hostObj.getOsInfo()
        if not osType:
            logger.error("Can't get host %s os info" % name)
            return False

    if osType.lower().find('hypervisor') == -1:
        host = Host(name=name, cluster=hostCl, address=host_address, **kwargs)
        host, status = util.create(host, positive)

        if not wait:
            return status and positive
        if hasattr(host, 'href'):
            return status and util.waitForElemStatus(host, "up", 800)
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

    hostObj = util.find(host)
    hostUpd = Host()

    if 'name' in kwargs:
        hostUpd.set_name(kwargs.pop('name'))
    if 'address' in kwargs:
        hostUpd.set_address(kwargs.pop('address'))
    if 'root_password' in kwargs:
        hostUpd.set_root_password(kwargs.pop('root_password'))

    if 'cluster' in kwargs:
        cl = clUtil.find(kwargs.pop('cluster', 'Default'))
        hostUpd.set_cluster(cl)
    
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
        
    hostObj, status = util.update(hostObj, hostUpd, positive)

    return status


def removeHost(positive,host):
    '''
    Description: remove existed host
    Author: edolinin
    Parameters:
       * host - name of a host to be removed
    Return: status (True if host was removed properly, False otherwise)
    '''

    hostObj = util.find(host)
    return util.delete(hostObj, positive)


def activateHost(positive, host, wait=True):
    '''
    Description: activate host (set status to UP)
    Author: edolinin
    Parameters:
       * host - name of a host to be activated
    Return: status (True if host was activated properly, False otherwise)
    '''
    hostObj = util.find(host)
    status = util.syncAction(hostObj, "activate", positive)

    if status and wait and positive:
        testHostStatus = util.waitForElemStatus(hostObj, "up", 10)
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

    hostObj = util.find(host)
    if not util.syncAction(hostObj, "deactivate", positive):
        return False

    # If state got changed, it may be transitional state so we may want to wait
    # for the final one. If it didn't, we certainly may return immediately.
    hostState = hostObj.get_status().get_state()
    getHostStateAgain = util.find(host).get_status().get_state()
    state_changed = hostState != getHostStateAgain
    if state_changed:
        testHostStatus = util.waitForElemStatus(hostObj, expected_status, 10)
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

    hostObj = util.find(host)
    status = util.syncAction(hostObj, "install", positive,
                             root_password=root_password,
                             override_iptables=override_iptables.lower())
    if not status:
        return False

    return util.waitForElemStatus(hostObj, "up", 800)


def approveHost(positive, host, cluster='Default'):
    '''
    Description: approve host (for ovirt hosts)
    Author: edolinin
    Parameters:
       * host - name of a host to be approved
       * cluster - name of cluster
    Return: status (True if host was approved properly, False otherwise)
    '''

    hostObj = None
    kwargs = {}

    hostObj = util.find(host)
    clusterObj = util.find(cluster)

    kwargs = { 'cluster': clusterObj}
    status = util.syncAction(hostObj, "approve", positive, **kwargs)
    testHostStatus = util.waitForRestElemStatus(hostObj, "up", 120)

    return status and testHostStatus


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
    if validateElementStatus(positive, 'host', host, 'PENDING_APPROVAL'):
        return True

    vdcHostName = getHostName(vdc)
    if not vdcHostName:
        util.logger.error("Can't get hostname from %s" % vdc)

    hostObj = machine.Machine(host, user_name, password).util('linux')
    if not hostObj.isConnective():
        util.logger.error("No connectivity to the host %s" % host)
        return False
    commands = []
    commands.append([SED, '-i', "'s/vdc_host_name=.*/vdc_host_name=" + vdcHostName + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SED, '-i', "'s/nc_host_name=.*/nc_host_name=" + vdc + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SED, '-i', "'s/vdc_host_port=.*/vdc_host_port=" + str(port) + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SERVICE, 'vdsm-reg', "restart"])
    for command in commands:
        res,out = hostObj.runCmd(command)
        if not res:
            util.logger.error("command %s" % " ".join(command))
            util.logger.error(str(out))
            return False

    if not waitForOvirtAppearance(positive, host, attempts=20, interval=3):
        util.logger.error("Host %s doesn't appear!" % host)
        return False

    if not waitForHostsStates(positive, host, states='pending_approval', timeout=timeout):
        util.logger.error("Host %s isn't in PENDING_APPROVAL state" % host)
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

    hostObj = util.find(host)
    return util.syncAction(hostObj, "commitnetconfig", positive)


def fenceHost(positive, host, fence_type):
    '''
    Description: host fencing
    Author: edolinin
    Parameters:
       * host - name of a host to be fenced
       * fence_type - fence action (start/stop/restart/status)
    Return: status (True if host was fenced properly, False otherwise)
    '''

    hostObj = util.find(host)
    status = util.syncAction(hostObj, "fence", positive,
                             fence_type=fence_type.upper())

    # if test type is negative, we don't have to wait for element status,
    # since host state will not be changed
    if status and not positive:
        return True
    testHostStatus = True
    if fence_type == "restart" or fence_type == "start":
        testHostStatus = util.waitForRestElemStatus(hostObj, "up", 500)
    if fence_type == "stop":
        testHostStatus = util.waitForRestElemStatus(hostObj, "down", 300)
    return (testHostStatus and status) == positive


def getHostNic(host, nic):

    hostObj = util.find(host)
    return util.getElemFromElemColl(hostObj, nic, 'nics', 'host_nic')


def attachHostNic(positive, host, nic, network):
    '''
    Description: attach network interface card to host
    Author: edolinin
    Parameters:
       * host - name of a host to attach nic to
       * nic - nic name to be attached
       * network - network name to be used
    Return: status (True if nic was attached properly to host, False otherwise)
    '''

    hostObj = util.find(host)
    cluster = clUtil.find(hostObj.cluster.id, 'id').get_name()
   
    hostNic = getHostNic(host, nic)
    clusterNet = getClusterNetwork(cluster, network)
   
    status = util.syncAction(hostNic, "attach", positive, network=clusterNet)

    return status


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


def updateHostNic(positive, host, nic, network=None, boot_protocol=None,
                  ip=None, netmask=None, bondOptions=None):
    '''
    Description: update nic of host
    Author: atal
    Parameters:
       * host - host where nic should be updated
       * nic - nic name that should be updated
       * network - network name
       * boot_protocol - new boot protocol. could be 'dhcp', 'static' or 'none'
       * ip - new static ip only if boot protocol is static
       * netmask - new netmask but same as ip.
       * bondOptions - new bonding option.
    Return: status (True if nic was updated properly, False otherwise)
    '''

    hostObj = util.find(host)
    cluster = clUtil.find(hostObj.cluster.id, 'id').get_name()
    
    nicObj = getHostNic(host, nic)

    if network:
        net = getClusterNetwork(cluster, network)
        nicObj.set_network(net)
    if boot_protocol:
        nicObj.set_boot_protocol(boot_protocol)
    if ip or netmask:
        nicObj.set_ip(IP(address=ip, netmask=netmask))
   
    # Build up bonding options if needed
    bondOpts = ""
    if bondOptions:
        for option in bondOptions.split(';'):
            optName, optValue = option.split('_')
            # Simple creation of option tag. multiple tags for multiple options
            bondOpts = bondOpts + "<option value='"+optValue.strip()+"' name='"+optName.strip()+"'/>\n"
            # Adding bonding tag only if needed.
            nicObj.bonding.options = bondOpts

    nic,status = util.update(hostObj.link['nics'].href,nicObj.href, nicObj, [201,200,202], positive)

    return status


def detachHostNic(positive, host, nic, network):
    '''
    Description: detach network interface card from host
    Author: edolinin
    Parameters:
       * host - name of a host to attach nic to
       * nic - nic name to be detached
       * network - network name to be used
    Return: status (True if nic was detach properly from host, False otherwise)
    '''
    hostObj = util.find(host)
    clusterObj = clUtil.find(hostObj.cluster.id, 'id')
    nicObj = getHostNic(host, nic)

    # Try to get the network object by his dataCenter id
    # to avoid duplicate network names
    netObjs = util.get(absLink=False)
    for netObj in netObjs:
        if re.match(netObj.get_name(), network, re.I) and \
        re.match(netObj.get_data_center().get_id(), clusterObj.get_data_center().get_id()):
            nicObj.set_network(netObj)
            break
    return util.syncAction(nicObj, "detach", positive, network=nicObj.get_network())


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
    regex = re.compile('\w(\d+)',re.I)
    for net in networks:
        match = regex.search(net)
        if not match:
            return False
        if not detachHostNic(positive,host,nic+'.'+match.group(1),net):
            return False
    return True


def addBond(positive, host, name, slaves, network, bondOptions=None):
    '''
    Description: add bond to a host
    Author: edolinin (maintain by atal)
    Parameters:
       * host - name of a host to attach bond to
       * name - bond name
       * slaves - list of bond slaves separated by comma
       * network - bond network name
       * bondOptions - Bonding options. format: "mode_1;miimon_50,....."
         supported modes are: 1,2,4,5. using underscore due to XML syntax limitations
    Return: status (True if bond was attached properly to host, False otherwise)
    '''

    # find host under hosts link
    hostObj = util.find(links['hosts'], host)
    clusterObj = util.findById(links['clusters'], hostObj.cluster.id)

    # Create host_nic collection
    hostNic = fmt.HostNIC()
    hostNic.name = name

    # Create Bonding Nic Collection
    bondNic = fmt.BondNic()

    # Build up bonding options if needed
    bondOpts = ""
    if bondOptions:
        for option in bondOptions.split(';'):
            optName, optValue = option.split('_')
            # Simple creation of option tag. multiple tags for multiple options
            bondOpts = bondOpts + "<option value='"+optValue.strip()+"' name='"+optName.strip()+"'/>\n"
            # Adding bonding tag only if needed.
            bondNic.options = bondOpts

    # Create network collection
    nicNetwork = fmt.Network()
    nicNetwork.id = util.find(clusterObj.link['networks'].href, network).id

    # Adding network to host_nic
    hostNic.network = nicNetwork

    # Create multiple salves under bonded interface
    nicSlaves = ""
    for slave in slaves.split(","):
        slaveNic = util.find(hostObj.link['nics'].href, slave)
        # Simple creation of multiple slaves
        nicSlaves = nicSlaves + "<host_nic id='" + slaveNic.id + "'/>\n"
    # Adding slaves to main host_nic
    bondNic.slaves = nicSlaves.strip()
    # Adding bond nic to main host_nic
    hostNic.bonding = bondNic

    # incrementNum: the following lines checks if we create vlan over bond
    # or regular bond interface
    # if vlan than the number of nic's will be incremented by 2
    # else incremented by 1
    incrementNum = 1
    if hasattr(util.find(clusterObj.link['networks'].href, network), 'vlan'):
        incrementNum = 2

    bond,status = util.create(hostObj.link['nics'].href, hostNic, positive, incrementBy=incrementNum)

    return status


def genSNNic(nic_name, network_name, by_id=False, boot_proto='none', **ip):
    '''
    generate a host_nic element of types regular or vlaned
    Author: atal
    params:
        * nic_name = name of the physical nic
        * by_id = attach <network> by ID or NAME
        * boot_proto = boot protocol. dhcp, static or none
        * ip = a dictionary for configuring ip.
          {address: '', netmask: '', gateway: ''}
    return True, dict with host nic element.
    '''
    nic_obj = fmt.HostNIC()
    nic_obj.name = nic_name

    nic_obj.network = fmt.Network()
    # TODO: handle by_id condition
    nic_obj.network.name = network_name

    nic_obj.boot_protocol = boot_proto
    if boot_proto.lower() == 'static':
        nic_obj.ip = fmt.IP()
        for k, v in ip.iteritems():
            setattr(nic_obj.ip, k, v)

    return True, {'host_nic': nic_obj.dump()}


def genSNBond(nic_name, network_name, by_id=False, slaves=None, **options):
    '''
    generate a host_nic element of type bond.
    Author: atal
    params:
        * nic_name - name of the physical nic
        * network_name - name of the network
        * by_id - attach <network> by ID or NAME
        * slaves - a list of slaves. ['eth1', 'eth2'].
        * options - dictionary of Bonding options. mode=1, miimon=150 etc'
    return True, dict with host nic element.
    '''
    slaves = slaves or []
    nic_obj = fmt.HostNIC()
    nic_obj.name = nic_name

    nic_obj.network = fmt.Network()
    # TODO: handle by_id condition
    nic_obj.network.name = network_name

    nic_obj.bonding = fmt.BondNic()
    nic_obj.bonding.slaves = ''
    for slave in slaves:
        sl = fmt.HostNIC()
        # TODO: handle by_id
        sl.name = slave
        nic_obj.bonding.slaves += sl.dump()

    nic_obj.bonding.options = ''
    for name, value in options.iteritems():
        nic_obj.bonding.options += '<option name="%s" value="%s" />' % (name, value)

    return True, {'host_nic': nic_obj.dump()}


def sendSNRequest(positive, host_name, host_nics=None, auto_nics=None, **options):
    '''
    send a POST request for <action> after attaching all host_nic
    Author: atal
    params:
        * host_name - a name of the host
        * host_nics - list of 'host_nic' values returned by genSN... functions.
        * auto_nics - a list of nics to collect automatically from the element.
        * options - a dictionary of supported options:
            checkConnectivity=boolean, connectivityTimeout=int, force=boolean
    '''
    host_nics = host_nics or []
    auto_nics = auto_nics or []

    host_obj = util.find(links['hosts'], host_name)
    root = etree.Element('action')
    nics = etree.SubElement(root, 'host_nics')

    for auto_nic in auto_nics:
        try:
            host_nic = util.find(host_obj.link['nics'].href, auto_nic)
        except EntityNotFound:
            continue
        host_nics.append(host_nic.dump())

    for nic in host_nics:
        nic_obj = etree.XML(nic)
        nics.append(nic_obj)

    for key, val in options.iteritems():
        etree.SubElement(root, key).text = val

    return util.syncCollectionAction(host_obj.link['nics'].href + '/setupnetworks',
                                     etree.tostring(root), positive)

def searchForHost(positive, query_key, query_val, key_name=None, expected_count=None):
    '''
    Description: search for a host by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in host object equivalent to query_key,
        required if expected_count is not set
    Return: status (True if expected number of hosts equal to found by search,
    False otherwise)
    '''
    if not expected_count:
        expected_count = 0
        hosts = util.get(absLink=False)

        for host in hosts:
            hostProperty = getattr(host, key_name)
            if re.match(r'(.*)\*$',query_val):
                if re.match(r'^' + query_val, hostProperty):
                    expected_count = expected_count + 1
            else:
                if hostProperty == query_val:
                    expected_count = expected_count + 1

    contsraint = "{0}={1}".format(query_key, query_val)
    query_hosts = util.query(contsraint)
    status = compareCollectionSize(query_hosts, expected_count, util.logger)

    return status


def rebootHost(positive,host,username,password):
    '''
    Description: rebooting host via ssh session
    Author: edolinin
    Parameters:
       * host - name of a host to be rebooted
       * username - user name for ssh session
       * password - password for ssh session
    Return: status (True if host was rebooted properly, False otherwise)
    '''
    hostObj = util.find(host)
    ssh = ssh_session.ssh_session(username, host, password)
    ssh.ssh("reboot")
    return util.waitForRestElemStatus(hostObj, "non_responsive", 180)


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
        util.logger.error("Sending delayed service control command failed. Output: %s",
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
        util.logger.error("Failed to check for service control command result.")
    if int(output[1]) != 0:
        util.logger.error("Last service control command failed.")
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

    hostObj = util.find(host)
    tagObj = Tag(name=tag)
    hostTags = util.getElemFromLink(hostObj, link_name='tags', attr='tag', get_href=True)
    tagObj, status = tagUtil.create(tagObj, positive, collection=hostTags)
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

    hostObj = util.find(host)
    tagObj = util.getElemFromElemColl(hostObj, tag, 'tags', 'tag')
    if tagObj:
        return util.delete(tagObj, positive)
    else:
        util.logger.error("Tag {0} is not found at host {1}".format(tag, host))
        return False

def checkHostStatistics(positive, host):
    '''
    Description: check hosts statistics (existence and format)
    Author: edolinin
    Parameters:
    * host - name of a host
    Return: status (True if all statistics were a success, False otherwise)
    '''

    hostObj = util.find(host)
    expectedStatistics = ['memory.total', 'memory.used', 'memory.free',
            'memory.buffers', 'memory.cached', 'swap.total', 'swap.free',
            'swap.used', 'swap.cached', 'ksm.cpu.current', 'cpu.current.user',
            'cpu.current.system', 'cpu.current.idle', 'cpu.load.avg.5m']

    numOfExpStat = len(expectedStatistics)
    status = True
    statistics = util.getElemFromLink(hostObj, link_name='statistics', attr='statistic')

    for stat in statistics:
        datum =  str(stat.get_values().get_value()[0].get_datum())
        if not re.match('(\d+\.\d+)|(\d+)', datum):
            util.logger.error('Wrong value for ' + stat.get_name() + ': ' + datum)
            status = False
        else:
            util.logger.info('Correct value for ' + stat.get_name() + ': ' + datum)

        if stat.get_name() in expectedStatistics:
            expectedStatistics.remove(stat.get_name())

    if len(expectedStatistics) == 0:
         util.logger.info('All ' + str(numOfExpStat) + ' statistics appear')
    else:
         util.logger.error('The following statistics are missing: ' + str(expectedStatistics))
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
    hostObj = util.find(hostName)

    if not hasattr(hostObj, attribute):
        util.logger.error("Element host" + hostName + " doesn't have attribute " + attribute)
        return False

    util.logger.info("checkHostSpmStatus - SPM Status of host " + hostName + \
                                " is: " + hostObj.get_storage_manager().upper())
    return (hostObj.get_storage_manager().lower() == 'true') == positive


def checkHostSubelementPresence(positive, host, element_path):
    '''
    Checks the presence of element specified by element_path.
    return: True if the host has the tags in path, False otherwise.
    '''

    hostObj = util.find(host)
    actual_tag = hostObj
    path = []
    for subelem_name in element_path.split('.'):
        if not hasattr(actual_tag, subelem_name):
            msg = "Element host %s doesn't have any subelement '%s' at path '%s'."
            util.logger.error(msg % (host, subelem_name, '.'.join(path)))
            return False
        path += (subelem_name,)
        actual_tag = getattr(actual_tag, subelem_name)
    util.logger.info("checkHostAttribute - tag %s in host %s has value '%s'"
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
    queryKey = 'cluster'
    element='host'

    try:
        clusters = clUtil.get(absLink=False)
        dataCenterObj = dcUtil.find(dataCenter)
    except EntityNotFound:
        return False, {'hostName': None}

    clusters = (cl for cl in clusters if hasattr(cl, 'data_center') \
                and cl.get_data_center.id == dataCenterObj.id)
    for cluster in clusters:
        elementStatus, hosts = searchElement(positive, element, queryKey, cluster.name)
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
            "Timeout when waiting for SPM to appear in DC %s."  % datacenter,
    for s in sampler:
        if s[0]:
            return True
 

def getHostNicAttr(positive, host, nic, attr):
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
        hostObj = util.find(links['hosts'], host)
        nicObj = util.find(hostObj.link['nics'].href, nic)
    except EntityNotFound:
        return False, {'attrValue':None}

    for tag in attr.split('.'):
        try:
            nicObj = getattr(nicObj, tag)
        except AttributeError as err:
            logger.error(str(err))
            return False, {'attrValue':None}

    return True, {'attrValue': nicObj}

def countHostNics(positive, host):
    '''
    Count the number of a Host network interfaces
    Author: atal
    Parameters:
       * host - name of a host
    return: True and counter if the function succeeded, otherwise False and None
    '''
    hostObj = util.find(links['hosts'],host)
    nics = util.get(hostObj.link['nics'].href)
    return True, {'nicsNumber':len(nics)}


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
    hosts = util.get(absLink=False)
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
        hostObj = util.find(host)
    except EntityNotFound:
        return False, {'hostCompatibilityVersion' : None}

    clId = hostObj.get_cluster().get_id()
    try:
        clObj = clUtil.find(clId, 'id')
    except EntityNotFound:
        return False, {'hostCompatibilityVersion' : None}
    
    cluster = clObj.get_name()
    status, clCompVer = getClusterCompatibilityVersion(positive, cluster)
    if not status:
        return False, {'hostCompatibilityVersion' : None}
    hostCompatibilityVersion = clCompVer['clusterCompatibilityVersion']
    return True, {'hostCompatibilityVersion' : hostCompatibilityVersion}


def waitForHostNicState(positive, host, nic, state, interval=1, attempts=1):
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
        res, out = getHostNicAttr(positive, host, nic, 'status.state')
        if res and regex.match(out['attrValue']):
            return True
        time.sleep(interval)
        attempts -= 1
    return False

def ifdownNic(positive, host, root_password, nic, wait=True):
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
    hostObj = machine.Machine(getIpAddressByHostName(host), 'root', root_password).util('linux')
    if not hostObj.ifdown(nic):
        return False
    if wait:
        return waitForHostNicState(positive, host, nic, 'down', interval=5, attempts=10)
    return True


def ifupNic(positive, host, root_password, nic, wait=True):
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
    hostObj = machine.Machine(getIpAddressByHostName(host), 'root', root_password).util('linux')
    if not hostObj.ifup(nic):
        return False
    if wait:
        return waitForHostNicState(positive, host, nic, 'up', interval=5, attempts=10)
    return True


def checkIfNicStateIs(positive, host, user, password, nic, state):
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
    hostObj = machine.Machine(getIpAddressByHostName(host), user, password).util('linux')
    regex = re.compile(state, re.I)
    if regex.match(hostObj.getNicState(nic)) is not None:
        return True
    return False


def getOsInfo(positive, host, root_password=''):
    '''
    Description: get OS info wrapper.
    Author: atal
    Parameters:
       * host - name of a new host
       * root_password - password of root user (required, can be empty only for negative tests)
    Return: True with OS info string if succeeded, False and None otherwise
    '''
    hostObj = machine.Machine(host, 'root', root_password).util('linux')
    if not hostObj.isAlive():
        logger.error("No connectivity to the host %s" % host)
        return False, {'osName': None}
    osName = hostObj.getOsInfo()
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
    hostObj = util.find(host)
    status = util.syncAction(hostObj, "install", positive, image=image)

    testHostStatus = util.waitForRestElemStatus(hostObj, "up", 800)
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
        clusterObj = clUtil.find(cluster)
    except Exception as err:
        util.logger.error(err)
        return False, {'clusterCompatibilityVersion' : None}
    clVersion = '{0}.{1}'.format(clusterObj.get_version().get_major(),
                                clusterObj.get_version().get_minor())
    return True, {'clusterCompatibilityVersion' : clVersion}