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
import utilities.postgresConnection as psql
from art.core_api.apis_utils import TimeoutingSampler, data_st
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
import utilities.ssh_session as ssh_session
import re
import tempfile
from utilities.utils import getIpAddressByHostName, getHostName, readConfFile
# TODO: remove both compareCollectionSize, dump_entity is not needed
from art.core_api.validator import compareCollectionSize, dump_entity
from art.rhevm_api.tests_lib.low_level.networks import getClusterNetwork
from art.rhevm_api.tests_lib.low_level.vms import startVm, stopVm, stopVms, startVms,\
    waitForIP
from art.rhevm_api.utils.xpath_utils import XPathMatch, XPathLinks
from art.rhevm_api.utils.test_utils import searchForObj
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler import settings
from art.core_api import is_action
from art.rhevm_api.utils.guest import runLoadOnGuests, runLoadOnGuest
from random import choice

ELEMENT = 'host'
COLLECTION = 'hosts'
HOST_API = get_api(ELEMENT, COLLECTION)
CL_API = get_api('cluster', 'clusters')
DC_API = get_api('data_center', 'datacenters')
TAG_API = get_api('tag', 'tags')
HOST_NICS_API = get_api('host_nic', 'host_nics')
VM_API = get_api('vm', 'vms')
CAP_API = get_api('version', 'capabilities')

xpathMatch = is_action('xpathHosts', id_name='xpathMatch')(XPathMatch(HOST_API))
xpathHostsLinks = is_action('xpathLinksHosts', id_name='xpathHostsLinks')(XPathLinks(HOST_API))

Host = getDS('Host')
Options = getDS('Options')
Option = getDS('Option')
PowerManagement = getDS('PowerManagement')
PmProxyTypes = getDS('PmProxyTypes')
PmProxy=getDS('PmProxy')
PmProxies=getDS('PmProxies')
Agent = getDS('Agent')
Agents = getDS('Agents')
Tag = getDS('Tag')
StorageManager = getDS('StorageManager')

SED = '/bin/sed'
SERVICE = '/sbin/service'
ENUMS = settings.opts['elements_conf']['RHEVM Enums']
RHEVM_UTILS = settings.opts['elements_conf']['RHEVM Utilities']
KSM_STATUSFILE = '/sys/kernel/mm/ksm/run'
HOST_STATE_TIMEOUT=1000
KSMTUNED_CONF = '/etc/ksmtuned.conf'
MEGABYTE = 1024 ** 2
IP_PATTERN = '10.35.*'

virsh_cmd = ['nwfilter-dumpxml', 'vdsm-no-mac-spoofing']
search_for = ["<filterref filter='no-mac-spoofing'/>","<filterref filter='no-arp-mac-spoofing'/>"]

@is_action()
def getRandPM(positive, cluster, size):
    '''
    Description: get all power management types, and create random list of given size.
    Author: alukiano
    Parameters:
      * positive - True
      * cluster -  name of the cluster
      * size - size of list
    Return: Random list with types of power management by given size
    '''
    pm_list = list()
    rand_list = list()
    cluster_obj = CL_API.find(cluster)
    minor_v = cluster_obj.get_version().get_minor()
    major_v = cluster_obj.get_version().get_major()
    cap = CAP_API.get(absLink=False)
    version = [v for v in cap if v.get_major() == major_v and v.get_minor() == minor_v][0]
    for power_manager in version.get_power_managers().get_power_management():
        pm_list.append(power_manager.get_type())
    for i in range(size):
        rand_list.append(choice(pm_list))
    if rand_list:
        return True, {'pmList': rand_list}
    else:
        return False, {'pmList': None}


