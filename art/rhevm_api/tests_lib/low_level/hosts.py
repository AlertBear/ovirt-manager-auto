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

import time
import shlex
import json
import re
import tempfile

from utilities.utils import getIpAddressByHostName, getHostName
from utilities import machine

from art.core_api.apis_utils import TimeoutingSampler, data_st
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from art.core_api.apis_utils import getDS
from art.core_api import is_action

from art.test_handler import find_test_file
from art.test_handler import settings

from art.rhevm_api.utils.test_utils import get_api, split, getStat, \
    searchElement, searchForObj, stopVdsmd, startVdsmd
from art.rhevm_api.tests_lib.low_level.networks import getClusterNetwork, \
    create_properties
from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.vms import stopVm, getVmHost, \
    get_vm_state
from art.rhevm_api.utils.xpath_utils import XPathMatch, XPathLinks
from art.rhevm_api.utils.resource_utils import runMachineCommand

ELEMENT = 'host'
COLLECTION = 'hosts'
HOST_API = get_api(ELEMENT, COLLECTION)
CL_API = get_api('cluster', 'clusters')
DC_API = get_api('data_center', 'datacenters')
TAG_API = get_api('tag', 'tags')
HOST_NICS_API = get_api('host_nic', 'host_nics')
VM_API = get_api('vm', 'vms')
CAP_API = get_api('version', 'capabilities')
EVENT_API = get_api("event", "events")
xpathMatch = is_action('xpathHosts',
                       id_name='xpathMatch')(XPathMatch(HOST_API))
xpathHostsLinks = is_action('xpathLinksHosts',
                            id_name='xpathHostsLinks')(XPathLinks(HOST_API))

Host = getDS('Host')
Options = getDS('Options')
Option = getDS('Option')
PowerManagement = getDS('PowerManagement')
PmProxyTypes = getDS('PmProxyTypes')
PmProxy = getDS('PmProxy')
PmProxies = getDS('PmProxies')
Agent = getDS('Agent')
Agents = getDS('Agents')
Tag = getDS('Tag')
StorageManager = getDS('StorageManager')

SED = '/bin/sed'
SERVICE = '/sbin/service'
ENUMS = settings.opts['elements_conf']['RHEVM Enums']
RHEVM_UTILS = settings.opts['elements_conf']['RHEVM Utilities']
KSM_STATUSFILE = '/sys/kernel/mm/ksm/run'
HOST_STATE_TIMEOUT = 1000
KSMTUNED_CONF = '/etc/ksmtuned.conf'
MEGABYTE = 1024 ** 2
IP_PATTERN = '10.35.*'
TIMEOUT = 120
FIND_QEMU = 'ps aux |grep qemu | grep -e "-name %s"'
MOM_CONF = '/etc/vdsm/mom.conf'
MOM_SCRIPT_LOCAL = 'tests/rhevmtests/mom/momStats.py'
MOM_SCRIPT_PATH = '/tmp/momStats.py'

virsh_cmd = ['nwfilter-dumpxml', 'vdsm-no-mac-spoofing']
search_for = ["<filterref filter='no-mac-spoofing'/>",
              "<filterref filter='no-arp-mac-spoofing'/>"]


class HostObject(object):
    def __init__(self, name, password, ip=None, nics=None, user="root"):
        self.name = name
        self.user = user
        self.password = password
        self.ip = ip
        self.nics = nics
        if self.ip is None:
            self.ip = getHostIP(self.name)
        self.up_nics = []
        if self.nics is None:
            all_nics = getHostNicsList(self.name)
            self.nics = sorted([x.get_name() for x in all_nics])
            self.up_nics = [
                x.get_name() for x in all_nics
                if x.get_status().get_state() == 'up']


def get_host_list():
    hostUtil = get_api('host', 'hosts')
    return hostUtil.get(absLink=False)


def isHostSaturated(host, max_cpu=95, max_mem=95):
    """
    Description: checks if the host if saturated with VMs
    Author: adarazs
    Parameters:
      * host - name of a host
    Return: status (True if the host is saturated, False otherwise)
    """
    HOST_API.find(host)
    stats = getStat(host, ELEMENT, COLLECTION, ["memory.used", "memory.total",
                                                "cpu.current.system",
                                                "cpu.current.user"])
    cpu_sum = stats["cpu.current.system"] + stats["cpu.current.user"]
    mem_percent = stats["memory.used"] / float(stats["memory.total"]) * 100.0
    if cpu_sum > max_cpu or mem_percent > max_mem:
        if cpu_sum > max_cpu:
            HOST_API.logger.info("Host %s reached the CPU saturation point",
                                 host)
        else:
            HOST_API.logger.info("Host %s reached the memory saturation point",
                                 host)
        return True
    return False


def getHostState(host):
    """
    Description: Returns a host's state
    Author: cmestreg
    Parameters:
        * host - host to check
    Return: Returns the host's states [str] or raises EntityNotFound
    """
    return HOST_API.find(host).get_status().get_state()


def getHostIP(host):
    """
    Description: Returns IP of a host with given name in RHEVM
    Parameters:
        * host - host name in rhevm to check
    Return: Returns the host IP [str] or raises EntityNotFound
    """
    return HOST_API.find(host).get_address()


def getHostCluster(host):
    """
    Description: Returns name of cluster with given host
    Parameters:
        * host - host name in rhevm to check
    Return: Returns the cluster name [str] or raises EntityNotFound
    """
    host_obj = HOST_API.find(host)
    cluster = CL_API.get(host_obj.get_cluster().get_href())
    return cluster.get_name()


def getHostDC(host):
    """
    Description: Returns name of data center with given host
    Parameters:
        * host - host name in rhevm to check
    Return: Returns the data center name [str] or raises EntityNotFound
    """
    HOST_API.logger.info("Host: %s", host)
    cl_name = getHostCluster(host)
    cl_obj = CL_API.find(cl_name)
    dc = DC_API.get(cl_obj.get_data_center().get_href())
    return dc.get_name()


def isHostUp(positive, host):
    """
    Description: Checks if host is up
    Author: cmestreg
    Parameters:
        * host - host to check
    Return: positive if host is up, False otherwise
    """
    try:
        host_status = getHostState(host)
    except EntityNotFound:
        return False

    if (host_status == ENUMS['host_state_up']) == positive:
        return True
    return False


@is_action()
def waitForOvirtAppearance(positive, host, attempts=10, interval=3):
    """
    Wait till ovirt host appears in rhevm.
    Author: atal
    parameters:
    host - name of the host
    attempts - number of tries
    interval - wait between tries
    return True/False
    """
    while attempts:
        try:
            HOST_API.find(host)
            return True
        except EntityNotFound:
            attempts -= 1
            time.sleep(interval)
    return False


