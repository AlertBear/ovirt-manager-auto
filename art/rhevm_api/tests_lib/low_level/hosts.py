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
import re
import tempfile

from utilities.utils import getIpAddressByHostName, getHostName
from utilities import machine

from art.core_api.apis_utils import TimeoutingSampler, data_st
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from art.core_api.apis_utils import getDS
from art.core_api import is_action

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
TIMEOUT_NON_RESPONSIVE_HOST = 360
FIND_QEMU = 'ps aux |grep qemu | grep -e "-name %s"'

SAMPLER_TIMEOUT = 30

virsh_cmd = ['nwfilter-dumpxml', 'vdsm-no-mac-spoofing']
search_for = ["<filterref filter='no-mac-spoofing'/>",
              "<filterref filter='no-arp-mac-spoofing'/>"]


def get_host_list():
    hostUtil = get_api('host', 'hosts')
    return hostUtil.get(absLink=False)


def getHostState(host):
    """
    Description: Returns a host's state
    Author: cmestreg
    Parameters:
        * host - host to check
    Return: Returns the host's states [str] or raises EntityNotFound
    """
    return HOST_API.find(host).get_status().get_state()


def get_host_type(host_name):
    """
    Returns type of specific host name

    :param host_name: host name in rhevm to check his type
    :type host_name: str
    :return: the host type 'rhev-h'/'rhel'
    :rtype: str
    :raises: EntityNotFound
    """
    return HOST_API.find(host_name).get_type()


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
    Returns the name of the cluster that contains the input host

    :param host: host name
    :type host: str
    :returns: Returns the cluster name or raises EntityNotFound
    :rtype: str
    """
    host_obj = HOST_API.find(host)
    cluster = CL_API.find(host_obj.get_cluster().get_id(), attribute='id')
    return cluster.get_name()


def getHostDC(host):
    """
    Returns the name of the data center that contains the input host

    :param host: host name
    :type host: str
    :returns: Returns the data center name or raises EntityNotFound
    :rtype: str
    """
    HOST_API.logger.info("Host: %s", host)
    cl_name = getHostCluster(host)
    cl_obj = CL_API.find(cl_name)
    dc = DC_API.find(cl_obj.get_data_center().get_id(), attribute='id')
    return dc.get_name()


def isHostUp(positive, host):
    """
    Checks if host is in state "up"

    __author__ = "cmestreg"
    :param positive: True if action should succeed, False otherwise
    :type positive: bool
    :param host: name of the host
    :type host: str
    :return: True if host is in state "up", False otherwise
    :rtype: bool
    """
    host_status = getHostState(host)

    return (host_status == ENUMS['host_state_up']) == positive


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

    if isinstance(names, basestring):
        list_names = split(names)
    else:
        list_names = names[:]
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
    Update properties of existed host (provided in parameters)

    :param host: name of a target host
    :type host: str
    :param name: host name to change to
    :type name: str
    :param address: host address to change to
    :type address: str
    :param root_password: host password to change to
    :type root_password: str
    :param cluster: host cluster to change to
    :type cluster: str
    :param pm: host power management to change to
    :type pm: bool
    :param pm_type: host pm type to change to
    :type pm_type: str
    :param pm_address: host pm address to change to
    :type pm_address: str
    :param pm_username: host pm username to change to
    :type pm_username: str
    :param pm_password: host pm password to change to
    :type pm_password: str
    :param pm_port: host pm port to change to
    :type pm_port: int
    :param pm_secure: host pm security to change to
    :type pm_secure: bool
    :param pm_automatic: host automatic_pm_enabled flag
    :type pm_automatic: bool
    :param agents: if you have number of pm's, need to specify it under agents
    :type agents: dict
    :return: status (True if host was updated properly, False otherwise)
    :rtype: bool
    """

    host_obj = HOST_API.find(host)
    host_upd = Host()

    if 'name' in kwargs:
        host_upd.set_name(kwargs.pop('name'))
    if 'address' in kwargs:
        host_upd.set_address(kwargs.pop('address'))
    if 'root_password' in kwargs:
        host_upd.set_root_password(kwargs.pop('root_password'))

    if 'cluster' in kwargs:
        cl = CL_API.find(kwargs.pop('cluster', 'Default'))
        host_upd.set_cluster(cl)

    if 'storage_manager_priority' in kwargs:
        new_priority = kwargs.pop('storage_manager_priority')
        sm = StorageManager(new_priority,
                            host_obj.storage_manager.get_valueOf_())

        host_upd.set_storage_manager(sm)

    if 'pm' in kwargs:
        pm_address = kwargs.get('pm_address')
        pm_username = kwargs.get('pm_username')
        pm_password = kwargs.get('pm_password')
        pm_port = kwargs.get('pm_port')
        pm_slot = kwargs.get('pm_slot')
        pm_secure = kwargs.get('pm_secure')
        pm_automatic = kwargs.get('pm_automatic')

        pm_options = None
        if pm_port or pm_secure or pm_slot:
            pm_options = Options()
            if pm_port and pm_port.strip():
                op = Option(name='port', value=pm_port)
                pm_options.add_option(op)
            if pm_secure:
                op = Option(name='secure', value=pm_secure)
                pm_options.add_option(op)
            if pm_slot:
                op = Option(name='slot', value=pm_slot)
                pm_options.add_option(op)

        pm_proxies = None
        if kwargs.get('pm_proxies'):
            pm_proxies_list = [PmProxy(type_=proxy) for proxy
                               in kwargs.get('pm_proxies')]
            pm_proxies = PmProxies(pm_proxy=pm_proxies_list)

        if kwargs.get('agents'):
            agents = None
            agents_array = []
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
        else:
            agents = host_obj.get_power_management().get_agents()

        host_pm = PowerManagement(type_=kwargs.get('pm_type'),
                                  address=pm_address,
                                  enabled=kwargs.get('pm'),
                                  username=pm_username,
                                  password=pm_password,
                                  options=pm_options,
                                  pm_proxies=pm_proxies,
                                  automatic_pm_enabled=pm_automatic,
                                  agents=agents)

        host_upd.set_power_management(host_pm)

    try:
        host_obj, status = HOST_API.update(host_obj, host_upd, positive)
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
        if not isHostInMaintenance(positive, host):
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
    status = bool(HOST_API.syncAction(hostObj, "activate", positive))

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
    response = HOST_API.syncAction(
        hostObj, "install", positive, root_password=root_password,
        image=iso_image, override_iptables=override_iptables.lower()
    )
    if response and not positive:
        return True
    if not (
        response and HOST_API.waitForElemStatus(hostObj, state_installing, 800)
    ):
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
    status = bool(
        HOST_API.syncAction(hostObj, "approve", positive, **kwargs)
    )
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
    return bool(
        HOST_API.syncAction(hostObj, "commitnetconfig", positive)
    )