@is_action()
def measureKSMThreshold(positive, poolname, pool_size, vm_num, host, host_user,
                        host_passwd, guest_user, guest_passwd, vm_mem,
                        loadType, port, load=None, allocationSize=None,
                        protocol=None, clientVMs=None, extra=None,
                        timeout=600):
    '''
    Description: starts VMs until the KSM daemon starts on the host.
    After the KSM is engaged, it shuts down all the started VMs.
    Author: adarazs
    Parameters:
      * poolname - the basename of the pool
      * pool_size - how many VMs are in the pool
      * vm_num - expected KSM threshold
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
    HOST_API.logger.info("Expected threshold is %s", vm_num)
    if checkKSMRun(host, host_user, host_passwd, timeout=10):
        HOST_API.logger.error('KSM is running at the start of the test')
        return False
    status = True
    started_count = 0
    iterations = int(vm_num) + 1 if pool_size > int(vm_num) else int(vm_num)
    for vm_index in range(iterations):
        ksm_timeout = 10 if vm_index < int(vm_num)-2 else 60
        vm_name = "%s-%s" % (poolname, str(vm_index + 1))
        HOST_API.logger.debug('Starting VM: %s', vm_name)
        if not startVm(True, vm_name, wait_for_status=None):
            HOST_API.logger.error('Failed to start VM: %s', vm_name)
        query = "name={0} and status=up or name={0} and status=poweringup".format(vm_name)
        HOST_API.logger.info("Running memory load on VM %s", vm_name)
        VM_API.waitForQuery(query, timeout=timeout, sleep=10)
        load_status = runLoadOnGuest(True, targetVM=vm_name, osType='linux',
                                     username=guest_user,
                                     password=guest_passwd, loadType=loadType,
                                     duration=0, port=port, load=load,
                                     allocationSize=allocationSize,
                                     protocol=protocol, clientVMs=clientVMs,
                                     extra=extra, stopLG=False)
        if not load_status[0]:
            HOST_API.logger.error("Error running load on VM")
            return False
        # time for stats to refresh in the REST API
        HOST_API.logger.debug("Checking if KSM is running on the host")
        if checkKSMRun(host, host_user, host_passwd, timeout=ksm_timeout):
            started_count = vm_index + 1
            HOST_API.logger.info("KSM threshold found at %d guests",
                                 started_count)
            break
        else:
            HOST_API.logger.info("KSM is not running at %d guests", vm_index+1)
    if int(vm_num) == started_count:
        HOST_API.logger.info("Calculated and real threshold equals")
    elif abs(int(vm_num) - started_count) <= 1:
        HOST_API.logger.info("Difference between calculated and "
                             "real threshold is 1.")
    else:
        status = False
        HOST_API.logger.error("Calculated and real threshold differs")
    HOST_API.logger.debug("Stopping the previously started VMs")
    for vm_index in range(started_count):
        vm_name = "%s-%s" % (poolname, str(vm_index + 1))
        if not stopVm(True, vm_name):
            status = False
    return status,{'actual_thres': started_count}


@is_action()
def verifyKSMThreshold(positive, poolname, vm_num, host, host_user,
                       host_passwd, guest_user, guest_passwd, vm_mem,
                       loadType, port, load=None, allocationSize=None,
                       protocol=None, clientVMs=None, extra=None,
                       timeout = 600):
    '''
    Description: starts all of the calculated VMs at once and check if
    it was enough to trigger the KSM routines. Shuts down the started
    VMs after that.
    Author: adarazs
    Parameters:
      * poolname - the basename of the pool
      * vm_num - expected KSM threshold
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
    HOST_API.logger.info("Measured threshold is %s", vm_num)
    if checkKSMRun(host, host_user, host_passwd, timeout=10):
        HOST_API.logger.error('KSM is running at the start of the test')
        return False
    status = True
    vm_list = []
    for vm_index in range(int(vm_num)):
        vm_name = "%s-%s" % (poolname, str(vm_index + 1))
        vm_list.append(vm_name)
    HOST_API.logger.debug('Starting VMs')
    if not startVms(','.join(vm_list)):
        HOST_API.logger.error('Failed to start VMs')
        return False
    query = ' or '.join(['name={0} and status=up or name={0} and status=poweringup'.format(vm_name) for vm_name in vm_list])
    VM_API.waitForQuery(query, timeout=timeout, sleep=10)
    for vm_name in vm_list:
        load_status = runLoadOnGuest(True, targetVM=vm_name, osType='linux',
                                     username=guest_user,
                                     password=guest_passwd, loadType=loadType,
                                     duration=0, port=port, load=load,
                                     allocationSize=allocationSize,
                                     protocol=protocol, clientVMs=clientVMs,
                                     extra=extra, stopLG=False)
        if not load_status[0]:
            HOST_API.logger.error("Error running load on VM")
            return False
    # time for stats to refresh in the REST API
    HOST_API.logger.debug("Checking if KSM is running on the host")
    if checkKSMRun(host, host_user, host_passwd, timeout=60):
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