@is_action()
def waitForHostsStates(positive, names, states='up',
                       timeout=HOST_STATE_TIMEOUT,
                       stop_states=[ENUMS['host_state_install_failed']]):
    """
    Wait until all of the hosts identified by names exist and have the desired
    status declared in states.
    Parameters:
        * names - A comma separated names of the hosts with status to wait for.
        * states - A state of the hosts to wait for.
    Author: talayan
    """

    list_names = split(names)
    [HOST_API.find(host) for host in list_names]
    number_of_hosts = len(list_names)

    sampler = TimeoutingSampler(timeout, 10, HOST_API.get, absLink=False)

    try:
        for sample in sampler:
            ok = 0
            for host in sample:
                if host.name in names:
                    if host.status.state in stop_states:
                        HOST_API.logger.error("Host state: %s",
                                              host.status.state)
                        return False
                    elif host.status.state == states:
                        ok += 1
                    if ok == number_of_hosts:
                        return True

    except APITimeout:
        HOST_API.logger.error("Timeout waiting for all hosts in state %s",
                              states)
        return False


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

    if host.get_status() == ENUMS['search_host_state_pending_approval'] and \
            positive:
        return approveHost(True, host, cluster)
    return False


@is_action()
def addHost(positive, name, wait=True, vdcPort=None, rhel_like=True,
            reboot=True, **kwargs):
    """
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
       * protocol - vdsm trasport protocol (stomp / xml)
    Return: True if host     added and test is    positive,
            True if host not added and test isn't positive,
            False otherwise.
    """

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

    hostObj = None

    if kwargs.get('protocol') is None:
        # check whether configuration requires specific transport protocol
        transport_proto = settings.opts.get('vdsm_transport_protocol')
        if transport_proto is not None:
            HOST_API.logger.info(
                "Setting vdsm_transport_protocol = %s explicitly",
                transport_proto
            )
            kwargs['protocol'] = transport_proto

    kwargs.setdefault('override_iptables', 'true')

    if root_password:
        hostObj = machine.Machine(host_address, 'root',
                                  root_password).util(machine.LINUX)
    if positive:
        hostObj.isConnective(attempt=5, interval=5, remoteCmd=False)
        osType = hostObj.getOsInfo()
        if not osType:
            HOST_API.logger.error("Can't get host %s os info" % name)
            return False

    if osType.lower().find('hypervisor') == -1 or rhel_like:
        host = Host(name=name, cluster=hostCl, address=host_address,
                    reboot_after_installation=reboot, **kwargs)

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
    """
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
    """

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
        sm = StorageManager(new_priority,
                            hostObj.storage_manager.get_valueOf_())

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

        if pm_port or pm_secure or pm_slot:
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
            pm_proxies_list = [PmProxy(type_=proxy) for proxy
                               in kwargs.get('pm_proxies')]
            pm_proxies = PmProxies(pm_proxy=pm_proxies_list)

        if kwargs.get('agents'):
            agents_array = []
            agents = None
            use_agents = kwargs.get('agents')
            for pm_agent_type, pm_agent_addr, pm_agent_usr, pm_agent_passwd, \
                pm_agent_opts, pm_agent_concurrent, pm_agent_order in \
                    use_agents:
                agent_obj = Agent(type_=pm_agent_type, address=pm_agent_addr,
                                  username=pm_agent_usr,
                                  password=pm_agent_passwd,
                                  options=pm_agent_opts,
                                  concurrent=pm_agent_concurrent,
                                  order=pm_agent_order)
                agents_array.append(agent_obj)
                agents = Agents(agent=agents_array)

        if kwargs.get('agents') and kwargs.get('pm_proxies'):
            hostPm = PowerManagement(type_=kwargs.get('pm_type'),
                                     address=pm_address,
                                     enabled=kwargs.get('pm'),
                                     username=pm_username,
                                     password=pm_password,
                                     options=pmOptions, pm_proxies=pm_proxies,
                                     agents=agents)
        else:
            hostPm = PowerManagement(type_=kwargs.get('pm_type'),
                                     address=pm_address,
                                     enabled=kwargs.get('pm'),
                                     username=pm_username,
                                     password=pm_password, options=pmOptions)
        hostUpd.set_power_management(hostPm)

    try:
        hostObj, status = HOST_API.update(hostObj, hostUpd, positive)
    except TypeError:
        # TypeError expected on all backends except REST for negative cases
        # when passing wrong parameter type due to type-checking
        if not positive:
            return True
        # if this is not a negative case, continue raising exception upwards
        else:
            raise

    return status


@is_action()
def removeHost(positive, host, deactivate=False):
    """
    Description: remove existed host
    Author: edolinin
    Parameters:
       *  *host* - name of a host to be removed
       *  *deactivate* - Flag to put host in maintenance before remove
    Return: status (True if host was removed properly, False otherwise)
    """

    hostObj = HOST_API.find(host)
    if deactivate:
        if not deactivateHost(positive=positive, host=host):
            return False
    return HOST_API.delete(hostObj, positive)


@is_action()
def activateHost(positive, host, wait=True):
    """
    Description: activate host (set status to UP)
    Author: edolinin
    Parameters:
       * host - name of a host to be activated
    Return: status (True if host was activated properly, False otherwise)
    """
    hostObj = HOST_API.find(host)
    status = HOST_API.syncAction(hostObj, "activate", positive)

    if status and wait and positive:
        testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 200)
    else:
        testHostStatus = True

    return status and testHostStatus


def _sort_hosts_by_priority(hosts, reverse=True):
    """
    Description: Set hosts by priorities, default is DESC order
    Author: mbourvin
    Parameters:
    * hosts - hosts to be sorted
    Returns: A list of hosts, order by priority (default: DESC)
    """
    if type(hosts) == str:
        hosts = hosts.split(',')

    hosts_priorities_dic = {}
    for host in hosts:
        spm_priority = getSPMPriority(host)
        hosts_priorities_dic[host] = spm_priority

    sorted_list = sorted(hosts_priorities_dic, key=hosts_priorities_dic.get,
                         reverse=reverse)
    HOST_API.logger.info('Sorted hosts list: %s', sorted_list)
    return sorted_list


@is_action()
def activateHosts(positive, hosts):
    """
    Description: activates the set of hosts. If host activation is not
                 successful, waits 30 seconds before the second attempt
                 - due to possible contending for SPM
    Author: alukiano
    Parameters:
    * hosts - hosts to be activated
    Returns: True (success) / False (failure)
    """
    sorted_hosts = _sort_hosts_by_priority(hosts)

    for host in sorted_hosts:
        status = activateHost(True, host)
        if not status:
            time.sleep(30)
            status = activateHost(True, host)
            if not status:
                return status
    return positive


def isHostInMaintenance(positive, host):
    """
    Description: Checks if host is in maintenance state
    Author: ratamir
    Parameters:
        * host - name of host to check
    Return: positive if host is up, False otherwise
    """
    try:
        host_status = getHostState(host)
    except EntityNotFound:
        return False

    return (host_status == ENUMS['host_state_maintenance']) == positive


@is_action()
def deactivateHost(positive, host,
                   expected_status=ENUMS['host_state_maintenance'],
                   timeout=300):
    """
    Description: check host state for SPM role, for 'timeout' seconds, and
    deactivate it if it is not contending to SPM.

    (set status to MAINTENANCE)
    Author: jhenner
    Parameters:
       * host - the name of a host to be deactivated.
       * host_state_maintenance - the state to expect the host to remain in.
       * timeout - time interval for checking if the state is changed
    Return: status (True if host was deactivated properly and positive,
                    False otherwise)
    """
    hostObj = HOST_API.find(host)
    sampler = TimeoutingSampler(
        timeout, 1, lambda x: x.get_storage_manager().get_valueOf_(), hostObj)
    for sample in sampler:
        if not sample == ENUMS['spm_state_contending']:
            if not HOST_API.syncAction(hostObj, "deactivate", positive):
                return False

            # If state got changed, it may be transitional
            # state so we may want to wait
            # for the final one. If it didn't, we certainly can
            # return immediately.
            hostState = hostObj.get_status().get_state()
            getHostStateAgain = HOST_API.find(host).get_status().get_state()
            state_changed = hostState != getHostStateAgain
            if state_changed:
                testHostStatus = HOST_API.waitForElemStatus(hostObj,
                                                            expected_status,
                                                            180)
                return testHostStatus and positive
            else:
                return not positive