@is_action()
def fenceHost(positive, host, fence_type, timeout=500):
    """
    Description: host fencing
    Author: edolinin
    Parameters:
       * host - name of a host to be fenced
       * fence_type - fence action (start/stop/restart/status)
    Return: status (True if host was fenced properly, False otherwise)
    """

    host_obj = HOST_API.find(host)
    # this is meant to differentiate between fencing a host in maintenance
    # and fencing a host in down state. since 3.4 fencing a host in maintenance
    # will result with the host staying in maintenance and not up state.
    host_in_maintenance = getHostState(host) == ENUMS['host_state_maintenance']
    status = bool(
        HOST_API.syncAction(
            host_obj, "fence", positive, fence_type=fence_type.upper()
        )
    )

    # if test type is negative, we don't have to wait for element status,
    # since host state will not be changed
    if status and not positive:
        return True
    test_host_status = True
    if fence_type == "restart" or fence_type == "start":
        if host_in_maintenance:
            test_host_status = HOST_API.waitForElemStatus(
                host_obj, "maintenance", timeout
            )
        else:
            test_host_status = HOST_API.waitForElemStatus(
                host_obj, "up", timeout
            )
    if fence_type == "stop":
        test_host_status = HOST_API.waitForElemStatus(
            host_obj, "down", timeout
        )
    return (test_host_status and status) == positive


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
            if (mode == 1 or mode == 2) and not miimon:
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

    return bool(
        HOST_API.syncAction(host_nic, "attach", positive, network=cl_net)
    )


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

    return bool(
        HOST_API.syncAction(
            nicObj, "detach", positive, network=nicObj.get_network()
        )
    )


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

    # running with sampler BZ 1262051
    res = lambda: bool(
        HOST_NICS_API.syncAction(
            current_nics_obj, "setupnetworks", positive,
            host_nics=host_nics, **kwargs
        )
    )
    sample = TimeoutingSampler(timeout=SAMPLER_TIMEOUT, sleep=1, func=res)
    return sample.waitForFuncStatus(result=True)


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
    Rebooting host via ssh session

    __author__ = "edolinin"
    :param host: name of the host to be rebooted
    :type host: str
    :param username: user name for ssh session
    :type username: str
    :param password: password for ssh session
    :type password: str
    :returns: True if host was rebooted successfully, False otherwise
    :rtype: bool
    """
    host_ip = getHostIP(host)
    host_machine = machine.Machine(
        host=host_ip, user=username, password=password,
    ).util(machine.LINUX)
    host_machine.reboot()
    return waitForHostsStates(
        positive, host, ENUMS['host_state_non_responsive'],
        TIMEOUT_NON_RESPONSIVE_HOST,
    )


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
        host_value = host.get_storage_manager().get_valueOf_()
        if (isinstance(host_value, str) and host_value == 'true') or (
           isinstance(host_value, bool) and host_value):
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

        host_value = host.get_storage_manager().get_valueOf_()
        if (isinstance(host_value, str) and host_value == 'false') or (
           isinstance(host_value, bool) and not host_value):
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


# noinspection PyBroadException
@is_action()
def set_spm_priority_in_db(host_name, spm_priority, engine):
    """
    Description: set SPM priority for host in DB

    :param host_name: the name of the host
    :type host_name: string
    :param spm_priority: SPM priority to be set for host
    :type spm_priority: int
    :param engine: engine machine
    :type engine: instance of Engine
    :return: True if update of db success, otherwise False
    """
    sql = "UPDATE vds_static SET vds_spm_priority = '%s' WHERE vds_name = '%s'"
    try:
        engine.db.psql(sql, spm_priority, host_name)
    except Exception:
        return False
    return True


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
    if isinstance(hosts, str):
        hosts_list = split(',')
    else:
        hosts_list = hosts[:]
    for host in hosts_list:
        if checkHostSpmStatus(True, host):
            return positive
    else:
        return not positive


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
            continue
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
def check_network_filtering_ebtables(host_obj, vm_macs):
    """
    Description: Check that network filtering is enabled via ebtables

    :param host_obj: Host object
    :type host_obj: resources.VDS object
    :param vm_macs: list of vm_macs
    :type vm_macs: list
    :return: True if network filtering is enabled, False otherwise
    :rtype: bool
    """
    host_exec = host_obj.executor()
    cmd = "ebtables -t nat -L"
    rc, output, err = host_exec.run_cmd(shlex.split(cmd))
    if rc:
        HOST_API.logger.error("Failed to run command %s", cmd)
        return False
    for mac in vm_macs:
        vm_mac = ":".join(
            [i[1] if i.startswith('0') else i for i in mac.split(':')]
        )
        num_macs_ebtable = output.count(vm_mac)
        if num_macs_ebtable != 2:
            HOST_API.logger.info(
                "%s MACs found instead of 2", num_macs_ebtable
            )
            return False
    return True


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
    response = HOST_API.syncAction(hostObj, "forceselectspm", positive)

    if response:
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
                              timeout=TIMEOUT * 2)


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
        * host - name of the host
        * user - username for  host
        * password - password for host
    Author: ratamir
    Return:
        pid, or raise EntityNotFound exception
    """
    linux_machine = get_linux_machine_obj(host, user, password)
    cmd = FIND_QEMU % vm_name
    status, output = linux_machine.runCmd(shlex.split(cmd))
    if not status:
        raise RuntimeError("Output: %s" % output)
    qemu_pid = output.split()[1]
    HOST_API.logger.info("QEMU pid: %s", qemu_pid)

    return linux_machine.runCmd(['kill', '-9', qemu_pid])


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

    :param host: Name of host.
    :type host: str.
    :param num_of_vms: Expected number of vms on host.
    :type num_of_vms: int.
    :param timeout: Timeout in seconds.
    :type timeout: int.
    :param sleep: Time between samples in seconds.
    :type sleep: int.
    :returns: Waiting time for vms.
    :raises: APITimeout
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
    :param host: resources.VDS object
    :return: host.name or None
    """

    host_name = HOST_API.find(host)
    return host_name.get_address()


def refresh_host_capabilities(host, start_event_id):
    """
    Refresh Host Capabilities
    :param host: Host name
    :type host: str
    :param start_event_id: Event id to search from
    :type start_event_id: str
    :return: True/False
    :rtype: bool
    """
    host_obj = HOST_API.find(host)
    code = [606, 607]
    query = "type={0} OR type={1}".format(code[0], code[1])
    refresh_href = "{0};force".format(host_obj.get_href())
    HOST_API.get(href=refresh_href)

    for event in EVENT_API.query(query):
        if int(event.get_id()) < int(start_event_id):
            return False
        if event.get_code() in code:
            return True if event.get_code() == code[0] else False
    return False


def get_cluster_hosts(cluster_name, host_status=ENUMS['host_state_up']):
    """
    Get a list of host names for a given cluster.
        * cluster_name: name of the cluster
        * host_status: status of the host
    Return: List of host names in a cluster with host_status or empty list
    """
    elm_status, hosts = searchElement(
        True, ELEMENT, COLLECTION, 'cluster', cluster_name
    )
    if elm_status:
        return [host.get_name() for host in hosts
                if host.get_status().get_state() == host_status]
    return []


def get_linux_machine_obj(host, host_user, host_passwd, by_ip=True):
    """
    Get linux machine object

    :param host: name of host
    :type host: str
    :param host_user: user name to login to host
    :type host_user: str
    :param host_passwd: user password to login to host
    :type host_passwd: str
    :param by_ip: if get linux machine by ip
    :type by_ip: bool
    :returns: object of linux machine
    """
    host_ip = getHostIP(host) if by_ip else host
    return machine.Machine(host_ip, host_user, host_passwd).util(machine.LINUX)


def get_host_memory(host_name):
    """
    Get host memory

    :param host_name: host name
    :type host_name: str
    :returns: total host memory
    """
    stats = getStat(host_name, ELEMENT, COLLECTION, ["memory.total"])
    return stats["memory.total"]


def get_host_max_scheduling_memory(host_name):
    """
    Get host max scheduling memory

    :param host_name: host name
    :type host_name: str
    :returns: host max scheduling memory
    """
    host_obj = get_host_object(host_name)
    return host_obj.get_max_scheduling_memory()


def wait_until_num_of_hosts_in_state(num_of_hosts, timeout,
                                     sleep, cluster_name,
                                     state=ENUMS['host_state_up']):
    """
    Wait until number of hosts will have specific state

    :param num_of_hosts: Wait until number of hosts will have some state
    :type num_of_hosts: int
    :param timeout: Timeout in seconds
    :type timeout: int
    :param sleep: Time between samples in seconds
    :type sleep: int
    :param cluster_name: hosts on this cluster
    :type cluster_name: str
    :param state: Expected state of hosts
    :type state: str
    :return: True, if engine have given number of hosts in given state,
     otherwise False
    :rtype: bool
    """
    cluster_obj = CL_API.find(cluster_name)
    sampler = TimeoutingSampler(timeout, sleep, HOST_API.get, absLink=False)
    try:
        for sample in sampler:
            count = 0
            for host in sample:
                if host.get_cluster().get_id() == cluster_obj.get_id():
                    if host.get_status().get_state().lower() == state:
                        count += 1
            if count == num_of_hosts:
                return True
    except APITimeout:
        HOST_API.logger.error(
            "Timeout when waiting for number of hosts %d in state %s",
            num_of_hosts, state
        )
        return False


def get_host_free_memory(host_name):
    """
    Get host free memory

    :param host_name: host name
    :type host_name: str
    :returns: total host free memory
    :rtype: int
    """
    stats = getStat(host_name, ELEMENT, COLLECTION, ["memory.free"])
    return stats["memory.free"]


def get_host_nic_statistics(host, nic):
    """
    Get HOST NIC statistics collection

    :param host: Host name
    :type host: str
    :param nic: NIC name
    :type nic: str
    :return: VM NIC statistics list
    :rtype: list
    """
    host_nic = getHostNic(host, nic)
    return HOST_NICS_API.getElemFromLink(
        host_nic, link_name="statistics", attr="statistic"
    )


def get_numa_nodes_from_host(host_name):
    """
    Get list of host numa nodes objects

    :param host_name: name of host
    :type host_name: str
    :returns: list of NumaNode objects
    :rtype: list
    """
    host_obj = get_host_object(host_name)
    return HOST_API.getElemFromLink(host_obj, "numanodes", "host_numa_node")


def get_numa_node_memory(numa_node_obj):
    """
    Get numa node memory

    :param numa_node_obj: object of NumaNode
    :type numa_node_obj: instance of NumaNode
    :returns: total amount of memory of numa node
    :rtype: int
    """
    return numa_node_obj.get_memory()


def get_numa_node_cpus(numa_node_obj):
    """
    Get numa node cpu's

    :param numa_node_obj: object of NumaNode
    :type numa_node_obj: instance of NumaNode
    :returns: list of cores indexes of numa node
    :rtype: list
    """
    cores = []
    numa_node_cpus = numa_node_obj.get_cpu()
    if numa_node_cpus:
        numa_node_cores = numa_node_cpus.get_cores().get_core()
        cores = [numa_node_core.index for numa_node_core in numa_node_cores]
    return cores


def get_numa_node_index(numa_node_obj):
    """

    :param numa_node_obj: object of NumaNode
    :type numa_node_obj: instance of NumaNode
    :returns: index of numa node
    :rtype: int
    """
    return numa_node_obj.get_index()


def get_numa_node_statistics(numa_node_obj):
    """
    Get numa node statistics

    :param numa_node_obj: object of NumaNode
    :type numa_node_obj: instance of NumaNode
    :returns: dictionary of numa node statistics
    :rtype: dict
    """
    numa_statistics = {}
    statistics = numa_node_obj.get_statistics()
    for statistic in statistics:
        numa_statistics[statistic.name] = []
        for value in statistic.values:
            numa_statistics[statistic.name].append(value.datum)
    return numa_statistics


def get_numa_node_by_index(host_name, index):
    """
    Get numa node by index

    :param host_name: name of host
    :type host_name: str
    :param index: index of numa node
    :type index: int
    :returns: NumaNode object or None
    :rtype: instance of NumaNode or None
    """
    numa_nodes = get_numa_nodes_from_host(host_name)
    for numa_node in numa_nodes:
        if numa_node.index == index:
            return numa_node
    return None


def get_num_of_numa_nodes_on_host(host_name):
    """
    Get number of numa nodes that host has

    :param host_name: name of host
    :type host_name: str
    :returns: number of numa nodes
    :rtype: int
    """
    return len(get_numa_nodes_from_host(host_name))


def get_numa_nodes_indexes(host_name):
    """
    Get list of host numa indexes

    :param host_name: name of host
    :type host_name: str
    :returns: list of host numa indexes
    :rtype: list
    """
    return [
        get_numa_node_index(
            node_obj
        ) for node_obj in get_numa_nodes_from_host(host_name)
    ]


def upgrade_host(host_name, image=None):
    """
    Upgrade host

    :param host_name: Name of the host to be upgraded
    :type host_name: str
    :param image: Image to use in upgrading host (RHEV-H only)
    :type image: str
    :return: True if host was upgraded, otherwise False
    :rtype: bool
    """
    host = HOST_API.find(host_name)
    if bool(
        HOST_API.syncAction(
            host,
            'upgrade',
            True,
            image=image,
        )
    ):
        return waitForHostsStates(True, [host_name], states='up')

    return False


def is_upgrade_available(host_name):
    """
    Check if upgrade is available for host

    :param host_name: Name of the host to be upgraded
    :type host_name: str
    :return: True if upgrade is available for host, otherwise False
    :rtype: bool
    """
    return bool(HOST_API.find(host_name).get_update_available())


def get_host_vm_run_on(vm_name):
    """
    Return host address where vm run

    :param vm_name: name of vm
    :type vm_name: str
    :return: address of the host where vm run
    :rtype: str
    """
    vm_obj = VM_API.find(vm_name)
    return HOST_API.find(vm_obj.host.id, 'id').get_address()


def wait_for_host_spm(host_name, timeout=HOST_STATE_TIMEOUT, sleep=10):
    """
    Wait until host will be SPM

    :param host_name: host name
    :type host_name: str
    :param timeout: sampler timeout
    :type timeout: int
    :param sleep: sampler sleep
    :type sleep: int
    :return: True, if host receive SPM, before timeout, otherwise False
    :rtype: bool
    """
    sampler = TimeoutingSampler(
        timeout, sleep, checkHostSpmStatus, True, host_name
    )
    HOST_API.logger.info("Wait until host %s will be SPM", host_name)
    try:
        for sample in sampler:
            HOST_API.logger.info(
                "Host %s SPM state equal to %s", host_name, sample
            )
            if sample:
                return True
    except APITimeout:
        HOST_API.logger.error("Host %s still not SPM", host_name)
        return False


def get_host_cpu_load(host_name):
    """
    Get host cpu load

    :param host_name: host name
    :type host_name: str
    :return: host current cpu load
    :rtype: float
    """
    stats = getStat(host_name, ELEMENT, COLLECTION, ["cpu.current.user"])
    return stats["cpu.current.user"]


def wait_for_host_cpu_load(
    host_name, expected_min_load=0,
    expected_max_load=100, timeout=120, sleep=10
):
    """
    Wait until host reach cpu load between minimal and maximal values

    :param host_name: host name
    :type host_name: str
    :param expected_min_load: wait for host cpu load greater
    than expected minimum value
    :type expected_min_load: int
    :param expected_max_load: wait for host cpu load smaller
    than expected maximum value
    :type expected_max_load: int
    :param timeout: sampler timeout
    :type timeout: int
    :param sleep: sampler sleep
    :type sleep: int
    :return: True, if host reach cpu load between expected minimal and
    maximal values before timeout, otherwise False
    :rtype: bool
    """
    sampler = TimeoutingSampler(
        timeout, sleep, get_host_cpu_load, host_name
    )
    HOST_API.logger.info(
        "Wait until host %s will have cpu load between %d and %d",
        host_name, expected_min_load, expected_max_load
    )
    try:
        for sample in sampler:
            HOST_API.logger.info(
                "Host %s cpu load equal to %d", host_name, sample
            )
            if expected_max_load >= sample >= expected_min_load:
                return True
    except APITimeout:
        HOST_API.logger.error(
            "Host %s cpu load not between expected values %d and %d",
            expected_min_load, expected_max_load
        )
        return False