@is_action()
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
    for vm_index in range(vm_total):
        vm_name = "%s-%s" % (poolname, str(vm_index + 1))
        HOST_API.logger.debug('Starting VM: %s', vm_name)
        if not startVm(True, vm_name, wait_for_status=None):
            HOST_API.logger.error('Failed to start VM: %s', vm_name)
        HOST_API.logger.debug("Waiting for the guest %s to get IP address", vm_name)
        if not waitForIP(vm=vm_name)[0]:
            HOST_API.logger.error("Guest %s did not get IP.", vm_name)
            return False
        load_status = runLoadOnGuest(True, targetVM=vm_name, osType='linux',
                                     username=guest_user,
                                     password=guest_passwd, loadType=loadType,
                                     duration=0, port=port, load=load,
                                     allocationSize=allocationSize,
                                     protocol=protocol, clientVMs=clientVMs,
                                     extra=extra, stopLG=False)
        if not load_status[0]:
            HOST_API.logger.error("Error running load on VM")
            return False
        # time for stats to refresh in the REST API
        time.sleep(10)
        HOST_API.logger.debug("Checking for host saturation")
        if isHostSaturated(host):
            started_count = vm_index + 1
            HOST_API.logger.info("Saturation point found at %d guests", started_count)
            break
    HOST_API.logger.debug("Stopping the previously started VMs")
    for vm_index in range(vm_total):
        vm_name = "%s-%s" % (poolname, str(vm_index + 1))
        stopVm(True, vm_name)
    return status, {"satnum": started_count}


@is_action()
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


@is_action()
def waitForHostsStates(positive, names, states='up', timeout=HOST_STATE_TIMEOUT):
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
        try:
            HOST_API.find(host)
        except EntityNotFound:
            HOST_API.logger.warn("Host %s hasn't been found in system", host)
            return False
        query_host = "name={0} and status={1}".format(host, states)

        if not HOST_API.waitForQuery(query_host, timeout=timeout):
            return False

    return True


def _check_hypervisor(positive, host, cluster):
    """
    Description: Checks if host is already in setup waiting for approval
    Author: jlibosva
    Parameters:
        * host - host to check
        * cluster - eventually which cluster we want host to put in
    Return: positive if host has been approved, False otherwise
    """
    try:
        host = HOST_API.find(host)
    except EntityNotFound:
        return False

    if host.get_status() == \
        ENUMS['search_host_state_pending_approval'] and positive:
        return approveHost(True, host, cluster)
    return False


@is_action()
def addHost(positive, name, wait=True, vdcPort=None, rhel_like=True,
            reboot=True, **kwargs):
    '''
    Description: add new host
    Author: edolinin, jhenner
    Parameters:
       * name - name of a new host
       * root_password - (required, can be empty only for negative tests)
       * address - host IP address, if not provided - fetched from name
       * port - port number
       * cluster - name of the cluster where to attach a new host
       * wait - True if test should wait till timeout or host state to be "UP"
       * vdcPort - default = port parameter, located at settings.conf
       * override_iptables - override iptables. gets true/false strings.
       * rhel_like - for hypervisors only - True will install hypervisor as it
                                            does with rhel
                                          - False will install hypervisor
                                            using vdsm-reg on hypervisor
       * reboot - True - to reboot host after install.
                  False- host won't reboot after install.
    Return: True if host     added and test is    positive,
            True if host not added and test isn't positive,
            False otherwise.
    '''

#TODO: This function needs serious refactoring. (talayan)
    cluster = kwargs.pop('cluster', 'Default')

    if _check_hypervisor(positive, name, cluster):
        return True

    address = kwargs.get('address')
    if not address:
        host_address = getIpAddressByHostName(name)
    else:
        host_address = kwargs.pop('address')

    hostCl = CL_API.find(cluster)

    osType = 'rhel'
    root_password = kwargs.get('root_password')
    if root_password and positive:
        hostObj = machine.Machine(host_address,
                                  'root', root_password).util('linux')
        hostObj.isConnective(attempt=5, interval=5, remoteCmd=False)
        osType = hostObj.getOsInfo()
        if not osType:
            HOST_API.logger.error("Can't get host %s os info" % name)
            return False

    if osType.lower().find('hypervisor') == -1 or rhel_like:
        host = Host(name=name, cluster=hostCl, address=host_address,
                    reboot_after_installation=reboot, **kwargs)
        # cleanup host storage sessions and qemus from previous runs
        # since host are not rebooted
        cleanHostStorageSession(hostObj)
        killProcesses(hostObj, 'qemu')

        host, status = HOST_API.create(host, positive)

        if not wait:
            return status and positive

        if hasattr(host, 'href'):
            return status and HOST_API.waitForElemStatus(host, "up", 800)
        else:
            return status and not positive

    if vdcPort is None:
        vdcPort = settings.opts['port']

    if not installOvirtHost(positive, name, 'root', root_password,
                            settings.opts['host'], vdcPort):
        return False

    return approveHost(positive, name, cluster)