@is_action()
def installHost(positive, host, root_password, iso_image=None,
                override_iptables='true'):
    """
    Description: run host installation
    Author: edolinin, atal
    Parameters:
       * host - name of a host to be installed
       * root_password - password of root user
       * iso_image - iso image for rhevh installation
       * override_iptables - override iptables. gets true/false strings.
    Return: status (True if host was installed properly, False otherwise)
    """
    state_maintenance = ENUMS['host_state_maintenance']
    state_installing = ENUMS['host_state_installing']
    hostObj = HOST_API.find(host)
    status = HOST_API.syncAction(hostObj, "install", positive,
                                 root_password=root_password,
                                 image=iso_image,
                                 override_iptables=override_iptables.lower())
    if status and not positive:
        return True
    if not (status and HOST_API.waitForElemStatus(hostObj, state_installing,
                                                  800)):
        return False
    return HOST_API.waitForElemStatus(hostObj, state_maintenance, 800)


@is_action()
def approveHost(positive, host, cluster='Default'):
    """
    Description: approve host (for ovirt hosts)
    Author: edolinin
    Parameters:
       * host - name of a host to be approved
       * cluster - name of cluster
    Return: status (True if host was approved properly, False otherwise)
    """

    hostObj = HOST_API.find(host)
    clusterObj = CL_API.find(cluster)

    kwargs = {'cluster': clusterObj}
    status = HOST_API.syncAction(hostObj, "approve", positive, **kwargs)
    testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 120)

    return status and testHostStatus