@is_action()
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

    if 'storage_manager_priority' in kwargs:
        new_priority = kwargs.pop('storage_manager_priority')
        sm = StorageManager(new_priority, hostObj.storage_manager.valueOf_)
        hostUpd.set_storage_manager(sm)

    if 'pm' in kwargs:
        pm_address = kwargs.get('pm_address')
        pm_username = kwargs.get('pm_username')
        pm_password = kwargs.get('pm_password')
        pm_port = kwargs.get('pm_port')
        pm_slot = kwargs.get('pm_slot')
        pm_secure = kwargs.get('pm_secure')
        pmOptions = None
        pm_proxies = None

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

        if kwargs.get('pm_proxies'):
            pm_proxies_list = [PmProxy(type_=proxy) for proxy \
                                                    in kwargs.get('pm_proxies')]
            pm_proxies = PmProxies(pm_proxy=pm_proxies_list)

        if kwargs.get('agents'):
            agents_array = []
            agents = None
            use_agents = kwargs.get('agents')
            for pm_agent_type   , pm_agent_addr, pm_agent_usr \
              , pm_agent_passwd , pm_agent_opts, pm_agent_concurrent \
              , pm_agent_order \
              in use_agents:
                agent_obj = Agent(type_=pm_agent_type            \
                                , address=pm_agent_addr          \
                                , username=pm_agent_usr          \
                                , password=pm_agent_passwd       \
                                , options=pm_agent_opts          \
                                , concurrent=pm_agent_concurrent \
                                , order=pm_agent_order)
                agents_array.append(agent_obj)
                agents = Agents(agent=agents_array)

        if kwargs.get('agents') and kwargs.get('pm_proxies'):
            hostPm = PowerManagement(type_=kwargs.get('pm_type') \
                                   , address=pm_address          \
                                   , enabled=kwargs.get('pm')    \
                                   , username=pm_username        \
                                   , password=pm_password        \
                                   , options=pmOptions           \
                                   , pm_proxies=pm_proxies       \
                                   , agents=agents)
        else:
             hostPm = PowerManagement(type_=kwargs.get('pm_type')\
                                    , address=pm_address         \
                                    , enabled=kwargs.get('pm')   \
                                    , username=pm_username       \
                                    , password=pm_password       \
                                    , options=pmOptions)

        hostUpd.set_power_management(hostPm)

    hostObj, status = HOST_API.update(hostObj, hostUpd, positive)

    return status


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
def installHost(positive, host, root_password,
                iso_image=None, override_iptables='false'):
    '''
    Description: run host installation
    Author: edolinin, atal
    Parameters:
       * host - name of a host to be installed
       * root_password - password of root user
       * iso_image - iso image for rhevh installation
       * override_iptables - override iptables. gets true/false strings.
    Return: status (True if host was installed properly, False otherwise)
    '''

    hostObj = HOST_API.find(host)
    status = HOST_API.syncAction(hostObj, "install", positive,
                                 root_password=root_password,
                                 image=iso_image,
                                 override_iptables=override_iptables.lower())
    if not status:
        return False

    return HOST_API.waitForElemStatus(hostObj, "up", 800)


@is_action()
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
    clusterObj = CL_API.find(cluster)

    kwargs = {'cluster': clusterObj}
    status = HOST_API.syncAction(hostObj, "approve", positive, **kwargs)
    testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 120)

    return status and testHostStatus


# FIXME: need to rewrite this def because new ovirt approval has been changed
@is_action()
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
    if waitForHostsStates(positive, host,
                          ENUMS['search_host_state_pending_approval']):
        return True

    vdcHostName = getHostName(vdc)
    if not vdcHostName:
        HOST_API.logger.error("Can't get hostname from %s" % vdc)

    hostObj = machine.Machine(host, user_name, password).util('linux')
    if not hostObj.isConnective():
        HOST_API.logger.error("No connectivity to the host %s" % host)
        return False
    commands = []
    commands.append([SED, '-i',
                    "'s/vdc_host_name[[:space:]]*=.*/vdc_host_name = " +
                    vdcHostName + "/'", "/etc/vdsm-reg/vdsm-reg.conf",
                    '--copy'])
    commands.append([SED, '-i',
                     "'s/nc_host_name[[:space:]]*=.*/nc_host_name = " +
                     vdc + "/'", "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([SED, '-i',
                     "'s/vdc_host_port[[:space:]]*=.*/vdc_host_port = " +
                     str(port) + "/'", "/etc/vdsm-reg/vdsm-reg.conf",
                     '--copy'])
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

    if not waitForHostsStates(positive, host,
                       states=ENUMS['search_host_state_pending_approval']):
        HOST_API.logger.error("Host %s isn't in PENDING_APPROVAL state" % host)
        return False

    return True


@is_action()
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