# FIXME: need to rewrite this def because new ovirt approval has been changed
@is_action()
def installOvirtHost(positive, host, user_name, password, vdc, port=443,
                     timeout=60):
    """
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
    """
    if waitForHostsStates(positive, host,
                          ENUMS['search_host_state_pending_approval']):
        return True

    vdcHostName = getHostName(vdc)
    if not vdcHostName:
        HOST_API.logger.error("Can't get hostname from %s" % vdc)

    ip = getHostIP(host)
    hostObj = machine.Machine(ip, user_name, password).util(machine.LINUX)
    if not hostObj.isConnective():
        HOST_API.logger.error("No connectivity to the host %s" % host)
        return False
    commands = []
    commands.append([
        SED, '-i',
        "'s/vdc_host_name[[:space:]]*=.*/vdc_host_name = %s/'" % vdcHostName,
        "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([
        SED, '-i',
        "'s/nc_host_name[[:space:]]*=.*/nc_host_name = %s/'" % vdc,
        "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
    commands.append([
        SED, '-i',
        "'s/vdc_host_port[[:space:]]*=.*/vdc_host_port = %s/'" % port,
        "/etc/vdsm-reg/vdsm-reg.conf", '--copy'])
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
                              states=ENUMS[
                                  'search_host_state_pending_approval']):
        HOST_API.logger.error("Host %s isn't in PENDING_APPROVAL state" % host)
        return False

    return True


@is_action()
def commitNetConfig(positive, host):
    """
    Description: save host network configuration
    Author: edolinin
    Parameters:
       * host - name of a host to be committed
    Return: status (True if host network configuration was saved properly,
     False otherwise)
    """

    hostObj = HOST_API.find(host)
    return HOST_API.syncAction(hostObj, "commitnetconfig", positive)


@is_action()
def fenceHost(positive, host, fence_type):
    """
    Description: host fencing
    Author: edolinin
    Parameters:
       * host - name of a host to be fenced
       * fence_type - fence action (start/stop/restart/status)
    Return: status (True if host was fenced properly, False otherwise)
    """

    hostObj = HOST_API.find(host)
    # this is meant to differentiate between fencing a host in maintenance
    # and fencing a host in down state. since 3.4 fencing a host in maintenance
    # will result with the host staying in maintenance and not up state.
    host_in_maintenance = HOST_API.waitForElemStatus(hostObj, "maintenance",
                                                     30)
    status = HOST_API.syncAction(hostObj, "fence", positive,
                                 fence_type=fence_type.upper())

    # if test type is negative, we don't have to wait for element status,
    # since host state will not be changed
    if status and not positive:
        return True
    testHostStatus = True
    if fence_type == "restart" or fence_type == "start":
        if host_in_maintenance:
            testHostStatus = HOST_API.waitForElemStatus(hostObj, "maintenance",
                                                        500)
        else:
            testHostStatus = HOST_API.waitForElemStatus(hostObj, "up", 500)
    if fence_type == "stop":
        testHostStatus = HOST_API.waitForElemStatus(hostObj, "down", 300)
    return (testHostStatus and status) == positive


def _prepareHostNicObject(**kwargs):
    """
    preparing Host Nic object
    Author: atal
    if update exists in kwargs the nic_obj should be updated and not created
    return: Host Nic data structure object
    """
    add = True
    if 'update' in kwargs:
        nic_obj = kwargs.get('update')
        kwargs['name'] = nic_obj.get_name()
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

    if 'boot_protocol' in kwargs:
        nic_obj.set_boot_protocol(kwargs.get('boot_protocol'))

    if 'override_configuration' in kwargs:
        nic_obj.set_override_configuration(kwargs.get(
            'override_configuration'))
    if kwargs.get('properties'):
        properties_obj = create_properties(**kwargs.get('properties'))
        nic_obj.set_properties(properties_obj)

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

    if slave_list:
        bond_obj = data_st.Bonding()
        slaves = data_st.Slaves()
        for nic in slave_list:
            slaves.add_host_nic(data_st.HostNIC(name=nic.strip()))

        bond_obj.set_slaves(slaves)

        if mode:
            options = data_st.Options()
            options.add_option(data_st.Option(name='mode', value=mode))
            # for bond mode 1 miimon is reuqired
            if mode == 1 and not miimon:
                miimon = 100

            if miimon:
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
    return HOST_API.getElemFromLink(host_obj, 'nics', 'host_nic',
                                    get_href=True)


def getHostNicsList(host):
    host_obj = HOST_API.find(host)
    return HOST_API.getElemFromLink(host_obj, 'nics', 'host_nic',
                                    get_href=False)


@is_action()
def attachHostNic(positive, host, nic, network):
    """
    Description: attach network interface card to host
    Author: edolinin
    Parameters:
        * host - name of a host to attach nic to
        * nic - nic name to be attached
        * network - network name
    Return: status (True if nic was attached properly to host, False otherwise)
    """

    host_obj = HOST_API.find(host)
    cluster = CL_API.find(host_obj.cluster.id, 'id').get_name()

    host_nic = getHostNic(host, nic)
    cl_net = getClusterNetwork(cluster, network)

    return HOST_API.syncAction(host_nic, "attach", positive, network=cl_net)


@is_action()
def updateHostNic(positive, host, nic, **kwargs):
    """
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
    """

    nic_obj = getHostNic(host, nic)
    kwargs.update([('nic', nic_obj)])
    nic_new = _prepareHostNicObject(**kwargs)
    nic, status = HOST_NICS_API.update(nic_obj, nic_new, positive)

    return status


# FIXME: network param is deprecated.
@is_action()
def detachHostNic(positive, host, nic, network=None):
    """
    Description: detach network interface card from host
    Author: edolinin
    Parameters:
       * host - name of a host to attach nic to
       * nic - nic name to be detached
    Return: status (True if nic was detach properly from host, False otherwise)
    """
    nicObj = getHostNic(host, nic)

    return HOST_API.syncAction(nicObj, "detach", positive,
                               network=nicObj.get_network())


@is_action()
def genSNNic(nic, **kwargs):
    """
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
    """
    kwargs.update({'name': nic})
    nic_obj = _prepareHostNicObject(**kwargs)

    return True, {'host_nic': nic_obj}


@is_action()
def sendSNRequest(positive, host, nics=[], auto_nics=[], **kwargs):
    """
    Perform setupNetwork action on host with nic objects taken from 'nics' and
    'auto_nics' lists
    Author: atal, tgeft
    params:
        * host - the name of the host
        * nics - a list of nic objects to be added to the host by the
                 setupNework action
        * auto_nics - a list of nics to preserve from the current setup
        * kwargs - a dictionary of supported options:
            check_connectivity=boolean, connectivity_timeout=int, force=boolean
    """
    current_nics_obj = HOST_API.get(href=getHostNics(host))
    new_nics_obj = nics + [getHostNic(host, nic) for nic in auto_nics]

    host_nics = data_st.HostNics(host_nic=new_nics_obj)
    return HOST_NICS_API.syncAction(current_nics_obj, "setupnetworks",
                                    positive,
                                    host_nics=host_nics,
                                    **kwargs)


@is_action()
def searchForHost(positive, query_key, query_val, key_name=None, **kwargs):
    """
    Description: search for a host by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in host object equivalent to query_key
    Return: status (True if expected number of hosts equal to found by search,
    False otherwise)
    """

    return searchForObj(HOST_API, query_key, query_val, key_name, **kwargs)


@is_action()
def rebootHost(positive, host, username, password):
    """
    Description: rebooting host via ssh session
    Author: edolinin
    Parameters:
       * host - fqdn (name) of a host to be rebooted
       * username - user name for ssh session
       * password - password for ssh session
    Return: status (True if host was rebooted properly, False otherwise)
    """
    host_machine = machine.Machine(
        host=host, user=username, password=password,
    ).util(machine.LINUX)
    host_machine.reboot()
    return waitForHostsStates(positive, host, ENUMS['non_responsive'], 180)


@is_action()
def runDelayedControlService(positive, host, host_user, host_passwd, service,
                             command='restart', delay=0):
    """
    Description: Restarts a service on the host after a delay
    Author: adarazs
    Parameters:
      * host - ip or fqdn of the host
      * host_user - user name for the host
      * host_passwd - password for the user
      * service - the name of the service (eg. vdsmd)
      * command - command to issue (eg. start/stop/restart)
      * delay - the required delay in seconds
    Return: True if the command is sent successfully, False otherwise,
    or inverted in case of negative test
    """
    cmd = '( sleep %d; service %s %s 1>/dev/null; echo $? )' \
          % (delay, service, command)
    host_obj = machine.Machine(
        host, host_user, host_passwd
    ).util(machine.LINUX)
    output = host_obj.runCmd(cmd.split(), bg=('/tmp/delayed-stdout',
                                              '/tmp/delayed-stderr'))
    if not output[0]:
        HOST_API.logger.error("Sending delayed service control command failed."
                              " Output: %s", output[1])
    return output[0] == positive


@is_action()
def addTagToHost(positive, host, tag):
    """
    Description: add tag to a host
    Author: edolinin
    Parameters:
       * host - name of a host to add a tag to
       * tag - tag name that should be added
    Return: status (True if tag was added properly, False otherwise)
    """

    hostObj = HOST_API.find(host)
    tagObj = Tag(name=tag)
    hostTags = HOST_API.getElemFromLink(hostObj, link_name='tags', attr='tag',
                                        get_href=True)
    tagObj, status = TAG_API.create(tagObj, positive, collection=hostTags)
    return status


@is_action()
def removeTagFromHost(positive, host, tag):
    """
    Description: remove tag from a host
    Author: edolinin
    Parameters:
       * host - name of a host to remove a tag from
       * tag - tag name that should be removed
    Return: status (True if tag was removed properly, False otherwise)
    """

    hostObj = HOST_API.find(host)
    tagObj = HOST_API.getElemFromElemColl(hostObj, tag, 'tags', 'tag')
    if tagObj:
        return HOST_API.delete(tagObj, positive)
    else:
        HOST_API.logger.error("Tag {0} is not found at host {1}".format(tag,
                                                                        host))
        return False


@is_action()
def checkHostSpmStatus(positive, hostName):
    """
    Description: The function checkHostSpmStatus checking Storage Pool Manager
                 (SPM) status of the host.
    Parameters:
    * hostName - the host name
    Returns: 1) True when the host is SPM and positive also True,
                otherwise return False.
             2) True when host is not SPM and positive equal to False,
                otherwise return False.
    """
    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                              hostName, attribute)
        return False

    spmStatus = hostObj.get_storage_manager().get_valueOf_()
    HOST_API.logger.info("checkHostSpmStatus - SPM Status of host %s is: %s",
                         hostName, spmStatus)

    # due to differences between the return types of java and python sdk
    # checks for spmStatus in a set with different possible return values
    # as a workaround
    return (spmStatus in ('true', True, 'True')) == positive


@is_action()
def returnSPMHost(hosts):
    """
    Description: get SPM host from the list of hosts
    Author: gickowic
    Parameters:
    * hosts - the list of hosts to be searched through
    """
    if isinstance(hosts, str):
        hosts = hosts.split(',')
    hosts = [HOST_API.find(host) for host in hosts]

    for host in hosts:
        # TODO: remove check against string and leave as boolean when ticket
        # https://engineering.redhat.com/trac/automation/ticket/2142 is solved
        if host.get_storage_manager().get_valueOf_() == 'true':
            return True, {'spmHost': host.get_name()}
    return False, {'spmHost': None}


@is_action()
def getAnyNonSPMHost(hosts, expected_states=None, cluster_name=None):
    """
    Description: get any not SPM host from the list of hosts in the expected
    state
    Author: gickowic
    Parameters:
    * hosts - the list of hosts to be searched through
    * expected_states - list of states to filter hosts by. Set to None to
    disable filtering by host state
    * cluster_name - filter for hosts belonging to a specific cluster
    """
    if isinstance(hosts, str):
        hosts = hosts.split(',')

    hosts = [HOST_API.find(host) for host in hosts]

    if expected_states:
        HOST_API.logger.info('Filtering host list for hosts in states %s',
                             expected_states)
        hosts = [host for host in hosts
                 if host.get_status().get_state() in expected_states]
        HOST_API.logger.info('New hosts list is %s',
                             [host.get_name() for host in hosts])

    for host in hosts:
        # TODO: remove check against string and leave as boolean when ticket
        # https://engineering.redhat.com/trac/automation/ticket/2142 is solved
        if cluster_name and cluster_name != CL_API.find(
                host.get_cluster().get_id(),  attribute='id').get_name():
            continue
        if host.get_storage_manager().get_valueOf_() == 'false':
            return True, {'hsmHost': host.get_name()}
    return False, {'hsmHost': None}


@is_action()
def getSPMPriority(hostName):
    """
    Description: Get SPM priority of host
    Author: mbourvin
    Parameters:
    * hostName - name/ip of host
    Return: The SPM priority of the host.
    """

    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                              hostName, attribute)
        return False

    spmPriority = hostObj.get_storage_manager().get_priority()
    HOST_API.logger.info("checkSPMPriority - SPM Value of host %s is %s",
                         hostName, spmPriority)
    return spmPriority


@is_action()
def checkSPMPriority(positive, hostName, expectedPriority):
    """
    Description: check SPM priority of host
    Author: imeerovi
    Parameters:
    * hostName - name/ip of host
    * expected priority - expected value of SPM priority on host
    Return: True if SPM priority value is equal to expected value.
            False in other case.
    """
    spmPriority = getSPMPriority(hostName)

    return (str(spmPriority) == expectedPriority)


@is_action()
def setSPMPriority(positive, hostName, spmPriority):
    """
    Description: set SPM priority on host
    Author: imeerovi
    Parameters:
    * hostName - name/ip of host
    * spmPriority - expecded value of SPM priority on host
    Return: True if spm value is set OK.
            False in other case.
    """

    attribute = 'storage_manager'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                              hostName, attribute)
        return False

    # Update host
    HOST_API.logger.info("Updating Host %s priority to %s", hostName,
                         spmPriority)
    updateStat = updateHost(positive=positive, host=hostName,
                            storage_manager_priority=spmPriority)

    # no need to continue checking what the new priority is in case of
    # negative test
    if not positive:
        return updateStat

    if not updateStat:
        return False

    hostObj = HOST_API.find(hostName)
    new_priority = hostObj.get_storage_manager().get_priority()
    HOST_API.logger.info("setSPMPriority - SPM Value of host %s is set to %s",
                         hostName, new_priority)

    return new_priority == int(spmPriority)


@is_action()
def setSPMPriorityInDB(
        positive, hostName, spm_priority, ip, user, password, db_user):
    """
    Description: set SPM priority for host in DB
    Author: pdufek
    Parameters:
    * hostName - the name of the host
    * spm_priority - SPM priority to be set for host
    * ip - IP of the machine where DB resides
    * user - username for remote access
    * password - password for remote access
    Returns: True (successfully set) / False (failure)
    """
    cmd = 'psql engine %s -c \"UPDATE vds_static SET ' \
          'vds_spm_priority=\'%s\' WHERE vds_name=\'%s\';\"' \
          % (db_user, spm_priority, hostName)
    status = runMachineCommand(True, ip=ip, user=user, password=password,
                               cmd=cmd)
    if not status[0]:
        log_fce = HOST_API.logger.error \
            if (positive is not None) and positive else HOST_API.logger.info
        log_fce('Command \'%s\' failed: %s' % (cmd, status[1]['out']))
    return status[0] == positive


@is_action()
def checkHostsForSPM(positive, hosts, expected_spm_host):
    """
    Description: checks whether SPM is expected host or not
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    * expected_spm_host - host which should be SPM
    Returns: True (success - SPM is expected host) / False (failure)
    """
    for host in hosts.split(','):
        if checkHostSpmStatus(True, host):
            return (host == expected_spm_host) == positive
    return not positive


@is_action()
def checkSPMPresence(positive, hosts):
    """
    Description: checks whether SPM is set within the set of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: True (success - SPM is present on any host from list)
             False (failure - SPM not present)
    """
    for host in hosts.split(','):
        if checkHostSpmStatus(True, host):
            return positive
    else:
        return not (positive)


def _getSPMHostname(hosts):
    """
    Description: get SPM host from the list of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: hostName (success) / raises EntityNotFound exception
    """
    status, spmHostDict = returnSPMHost(hosts)
    if status:
        return spmHostDict['spmHost']
    else:
        raise EntityNotFound('SPM not found among these hosts: %s'
                             % (str(hosts),))


@is_action()
def deactivateHosts(positive, hosts):
    """
    Description: deactivates the set of hosts. If host deactivation is not
                 successful, waits 30 seconds before the second attempt
                 - due to possible contending for SPM
    Author: pdufek
    Parameters:
    * hosts - hosts to be deactivated
    Returns: True (success) / False (failure)
    """
    if isinstance(hosts, str):
        hosts = hosts.split(',')

    sorted_hosts = _sort_hosts_by_priority(hosts, False)

    for host in sorted_hosts:
        status = deactivateHost(True, host)
        if not status:
            return status == positive
    return True == positive


@is_action()
def reactivateHost(positive, host):
    """
    Description: reactivates host (puts it to 'Maintenance' state first,
                 then to 'UP' state)
    Author: pdufek
    Parameters:
    * host - the name of the host to be reactivated
    Returns: True (success) / False (failure)
    """
    status = deactivateHost(True, host)
    if status:
        status = activateHost(True, host)
    return status == positive


@is_action()
def getSPMHost(hosts):
    """
    Description: get SPM host from the list of hosts
    Author: pdufek
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: hostName (success) / raises EntityNotFound exception
    """
    for host in hosts:
        if checkHostSpmStatus(True, host):
            return host
    else:
        raise EntityNotFound('SPM not found among these hosts: %s'
                             % (str(hosts),))


@is_action()
def getHSMHost(hosts):
    """
    Description: get HSM host from the list of hosts
    Author: ratamir
    Parameters:
    * hosts - the list of hosts to be searched through
    Returns: hostName (success) / raises EntityNotFound exception
    """
    for host in hosts:
        if not checkHostSpmStatus(True, host):
            return host
    else:
        raise EntityNotFound('HSM not found among these hosts: %s'
                             % hosts)


@is_action()
def getHost(positive, dataCenter='Default', spm=True, hostName=None):
    """
    Locate and return SPM or HSM host from specific data center (given by name)
        dataCenter  - The data center name
        spm      - When true return SPM host, false locate and return the
        HSM host
        hostName - Optionally, when the host name exist, the function locates
                   the specific HSM host. When such host doesn't exist, the
                   first HSM found will be returned.
    return: True and located host name in case of success,
    otherwise false and None
    """

    try:
        clusters = CL_API.get(absLink=False)
        dataCenterObj = DC_API.find(dataCenter)
    except EntityNotFound:
        return False, {'hostName': None}

    clusters = (cl for cl in clusters if hasattr(cl, 'data_center')
                and cl.get_data_center()
                and cl.get_data_center().id == dataCenterObj.id)
    for cluster in clusters:
        elementStatus, hosts = searchElement(positive, ELEMENT, COLLECTION,
                                             'cluster', cluster.name)
        if not elementStatus:
            return False, {'hostName': None}
        for host in hosts:
            spmStatus = checkHostSpmStatus(positive, host.name)
            if spm and spmStatus:
                return True, {'hostName': host.name}
            elif not spm and not spmStatus and (not hostName
                                                or hostName == host.name):
                return True, {'hostName': host.name}
    return False, {'hostName': None}