@is_action()
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

    if 'vlan' in kwargs:
        nic_obj.set_vlan(data_st.VLAN(id=kwargs.get('vlan')))
        name = '{0}.{1}'.format(kwargs.get('name'), kwargs.get('vlan'))
        kwargs.update([('name', name)])

    if 'name' in kwargs:
        nic_obj.set_name(kwargs.get('name'))

    if 'network' in kwargs:
        nic_obj.set_network(data_st.Network(name=kwargs.get('network')))

    if 'boot_protocol'in kwargs:
        nic_obj.set_boot_protocol(kwargs.get('boot_protocol'))

    if 'override_configuration' in kwargs:
        nic_obj.set_override_configuration(kwargs.get('override_configuration'))

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
            for nic in slave_list:
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


def getHostNicsAction(host):

    host_obj = HOST_API.find(host)
    return HOST_API.getElemFromLink(host_obj, 'nics', 'actions', get_href=False)


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
@is_action()
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
            if not any(hostNic for hostNic in hostNicsNetworksMapper(host).keys() if re.search('%s\.\d' % (nic), hostNic)):
                return True, {'freeNic': nic}
    return False, {'freeNic': None}


@is_action()
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


@is_action()
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


@is_action()
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
@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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

    nics_obj = HOST_API.get(href=getHostNics(host))

    for nic in auto_nics:
        nics.append(getHostNic(host, nic))

    return HOST_NICS_API.syncAction(nics_obj, "setupnetworks", positive,
                                    host_nics=data_st.HostNics(host_nic=nics),
                                    **kwargs)


@is_action()
def isSyncNetwork(host, nic):
    '''
    Description: Validating if Network sync.
    Author: atal
    Parameters:
        * host - host name
        * nic - nic name
    Return: return True if network sync else False
    '''
    nic_obj = getHostNic(host, nic)
    return nic_obj.get_custom_configuration()


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
def returnSPMHost(hosts):
    '''
    Description: get SPM host from the list of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    '''
    for host in hosts.split(','):
        if checkHostSpmStatus(True, host):
            return True, {'spmHost': host}
    return False, {'spmHost': None}


@is_action()
def getAnyNonSPMHost(hosts):
    '''
    Description: get any not SPM host from the list of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    '''
    for host in hosts.split(','):
        if not checkHostSpmStatus(True, host):
            return True, {'hsmHost': host}
    return False, {'hsmHost': None}


@is_action()
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


@is_action()
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


@is_action()
def setSPMPriorityInDB(positive, hostName, spm_priority, ip, user, password):
    '''
    Description: set SPM priority for host in DB
    Author: pdufek
    Parameters:
    * hostName - the name of the host
    * spm_priority - SPM priority to be set for host
    * ip - IP of the machine where DB resides
    * user - username for remote access
    * password - password for remote access
    Returns: True (successfully set) / False (failure)
    '''
    cmd = 'psql engine postgres -c \"UPDATE vds_static SET ' \
          'vds_spm_priority=\'%s\' WHERE vds_name=\'%s\';\"' \
          % (spm_priority, hostName)
    status = runMachineCommand(bool(True), ip=ip, user=user, password=password,
                               cmd=cmd)
    if not status[0]:
        log_fce = HOST_API.logger.error if (positive is not None) and positive \
                                        else HOST_API.logger.info
        log_fce('Command \'%s\' failed: %s' % (cmd, status[1]['out']))
    return status[0] == positive


@is_action()
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


@is_action()
def checkHostsForSPM(positive, hosts, expected_spm_host):
    '''
    Description: checks whether SPM is expected host or not
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    * expected_spm_host - host which should be SPM
    Returns: True (success - SPM is expected host) / False (failure)
    '''
    for host in hosts.split(','):
        if checkHostSpmStatus(bool(True), host):
            return (host == expected_spm_host) == positive


@is_action()
def checkSPMPresence(positive, hosts):
    '''
    Description: checks whether SPM is set within the set of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: True (success - SPM is present on any host from list)
             False (failure - SPM not present)
    '''
    for host in hosts.split(','):
        if checkHostSpmStatus(bool(True), host):
            return positive
    else:
        return not(positive)