@is_action()
def waitForSPM(datacenter, timeout, sleep):
    """
    Description: waits until SPM gets elected in DataCenter
    Author: jhenner
    Parameters:
      * datacenter - the name of the datacenter
      * timeout - how much seconds to wait until it fails
      * sleep - how much to sleep between checks
    Return: True if an SPM gets elected before timeout. It rises
    RESTTimeout exception on timeout.
    """
    sampler = TimeoutingSampler(timeout, sleep,
                                getHost, True, datacenter, True)
    sampler.timeout_exc_args = "Timeout when waiting for SPM to appear"
    " in DC %s." % datacenter,
    for s in sampler:
        if s[0]:
            return True


@is_action()
def getHostNicAttr(host, nic, attr):
    """
    get host's nic attribute value
    Author: atal
    Parameters:
       * host - name of a host
       * nic - name of nic we'd like to check
       * attr - attribute of nic we would like to recive. attr can dive deeper
         as a string with DOTS ('.').
    return: True if the function succeeded, otherwise False
    """
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


# FIXME: remove this function - not being used at all, even not in actions.conf
def validateHostExist(positive, host):
    """
    Description: Validate host if exists in the setup
    Author: egerman
    Parameters:
       * host - host name
    Return:
        1) When positive equals True and given host exists in the setup -
           return true,otherwise return false
        2) When positive equals False and given host does not exists in
           the setup  - return true,otherwise return false
    """
    hosts = HOST_API.get(absLink=False)
    hosts = filter(lambda x: x.get_name().lower() == host.lower(), hosts)
    return bool(hosts) == positive


@is_action()
def getHostCompatibilityVersion(host):
    """
    Description: Get Host compatibility version
    Author: istein, gickowic
    Parameters:
       * host - host name
    Return: Compatibility version if found else None
    """

    # check if given hostname exists in the setup
    try:
        hostObj = HOST_API.find(host)
    except EntityNotFound:
        return None

    # Since host returned from API supplies the cluster ID, cluster *must*
    # exist in rhevm - no need to check
    clId = hostObj.get_cluster().get_id()
    clObj = CL_API.find(clId, 'id')

    cluster = clObj.get_name()
    return getClusterCompatibilityVersion(cluster)


@is_action()
def waitForHostNicState(host, nic, state, interval=1, attempts=1):
    """
    Waiting for Host's nic state
    Author: atal
    params:
        * host - host name
        * nic - nic name
        * state - state we would like to achive
        * interval - time between checks
        * attempts - number of attempts before returning False
    return True/False
    """
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
    """
    Turning remote machine interface down
    :param host: ip or fqdn of name
    :param root_password: to login remote machine
    :param nic: interface name. make sure you're not trying to disable rhevm
           network!
    :param wait: Wait for NIC status down
    :return True/False
    """
    # must always run as a root in order to run ifdown
    host_obj = machine.Machine(getIpAddressByHostName(host), "root",
                               root_password).util(machine.LINUX)
    if not host_obj.ifdown(nic):
        return False
    if wait:
        return wait_for_host_nic_status(
            host=host, username="root", password=root_password, nic=nic,
            status="down", interval=10, attempts=10
        )

    return True


@is_action()
def ifupNic(host, root_password, nic, wait=True):
    """
    Turning remote machine interface up
    :param host: ip or fqdn
    :param root_password: to login remote machine
    :param nic: interface name.
    :param wait: Wait for NIC status up
    :return True/False
    """
    # must always run as a root in order to run ifup
    host_obj = machine.Machine(getIpAddressByHostName(host), "root",
                               root_password).util(machine.LINUX)
    if not host_obj.ifup(nic):
        return False
    if wait:
        return wait_for_host_nic_status(
            host=host, username="root", password=root_password, nic=nic,
            status="up", interval=10, attempts=10
        )
    return True


@is_action()
def getOsInfo(host, root_password=''):
    """
    Description: get OS info wrapper.
    Author: atal
    Parameters:
       * host - ip or fqdn
       * root_password - password of root user (required, can be empty only
         for negative tests)
    Return: True with OS info string if succeeded, False and None otherwise
    """
    host_obj = machine.Machine(host, 'root', root_password).util(machine.LINUX)
    if not host_obj.isAlive():
        HOST_API.logger.error("No connectivity to the host %s" % host)
        return False, {'osName': None}
    osName = host_obj.getOsInfo()
    if not osName:
        return False, {'osName': None}

    return True, {'osName': osName}


def getClusterCompatibilityVersion(cluster):
    """
    Description: Get Cluster compatibility version
    Author: istein, gickowic
    Parameters:
       * cluster - cluster name
    Return: Compatibilty version or None
    """
    try:
        clusterObj = CL_API.find(cluster)
    except EntityNotFound as err:
        HOST_API.logger.error(err)
        return None
    clVersion = '{0}.{1}'.format(clusterObj.get_version().get_major(),
                                 clusterObj.get_version().get_minor())
    return clVersion


@is_action()
def waitForHostPmOperation(host, engine):
    """
    Wait for next PM operation availability
    Author: lustalov

    :param host: vds host name
    :type host: string
    :param engine: engine
    :type engine: instance of resources.Engine
## CONTINUE
    Return: True if success, False otherwise
    """

    timeToWait = 0
    returnVal = True
    db = engine.db
    try:
        sql = (
            "select option_value from vdc_options "
            "where option_name = 'FenceQuietTimeBetweenOperationsInSec';"
        )
        res = db.psql(sql)
        waitSec = res[0][0]
        events = ['USER_VDS_STOP', 'USER_VDS_START', 'USER_VDS_RESTART']
        for event in events:
            sql = (
                "select get_seconds_to_wait_before_pm_operation("
                "'%s','%s', %s);"
            )
            res = db.psql(sql, host, event, waitSec)
            timeSec = int(res[0][0])
            if timeSec > timeToWait:
                timeToWait = timeSec
    except Exception as ex:
        HOST_API.logger.error(
            'Failed to get wait time before host %s PM operation: %s',
            host, ex
        )
        returnVal = False
    if timeToWait > 0:
        HOST_API.logger.info(
            'Wait %d seconds until PM operation will be permitted.',
            timeToWait
        )
        time.sleep(timeToWait)
    return returnVal


@is_action()
def checkNetworkFiltering(positive, host, user, passwd):
    """
    Description: Check that network filtering is enabled via VDSM
                 This function is also described in tcms_plan 6955
                 test_case 198901
    Author: awinter
    Parameters:
      * host - ip or fqdn
      * user - user name for the host
      * passwd - password for the user
    return: True if network filtering is enabled, False otherwise
    """

    host_obj = machine.Machine(host, user, passwd).util(machine.LINUX)
    if host_obj.runVirshCmd(['nwfilter-list'])[1].count(
            "vdsm-no-mac-spoofing") != 1:
        HOST_API.logger.error("nwfilter-list does not have"
                              " 'vdsm-no-mac-spoofing'")
        return not positive
    if not host_obj.isFileExists(RHEVM_UTILS['NWFILTER_DUMPXML']):
        HOST_API.logger.error("vdsm-no-mac-spoofing.xml file not found")
        return not positive
    if not checkNWFilterVirsh(host_obj):
        return not positive
    return positive