@is_action()
def checkSPMElectionRandomness(positive, hosts, attempt_number=5, spm_priority='1'):
    '''
    Description: checks whether SPM host is being chosen randomly when hosts
                 have the same SPM priority
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be gone through
    * attempt_number - the number of runs to check election randomness
    * spm_priority - SPM priority to be set to all hosts for this test
    Returns: True (success - SPM host is being chosen randomly)
             False (failure)
    '''
    hosts_pairs = {}
    for host in hosts.split(','):
        setSPMPriority(bool(True), host, spm_priority)
    deactivateHosts(bool(True), hosts)

    hosts = sorted(hosts.split(','))
    for host in hosts:
        running_hosts = hosts[:]
        running_hosts.remove(host)
        activation_order = running_hosts[:]
        activation_order.insert(0, host)
        running_hosts = tuple(running_hosts)

        for i in xrange(attempt_number):
            for h in activation_order:
                activateHost(bool(True), h)
            time.sleep(45) # waiting due to SPM contending
            deactivateHost(bool(True), host)
            time.sleep(45)
            try:
                spm = _getSPMHostname(running_hosts)
            except EntityNotFound, e:
                HOST_API.logger.error(e.message)
                return False
            if running_hosts not in hosts_pairs:
                hosts_pairs[running_hosts] = [spm]
            else:
                hosts_pairs[running_hosts].append(spm)
            deactivateHosts(bool(True), ','.join(running_hosts))

    status = True
    for spms in hosts_pairs.keys():
        if not len(set(spms)) > 1:
            logger.warning("SPM randomness test failed, but due to the nature" \
                           "of this test, there's a small chance of that" \
                           "happening at every run")
            status = False

    return status == positive


def _getSPMHostname(hosts):
    '''
    Description: get SPM host from the list of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: hostName (success) / raises EntityNotFound exception
    '''
    for host in hosts:
        if checkHostSpmStatus(bool(True), host):
            return host
    else:
        raise EntityNotFound('SPM not found among these hosts: %s' \
                             % (str(hosts),))


@is_action()
def deactivateHosts(positive, hosts):
    '''
    Description: deactivates the set of hosts. If host deactivation is not
                 successful, waits 30 seconds before the second attempt
                 - due to possible contending for SPM
    Author: pdufek
    Parameters:
    * hosts - hosts to be deactivated
    Returns: True (success) / False (failure)
    '''
    for host in hosts.split(','):
        status = deactivateHost(bool(True), host)
        if not status:
            time.sleep(30)
            status2 = deactivateHost(bool(True), host)
            return status2 == positive
    return True == positive


@is_action()
def reactivateHost(positive, host):
    '''
    Description: reactivates host (puts it to 'Maintenance' state first,
                 then to 'UP' state)
    Author: pdufek
    Parameters:
    * host - the name of the host to be reactivated
    Returns: True (success) / False (failure)
    '''
    status = deactivateHost(bool(True), host)
    if status:
        status = activateHost(bool(True), host)
    return status == positive


@is_action()
def getSPMHost(hosts):
    '''
    Description: get SPM host from the list of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: hostName (success) / raises EntityNotFound exception
    '''
    for host in hosts:
        if checkHostSpmStatus(bool(True), host):
            return host
    else:
        raise EntityNotFound('SPM not found among these hosts: %s' \
                             % (str(hosts),))


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
def waitForHostPmOperation(positive, host, vdc='localhost', dbuser='postgres',
                        dbpassword='postgres', dbname='engine'):
    '''
    Description: Wait for next PM operation availability
    Author: lustalov
    Parameters:
        * host - vds host name
        * vdc - vdc host name/IP
        * dbuser - vdc database username
        * dbname - vdc database name
    Return: True if success, False otherwise
    '''
    timeToWait = 0
    returnVal = True
    dbConn = psql.Postgresql(host=vdc, user=dbuser, password=dbpassword, dbname=dbname)
    try:
        dbConn.connect()
        sql = "select option_value from vdc_options \
            where option_name = 'FenceQuietTimeBetweenOperationsInSec';"
        res = dbConn.query(sql)
        waitSec = res[0][0]
        events = ['USER_VDS_STOP', 'USER_VDS_START', 'USER_VDS_RESTART']
        for event in events:
            sql = "select get_seconds_to_wait_before_pm_operation('{0}','{1}',{2});".\
                format(host, event, waitSec)
            res = dbConn.query(sql)
            timeSec = int(res[0][0])
            if timeSec > timeToWait:
                timeToWait = timeSec
    except Exception as ex:
        HOST_API.logger.error('Failed to get wait time before host %s \
            PM operation: %s' % (host, ex))
        returnVal = False
    finally:
        dbConn.close()
    if timeToWait > 0:
        HOST_API.logger.info('Wait %d seconds until PM operation will be permitted.' % timeToWait)
        time.sleep(timeToWait)
    return returnVal

@is_action()
def checkKSMRun(host, host_user, host_passwd, timeout=120, sleep=1):
    '''
    Description: Samples KSM run file every few seconds, telling if
    KSM is running or not
    Author: ibegun
    Parameters:
      * host - name of the host
      * host_user - user name for the host
      * host_passwd - password for the user
    Return: True if KSM is running, False otherwise
    '''
    starttime = time.time()
    HOST_API.logger.info('Checking if KSM is running: checking every {0} seconds, for {1} seconds.'.format(str(sleep), str(timeout)))
    host_obj = machine.Machine(host, host_user, host_passwd).util('linux')
    while (time.time() - starttime < timeout):
        output = host_obj.runCmd(['cat', KSM_STATUSFILE])
        if not output[0]:
            HOST_API.logger.error("Can't read '/sys/kernel/mm/ksm/run' on %s", host)
            return False
    # check if there's a 1 or a 0 in the file
        match_obj = re.search('([01])[\n\r]*$', output[1])
        status = match_obj.group(1) == '1'
        if status:
            HOST_API.logger.info('KSM is running.')
            return True
        else:
            time.sleep(sleep)
    HOST_API.logger.info('KSM is not running.')
    return False