def checkNWFilterVirsh(host_obj):
    """
    Description: Checking that NWfilter is enable in dumpxml and in virsh
    Author: awinter
    Parameters:
      * host_obj - the host's object
    return: True if all the elements were found, False otherwise
    """
    not_found = -1

    xml_file = tempfile.NamedTemporaryFile()
    if not host_obj.copyFrom(RHEVM_UTILS['NWFILTER_DUMPXML'], xml_file.name):
        HOST_API.logger.error("Coping failed")
        return False
    with xml_file as f:
        tmp_file = f.read().strip()
        for string in search_for:
            if (tmp_file.find(string) == not_found) or \
                    (host_obj.runVirshCmd(virsh_cmd)[1].count(string) != 1):
                HOST_API.logger.error("nwfilter tags weren't found in file")
                return False
    return True


@is_action()
def checkNetworkFilteringDumpxml(positive, host, user, passwd, vm, nics):
    """
    Description: Check that network filtering is enabled via dumpxml
                 This function is also described in tcms_plan 6955
                 test_case 198914
    Author: awinter
    Parameters:
      * host - ip or fqdn
      * user - user name for the host
      * passwd - password for the user
      * vm - name of the vm
      * nics - number nics for vm in dumpxml
    return: True if network filtering is enabled, False otherwise
    """
    host_obj = machine.Machine(host, user, passwd).util(machine.LINUX)
    res, out = host_obj.runVirshCmd(['dumpxml', '%s' % vm])
    HOST_API.logger.debug("Output of dumpxml: %s", out)
    if not out.count(
            "<filterref filter='vdsm-no-mac-spoofing'/>") == int(nics):
        return not positive
    return positive


@is_action()
def checkNetworkFilteringEbtables(positive, host, user, passwd, nics, vm_macs):
    """
    Description: Check that network filtering is enabled via ebtables
                 This function is also described in tcms_plan 6955
                 test_case 198920
    Author: awinter
    Parameters:
      *  *host - ip or fqdn
      *  *user - user name for the host
      *  *passwd - password for the user
      *  *nics - number of nics
      *  *vm_macs - list of vms' macs
    **return**: True if network filtering is enabled, False otherwise
    """
    count = 0
    macTemplate = re.compile('([0-9a-f]+[:]){5}[0-9a-f]+', re.I)
    host_obj = machine.Machine(host, user, passwd).util(machine.LINUX)
    cmd = ['ebtables', '-t', 'nat', '-L']
    output = (host_obj.runCmd(cmd)[1].strip()).splitlines()
    for line in output:
        line_list = line.split()
        mac_addr = [word for word in line_list if re.match(macTemplate,
                                                           "0" + word)]
        if mac_addr:
            mac = "0" + mac_addr[0]
            if mac in vm_macs:
                count += 1

    if count != 2 * int(nics):
        HOST_API.logger.error("Mac not found in ebtables")
        return not positive
    return positive


def cleanHostStorageSession(hostObj, **kwargs):
    """
    Description: Runs few commands on a given host to clean storage related
                 session and dev maps.
    **Author**: talayan
    **Parameters**:
      **hostObj* - Object represnts the hostObj
    """
    # check if there is an active session
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
    """
    Description: pkill procName

    **Author**: talayan
    **Parameters**:
      **hostObj* - Object represnts the hostObj
      **procName* - process to kill
    """
    # check if there is zombie qemu proccess
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


@is_action()
def select_host_as_spm(positive, host, datacenter,
                       timeout=HOST_STATE_TIMEOUT, sleep=10, wait=True):
    """
    Description: Selects the host to be spm
    Author: gickowic
    Parameters:
       * host - name of a host to be selected as spm
       * wait - True to wait for spm election to be completed before returning
       (only waits if positive and wait are both true)
    Return: status (True if host was elected as spm properly, False otherwise)
    """
    hostObj = HOST_API.find(host)
    HOST_API.logger.info('Selecting host %s as spm', host)
    status = HOST_API.syncAction(hostObj, "forceselectspm", positive)

    if status:
        # only wait for spm election if action is expected to succeed
        if wait and positive:
            waitForSPM(datacenter, timeout=timeout, sleep=sleep)
            return checkHostSpmStatus(True, host)
        else:
            return True
    return False


def setHostToNonOperational(orig_host, host_password, nic):
    """
    Helper Function for check_vm_migration.
    It puts the NIC with required network down and causes the Host
    to become non-operational
    **Author**: gcheresh
        **Parameters**:
            *  *orig_host* - host to make non-operational
            *  *host_password* - password for the host machine
            *  *nic* - NIC with required network.
                Will start the migration when turned down
        **Returns**: True if Host became non-operational by putting NIC down,
                     otherwise False
    """
    ip = getHostIP(orig_host)
    if not ifdownNic(host=ip, root_password=host_password, nic=nic):
        return False

    return waitForHostsStates(True, names=orig_host, states='non_operational',
                              timeout=TIMEOUT)


def start_vdsm(host, password, datacenter):
    """
    Start vdsm. Before that stop all vms and deactivate host.
    Parameters:
      * host - host name in RHEVM
      * password - password of host
      * datacenter - datacenter of host
    """
    ip = getHostIP(host)
    if not startVdsmd(vds=ip, password=password):
        HOST_API.logger.error("Unable to start vdsm on host %s", host)
        return False
    if not activateHost(True, host):
        HOST_API.logger.error("Unable to activate host %s", host)
        return False

    return waitForDataCenterState(datacenter)


def stop_vdsm(host, password):
    """
    Stop vdsm. Before that stop all vms and deactivate host.
    Parameters:
      * host - host name in RHEVM
      * password - password of host
    """
    for vm in VM_API.get(absLink=False):
        if get_vm_state(vm.name) == ENUMS['vm_state_down']:
            continue
        if getVmHost(vm.name)[1]['vmHoster'] == host:
            HOST_API.logger.error("Stopping vm %s", vm.name)
            if not stopVm(True, vm.name):
                return False

    if not deactivateHost(True, host):
        HOST_API.logger.error("Unable to deactivate host %s", host)
        return False
    ip = getHostIP(host)
    return stopVdsmd(vds=ip, password=password)


def kill_qemu_process(vm_name, host, user, password):
    """
    Description: kill qemu process of a given vm
    Parameters:
        * vm_name - the vm name that wish to find its qemu proc
        * host - ip or fqdn of host rum qemu process
        * user - username for  host
        * password - password for host
    Author: ratamir
    Return:
        pid, or raise EntityNotFound exception
    """
    linux_machine = machine.Machine(
        host=host, user=user,
        password=password).util(machine.LINUX)

    cmd = FIND_QEMU % vm_name
    status, output = linux_machine.runCmd(shlex.split(cmd))
    if not status:
        raise RuntimeError("Output: %s" % output)
    qemu_pid = output.split()[1]
    HOST_API.logger.info("QEMU pid: %s", qemu_pid)

    return linux_machine.runCmd(shlex.split('kill -9 %s', qemu_pid))


@is_action()
def change_mom_rpc_port(host, host_user, host_pwd, port=8080):
    '''
    Change port for mom rpc communication
    Author: lsvaty
    Parameters:
        * host - ip of host
        * host_user - user on host machine (root)
        * host_pwd - password for host_user user
        * port - port for xmlrpc communication
    @return value - (return code, output)
    '''
    host_machine = machine.Machine(
        host, host_user, host_pwd).util(machine.LINUX)
    rc, out = host_machine.runCmd(['sed', '-i',
                                   's/rpc-port: [-0-9]\\+/rpc-port: ' +
                                   str(port) + '/',
                                   MOM_CONF])
    if not rc:
        HOST_API.logger.error(
            "Failed to edit rpc port for mom on host %s ", host)
        return False
    return host_machine.restartService("vdsmd")


def set_mom_script(host, host_user, host_pwd, path=MOM_SCRIPT_PATH):
    '''
    Set script for xmlrpc communication with mom
    Author: lsvaty
    Parameters:
        * host - ip of host
        * host_user - user on host machine (root)
        * host_pwd - password for host_user user
        * path - path to file
    @return value - tuple (return code, output)
    '''
    host_machine = machine.Machine(
        host, host_user, host_pwd).util(machine.LINUX)

    return host_machine.copyTo(find_test_file(MOM_SCRIPT_LOCAL),
                               MOM_SCRIPT_PATH)


def remove_mom_script(host, host_user, host_pwd, path=MOM_SCRIPT_PATH):
    '''
    Remove script for xmlrpc communication with mom
    Author: lsvaty
    Parameters:
        * host - ip of host
        * host_user - user on host machine (root)
        * host_pwd - password for host_user user
        * path - path to file
    @return value - tuple (return code, output)
    '''
    host_machine = machine.Machine(
        host, host_user, host_pwd).util(machine.LINUX)
    return host_machine.runCmd(['rm', '-f', path])


@is_action()
def get_mom_statistics(host, host_user, host_pwd, port=8080,
                       path=MOM_SCRIPT_PATH):
    '''
    get statistics from mom through xmlrpc
    first need to set the script for usage by setMomScript()
    Author: lsvaty
    Parameters:
        * host - ip of host
        * host_user - user on host machine (root)
        * host_pwd - password for host_user user
        * port - port for rpc communication
        * path - path to mom script producing statistics
    @return value - tuple (True, dictionary of stats on succeess
        otherwise (False, output of run commands)
    '''
    host_machine = machine.Machine(
        host, host_user, host_pwd).util(machine.LINUX)
    rc, out = host_machine.runCmd(['python', path, str(port)])
    if rc:
        try:
            stats_dict = json.loads(out.replace('\'', '"'))
        except TypeError:
            return rc, out
        return rc, stats_dict
    return rc, out


def get_host_object(host_name):
    """
    This function get host object by host name.

    :param host_name: Name of host.
    :type host_name: str.
    :returns: Host object.
    """
    return HOST_API.find(host_name)


def get_host_topology(host_name):
    """
    This function get host topology object by host name.

    :param host_name: Name of host.
    :type host_name: str.
    :returns: Host topology object.
    :raises: EntityNotFound
    """
    host_obj = get_host_object(host_name)
    if not host_obj:
        raise EntityNotFound("No host with name %s" % host_name)
    return host_obj.cpu.topology


def run_command(host, user, password, cmd):
    """
    Description: ssh to user@hostname and run cmd on cli

    Parameters:
        * host_name - str , the name of the host
        * user - str , a string of the login user
        * password - str , a string of the login password
        * cmd - str , a string of the command to run

    Returns :
        * out - str , the command's output.
    """
    connection = machine.Machine(host=getHostIP(host),
                                 user=user,
                                 password=password).util(machine.LINUX)
    rc, out = connection.runCmd(shlex.split(cmd))
    if not rc:
        raise RuntimeError("Output: %s" % out)

    return out


def count_host_active_vms(host, num_of_vms, timeout=300, sleep=10):
    """
    Count number of active vms on host in given timeout
    **Author**: alukiano

    **Parameters**:
        * *host* - host to look on it
        * *num_of_vms - number of vms on host that you wait for
        * *timeout - timeout how long should we wait
        * *sleep - polling interval
    **Returns**: Migration time duration,
                 if number of vms on host equal to num_of_vms
                 None, otherwise
    """
    start_time = time.time()
    sampler = TimeoutingSampler(timeout, sleep, HOST_API.find, val=host)
    try:
        for sample in sampler:
            if sample.get_summary().get_active() == num_of_vms:
                return time.time() - start_time
    except APITimeout:
        HOST_API.logger.error(
            "Timeout when waiting for number of vms %d on host %s",
            num_of_vms, host)
        return None


def check_host_nic_status(host, username, password, nic, status):
    """
    Get NIC status from host
    :param host: Host IP or FQDN
    :param username: Host username
    :param password: Host password
    :param nic: NIC name
    :param status: Status to check
    :return: True/False
    """
    status = "yes" if status.lower() == "up" else "no"
    host_obj = machine.Machine(host, username, password).util(machine.LINUX)
    cmd = ["ethtool", nic]
    rc, out = host_obj.runCmd(cmd)

    if not rc:
        return False

    cmd_out = out.rsplit("\r\n\t", 1)[1].split(":")[-1].strip()
    if cmd_out.lower() == status:
        return True
    return False


def wait_for_host_nic_status(host, username, password, nic, status,
                             interval=1, attempts=1):
    """
    Wait for host NIC status
    :param host: host IP or FQDN
    :param username: Host Username
    :param password: Host password
    :param nic: NIC name
    :param status: Status to check
    :param interval: Sleep in seconds between attempts
    :param attempts: Number of attempts
    :return: True/False
    """
    while attempts:
        if check_host_nic_status(
            host=host, username=username, password=password, nic=nic,
            status=status
        ):
            return True
        time.sleep(interval)
        attempts -= 1
    return False


def get_host_name_from_engine(host_ip):
    """
    Get host name from engine by host IP
    :param host_ip: resources.VDS object
    :return: host.name or None
    """

    engine_hosts = HOST_API.get(absLink=False)
    for host in engine_hosts:
        if host.get_address() == host_ip or host.name == host_ip:
            return host.name
    return None


def get_host_ip_from_engine(host):
    """
    Get host name from engine by host IP
    :param host_ip: resources.VDS object
    :return: host.name or None
    """

    host_name = HOST_API.find(host)
    return host_name.get_address()


def refresh_host_capabilities(host):
    """
    Refresh Host Capabilities
    :param host: Host name
    :return: True/False
    """
    host_obj = HOST_API.find(host)
    code = 606
    last_event_id = EVENT_API.get(absLink=False)[0].get_id()
    event_description = (
        "Successfully refreshed the capabilities of host {0}.".format(
            host)
    )
    refresh_href = ";".join([host_obj.get_href(), "force"])
    HOST_API.get(href=refresh_href)

    for event in EVENT_API.get(absLink=False):
        if event.get_id() == last_event_id:
            return False
        if event.get_code() == code:
            if event_description == event.get_description():
                return True
    return False


def get_cluster_hosts(cluster_name, host_status=ENUMS['host_state_up']):
    """
    Get a list of host names for a given cluster.
        * cluster_name: name of the cluster
        * host_status: status of the host
    Return: List of host names in a cluster with host_status or empty list
    """
    elementStatus, hosts = searchElement(True, ELEMENT, COLLECTION,
                                         'cluster', cluster_name)
    if elementStatus:
        return [host.get_name() for host in hosts
                if host.get_status().get_state() == host_status]
    return []