@is_action()
def checkNetworkFiltering(positive, host, user, passwd):
    '''
    Description: Check that network filtering is enabled via VDSM
                 This function is also described in tcms_plan 6955
                 test_case 198901
    Author: awinter
    Parameters:
      * host - name of the host
      * user - user name for the host
      * passwd - password for the user
    return: True if network filtering is enabled, False otherwise
    '''

    host_obj = machine.Machine(host,user,passwd).util('linux')
    if host_obj.runVirshCmd(['nwfilter-list'])[1].count("vdsm-no-mac-spoofing") != 1:
        HOST_API.logger.error("nwfilter-list does not have 'vdsm-no-mac-spoofing'")
        return not positive
    if not host_obj.isFileExists(RHEVM_UTILS['NWFILTER_DUMPXML']):
        HOST_API.logger.error("vdsm-no-mac-spoofing.xml file not found")
        return not positive
    if not checkNWFilterVirsh(host_obj):
        return not positive
    if not host_obj.removeFile(RHEVM_UTILS['NWFILTER_DUMPXML']):
        HOST_API.logger.error("Deletion failed")
        return not positive
    if not host_obj.restartService("vdsmd"):
        HOST_API.logger.error("restarting vdsm failed")
        return not positive
    time.sleep(30)
    if not checkNWFilterVirsh(host_obj):
        return not positive
    return positive

def checkNWFilterVirsh(host_obj):
    '''
    Description: Checking that NWfilter is enable in dumpxml and in virsh
    Author: awinter
    Parameters:
      * host_obj - the host's object
    return: True if all the elements were found, False otherwise
    '''
    NOT_FOUND = -1

    xml_file = tempfile.NamedTemporaryFile()
    if not host_obj.copyFrom(RHEVM_UTILS['NWFILTER_DUMPXML'], xml_file.name):
        HOST_API.logger.error("Coping failed")
        return False
    with xml_file as f:
        tmp_file = f.read().strip()
        for string in search_for:
            if (tmp_file.find(string) == NOT_FOUND) or \
                    (host_obj.runVirshCmd(virsh_cmd)[1].count(string) != 1):
                HOST_API.logger.error("nwfilter tags weren't found in file")
                return False
    return True

@is_action()
def checkNetworkFilteringDumpxml(positive, host, user, passwd, vm, nics):
    '''
    Description: Check that network filtering is enabled via dumpxml
                 This function is also described in tcms_plan 6955
                 test_case 198914
    Author: awinter
    Parameters:
      * host - name of the host
      * user - user name for the host
      * passwd - password for the user
      * vm - name of the vm
      * nics - number nics for vm in dumpxml
    return: True if network filtering is enabled, False otherwise
    '''
    host_obj = machine.Machine(host,user,passwd).util('linux')
    res, out = host_obj.runVirshCmd(['dumpxml', '%s' %vm])
    if not out.count("<filterref filter='vdsm-no-mac-spoofing'/>") == int(nics):
        return not positive
    return positive

@is_action()
def checkNetworkFilteringEbtables(positive, host, user, passwd, nics, vm_macs):
    '''
    Description: Check that network filtering is enabled via ebtables
                 This function is also described in tcms_plan 6955
                 test_case 198920
    Author: awinter
    Parameters:
      * host - name of the host
      * user - user name for the host
      * passwd - password for the user
      * nics - number of nics
      * vm_macs - list of vms' macs
    return: True if network filtering is enabled, False otherwise
    '''
    count = 0
    macTemplate = re.compile('([0-9a-f]+[:]){5}[0-9a-f]+', re.I)
    host_obj = machine.Machine(host,user,passwd).util('linux')
    cmd = ['ebtables', '-t', 'nat', '-L']
    output = (host_obj.runCmd(cmd)[1].strip()).splitlines()
    for line in output:
        line_list = line.split()
        mac_addr = [word for word in line_list if re.match(macTemplate, "0" + word)]
        if mac_addr:
            mac = "0" + mac_addr[0]
            if mac in vm_macs:
                count = count + 1
            else:
                HOST_API.logger.error("Mac not found in ebtables")
                return not positive
    if count != 2 * int(nics):
        return not positive
    return positive


@is_action()
def getKSMStats(positive, host, host_user, host_passwd, vm_num, mem_ovrcmt,
                ksm_const, ksm_coeff):
    '''
    Gather information from the host in order to trigger KSM on host with
    given number of VM's.

    **Author**: ibegun

    **Parameters**:
        * *host* - IP of host
        * *host_user* - user name for the host
        * *host_passwd* - password for the user
        * *vm_num* - exptected VM threshold
        * *mem_ovrcmt* - cluster's memory overcommit policy (100, 150 or 200)
        * *ksm_const* - default value for KSM threshold const
        * *ksm_coeff* - default value for KSM threshold coefficient

    **Returns**: On success, returns information for triggering KSM on host
    with given number of VM's. Otherwise, returns False.
    '''
    stats = getStat(host, ELEMENT, COLLECTION, ['memory.total', 'memory.free'])
    total_mem = stats['memory.total']
    free_mem = stats['memory.free']
    vm_mem = (((free_mem + int(vm_num) - 1) / int(vm_num)) / MEGABYTE)\
             * MEGABYTE
    pool_size = (int(vm_num) * int(mem_ovrcmt) + 99) / 100
    # let's find out the thresholds for KSM on the host and default to
    # the known defaults if there are no custom settings
    host_obj = machine.Machine(host, host_user, host_passwd).util('linux')
    ksmtuned_output = host_obj.runCmd(['cat', KSMTUNED_CONF])
    if ksmtuned_output[0] is False:
        HOST_API.logger.error("Can't read {0}".format(KSMTUNED_CONF))
        return False
    match_obj = re.search('[^#]*\W*KSM_THRES_COEF=([0-9]+)',
                          ksmtuned_output[1])
    if match_obj is not None:
        ksm_thres_coeff = int(match_obj.group(1))
    else:
        ksm_thres_coeff = ksm_coeff
    match_obj = re.search('[^#]*\W*KSM_THRES_CONST=([0-9]+)',
                          ksmtuned_output[1])
    if match_obj is not None:
        ksm_thres_const = int(match_obj.group(1)) * MEGABYTE
    else:
        ksm_thres_const = ksm_const
    if (total_mem * (ksm_thres_coeff/100) > ksm_thres_const):
        vm_load = int(((100 - ksm_thres_coeff) / 100.0) * vm_mem)
    else:
        vm_load = int(((total_mem - ksm_thres_const) / float(total_mem))\
                      * vm_mem)
    vm_load = int(vm_load / MEGABYTE + 0.5)
    return True, {'vm_mem': vm_mem, 'vm_load': vm_load,
                  'pool_size': pool_size}


def cleanHostStorageSession(hostObj, **kwargs):
    '''
    Description: Runs few commands on a given host to clean storage related
                 session and dev maps.
    **Author**: talayan
    **Parameters**:
      **hostObj* - Object represnts the hostObj
    '''
#   check if there is an active session
    check_iscsi_active_session = ['iscsiadm', '-m', 'session']
    HOST_API.logger.info("Run %s to check if there are active iscsi sessions"
                         % " ".join(check_iscsi_active_session))
    res, out = hostObj.runCmd(check_iscsi_active_session)
    if not res:
        HOST_API.logger.info("Run %s Res: %s",
                             " ".join(check_iscsi_active_session), out)
        return

    HOST_API.logger.info("There are active session, perform clean and logout")

    commands = [['iscsiadm', '-m', 'session', '-u'],
                ['multipath', '-F'],
                ['dmsetup', 'remove_all']]

    for cmd in commands:
        HOST_API.logger.info("Run %s" % " ".join(cmd))
        res, out = hostObj.runCmd(cmd)
        if not res:
            HOST_API.logger.info(str(out))

def killProcesses(hostObj, procName, **kwargs):
    '''
    Description: pkill procName

    **Author**: talayan
    **Parameters**:
      **hostObj* - Object represnts the hostObj
      **procName* - process to kill
    '''
#   check if there is zombie qemu proccess
    pgrep_proc = ['pgrep', procName]
    HOST_API.logger.info("Run %s to check there are running processes.."
                         % " ".join(pgrep_proc))
    res, out = hostObj.runCmd(pgrep_proc)
    if not res:
        HOST_API.logger.info("Run %s Res: %s",
                             " ".join(pgrep_proc), out)
        return

    HOST_API.logger.info("performing: pkill %s" % procName)

    pkill_proc = ['pkill', procName]

    HOST_API.logger.info("Run %s" % " ".join(pkill_proc))
    res, out = hostObj.runCmd(pkill_proc)
    if not res:
        HOST_API.logger.info(str(out))
