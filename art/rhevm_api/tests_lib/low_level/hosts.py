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
import logging
from utilities.utils import getIpAddressByHostName, getHostName
from utilities import machine
from art.core_api.apis_utils import TimeoutingSampler, data_st
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from art.core_api.apis_utils import getDS
from art.test_handler import settings
from art.rhevm_api.utils.test_utils import (
    get_api, split, getStat, searchElement, searchForObj, stopVdsmd,
    startVdsmd
)
from art.rhevm_api.tests_lib.low_level.networks import (
    get_cluster_network, create_properties
)
from art.rhevm_api.tests_lib.low_level.datacenters import (
    waitForDataCenterState
)
from art.rhevm_api.tests_lib.low_level.vms import (
    stopVm, getVmHost, get_vm_state
)
import art.rhevm_api.tests_lib.low_level.general as ll_general

ELEMENT = "host"
COLLECTION = "hosts"
HOST_API = get_api(ELEMENT, COLLECTION)

VM_API = get_api("vm", "vms")
TAG_API = get_api("tag", "tags")
EVENT_API = get_api("event", "events")
AGENT_API = get_api("agent", "agents")
CL_API = get_api("cluster", "clusters")
CAP_API = get_api("version", "capabilities")
DC_API = get_api("data_center", "datacenters")
HOST_NICS_API = get_api("host_nic", "host_nics")

Host = getDS("Host")
Options = getDS("Options")
Option = getDS("Option")
PowerManagement = getDS("PowerManagement")
PmProxyTypes = getDS("PmProxyTypes")
PmProxy = getDS("PmProxy")
PmProxies = getDS("PmProxies")
Agent = getDS("Agent")
Agents = getDS("Agents")
Tag = getDS("Tag")

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

VIRSH_CMD = ["virsh", "-r"]
VDSM_MAC_SPOOFING = "vdsm-no-mac-spoofing"
NWF_XML_FILE = RHEVM_UTILS["NWFILTER_DUMPXML"]
MAC_SPOOF_LINES = [
    "<filterref filter='no-mac-spoofing'/>",
    "<filterref filter='no-arp-mac-spoofing'/>"
]
FENCE_AGENT = "fence agent"
logger = logging.getLogger("art.ll_lib.hosts")


def get_host_list():
    hostUtil = get_api('host', 'hosts')
    return hostUtil.get(absLink=False)


def get_host_status(host):
    """
    Description: Returns a host's status
    Author: cmestreg
    Parameters:
        * host - host to check
    Return: Returns the host's status [str] or raises EntityNotFound
    """
    return HOST_API.find(host).get_status()


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
    host_status = get_host_status(host)

    return (host_status == ENUMS['host_state_up']) == positive


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


def waitForHostsStates(
    positive, names, states='up', timeout=HOST_STATE_TIMEOUT,
    stop_states=[ENUMS['host_state_install_failed']]
):
    """
    Wait until all of the hosts identified by names exist and have the desired
    status declared in states.

    Args:
        positive (bool): Expected result.
        timeout (int): Timeout for sampler.
        stop_states (str): Host state that the function will exit on.
        names (str): A comma separated names of the hosts.
        states (str): A state of the hosts to wait for.

    Returns:
        bool: True if hosts are in states, False otherwise.
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
                    logger.info(
                        "Check if host %s has state %s", host.name, states
                    )
                    if host.get_status() in stop_states:
                        logger.error(
                            "Host %s state: %s", host.name, host.get_status()
                        )
                        return False

                    elif host.get_status() == states:
                        logger.info(
                            "Host %s has state %s", host.name, states
                        )
                        ok += 1

                    if ok == number_of_hosts:
                        return True

    except APITimeout:
        HOST_API.logger.error(
            "Timeout waiting for hosts (%s) in state %s", names, states
        )
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
        host = Host(name=name, cluster=hostCl, address=host_address, **kwargs)

        logger.info("Adding host %s to cluster %s", name, cluster)
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


def updateHost(positive, host, **kwargs):
    """
    Update properties of existed host (provided in parameters)

    Args:
        positive (bool): Expected result for update host.
        host (str): Name of a target host.
        kwargs (dict): kwargs for update host.

    Keyword Arguments:
        name (str): Host name to change to.
        address (str): Host address to change to.
        root_password (str): Host password to change to.
        cluster (str): Host cluster to change to.
        pm (bool): Host power management to change to.
        pm_type (str): Host pm type to change to.
        pm_address (str): Host pm address to change to.
        pm_username (str): Host pm username to change to.
        pm_password (str): Host pm password to change to.
        pm_port (int): Host pm port to change to.
        pm_secure (bool): Host pm security to change to.
        pm_automatic (bool): Host automatic_pm_enabled flag
        agents (dict): if you have number of pm's, need to specify it
            under agents.

    Returns:
        bool: True if host was updated properly, False otherwise.
    """

    log_info, log_error = ll_general.get_log_msg(
        action="Update", obj_type="host", obj_name=host,
        positive=positive, **kwargs
    )
    logger.info(log_info)
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

    if 'spm_priority' in kwargs:
        new_priority = kwargs.pop('spm_priority')
        host_upd.set_spm(data_st.Spm(new_priority))

    pm_enabled = kwargs.get('pm')
    if pm_enabled is not None:
        pm_automatic = kwargs.get('pm_automatic')
        pm_proxies = kwargs.get('pm_proxies')
        if pm_proxies:
            pm_proxies_list = [PmProxy(type_=proxy) for proxy in pm_proxies]
            pm_proxies = PmProxies(pm_proxy=pm_proxies_list)

        host_pm = PowerManagement(
            enabled=pm_enabled,
            pm_proxies=pm_proxies,
            automatic_pm_enabled=pm_automatic
        )

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
    if not status:
        logger.error(log_error)
    return status


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


def activateHost(positive, host, wait=True):
    """
    Activate host (set status to UP)

    __author__: edolinin

    Args:
        positive (bool): Expected result
        host (str): Name of a host to be activated
        wait (bool): Wait for host to be up

    Returns:
        bool: True if host was activated properly, False otherwise
    """
    host_obj = HOST_API.find(host)
    logger.info("Activate host %s", host)
    status = bool(HOST_API.syncAction(host_obj, "activate", positive))

    if status and wait and positive:
        test_host_status = HOST_API.waitForElemStatus(host_obj, "up", 200)
    else:
        test_host_status = True

    res = status and test_host_status
    if not res:
        logger.error("Failed to activate host %s", host)
    return res


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


def isHostInMaintenance(positive, host):
    """
    Description: Checks if host is in maintenance state
    Author: ratamir
    Parameters:
        * host - name of host to check
    Return: positive if host is up, False otherwise
    """
    try:
        host_status = get_host_status(host)
    except EntityNotFound:
        return False

    return (host_status == ENUMS['host_state_maintenance']) == positive


def deactivateHost(
    positive, host, expected_status=ENUMS['host_state_maintenance'],
    timeout=300
):
    """
    Check host state for SPM role, for 'timeout' seconds, and deactivate it
    if it is not contending to SPM. (set status to MAINTENANCE)

    __author__: jhenner

    Args:
        positive (bool): Expected result
        host (str): The name of a host to be deactivated.
        expected_status (str): The state to expect the host to remain in.
        timeout (int): Time interval for checking if the state is changed

    Returns:
        bool: True if host was deactivated properly and positive,
            False otherwise
    """
    host_obj = HOST_API.find(host)
    sampler = TimeoutingSampler(
        timeout, 1, lambda x: x.get_spm().status, host_obj
    )

    logger.info("Deactivate host %s", host)
    for sample in sampler:
        if not sample == ENUMS['spm_state_contending']:
            if not HOST_API.syncAction(host_obj, "deactivate", positive):
                return False

            # If state got changed, it may be transitional
            # state so we may want to wait
            # for the final one. If it didn't, we certainly can
            # return immediately.
            host_state = host_obj.get_status()
            get_host_state_again = HOST_API.find(host).get_status()
            state_changed = host_state != get_host_state_again
            if state_changed:
                test_host_status = HOST_API.waitForElemStatus(
                    host_obj, expected_status, 180
                )
                return test_host_status and positive
            else:
                return not positive


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


def commit_network_config(host):
    """
    Save host network configuration

    Args:
        host (str): Name of a host to be committed

    Returns:
        bool: True if host network configuration was saved properly,
            False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Commit", obj_type="network config", obj_name="",
        positive=True, extra_txt="on host %s" % host
    )
    logger.info(log_info)
    host_obj = HOST_API.find(host)
    res = bool(
        HOST_API.syncAction(host_obj, "commitnetconfig", True)
    )
    if not res:
        logger.error(log_error)
    return res


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
    host_in_maintenance = (
        get_host_status(host) == ENUMS['host_state_maintenance']
    )
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
        nic_obj = data_st.HostNic()

    if 'vlan' in kwargs:
        nic_obj.set_vlan(data_st.Vlan(id=kwargs.get('vlan')))
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
        ip_obj = data_st.Ip() if add else nic_obj.get_ip()
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
        slaves = data_st.HostNics()
        for nic in slave_list:
            slaves.add_host_nic(data_st.HostNic(name=nic.strip()))

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


def get_host_nic(host, nic, all_content=False):
    """
    Get host NIC

    Args:
        host (str): Host name
        nic (str): NIC name
        all_content (bool): Get all content in NIC object

    Returns:
        HostNic: Host NIC object

    """
    host_obj = HOST_API.find(host)
    return HOST_API.getElemFromElemColl(
        host_obj, nic, 'nics', 'host_nic', all_content=all_content
    )


def get_host_nics_list(host, all_content=False):
    """
    Get host NICs

    :param host: Host name
    :type host: str
    :param all_content: Get NICs objects with all content
    :type all_content: bool
    :return: Host NICs list
    :rtype: list
    """
    host_obj = HOST_API.find(host)
    logger.info("Get %s NICs list", host)
    return HOST_API.getElemFromLink(
        host_obj, 'nics', 'host_nic', get_href=False, all_content=all_content
    )


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

    host_nic = get_host_nic(host, nic)
    cl_net = get_cluster_network(cluster, network)

    return bool(
        HOST_API.syncAction(host_nic, "attach", positive, network=cl_net)
    )


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

    nic_obj = get_host_nic(host, nic)
    kwargs.update([('nic', nic_obj)])
    nic_new = _prepareHostNicObject(**kwargs)
    nic, status = HOST_NICS_API.update(nic_obj, nic_new, positive)

    return status


# FIXME: network param is deprecated.
def detachHostNic(positive, host, nic, network=None):
    """
    Description: detach network interface card from host
    Author: edolinin
    Parameters:
       * host - name of a host to attach nic to
       * nic - nic name to be detached
    Return: status (True if nic was detach properly from host, False otherwise)
    """
    nicObj = get_host_nic(host, nic)

    return bool(
        HOST_API.syncAction(
            nicObj, "detach", positive, network=nicObj.get_network()
        )
    )


def generate_sn_nic(nic, **kwargs):
    """
    generate a host_nic element of types regular or VLAN

    Args:
        nic (str): NIC name that should be generated

    Keyword Args:
        host (str): Host where nic should be generated
        network (str): Network name
        boot_protocol (str): Static, none or DHCP
        address (str): IP address in case of static protocol
        netmask (str): Netmask in case of static protocol
        gateway (str): Gateway address in case of static protocol

    Returns:
        dict: Dict with host NIC element
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Generate", obj_name=nic, obj_type="SetupNetwork NIC", **kwargs
    )
    logger.info(log_info)
    kwargs.update({'name': nic})
    nic_obj = _prepareHostNicObject(**kwargs)
    if not nic_obj:
        logger.error(log_error)

    return {'host_nic': nic_obj}


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


def checkHostSpmStatus(positive, hostName):
    """
    The function checkHostSpmStatus checking Storage Pool Manager (SPM)
        status of the host.

    Args:
        positive (bool): Expected results
        hostName (str): Host name

    Returns:
        bool: True when the host is SPM status == positive, otherwise return
            False.
    """
    attribute = 'spm'
    host_object = HOST_API.find(hostName)

    if not hasattr(host_object, attribute):
        HOST_API.logger.error(
            "Element host %s doesn't have attribute %s", hostName, attribute
        )
        return False

    spm_status = host_object.get_spm().get_status()
    HOST_API.logger.info(
        "checkHostSpmStatus - SPM Status of host %s is: %s", hostName,
        spm_status
    )
    return (spm_status == 'spm') == positive


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
        if host.get_spm().get_status() == 'spm':
            return True, {'spmHost': host.get_name()}
    return False, {'spmHost': None}


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
                 if host.get_status() in expected_states]
        HOST_API.logger.info('New hosts list is %s',
                             [host.get_name() for host in hosts])

    for host in hosts:
        if cluster_name and cluster_name != CL_API.find(
                host.get_cluster().get_id(),  attribute='id').get_name():
            continue

        if host.get_spm().get_status() != 'spm':
            return True, {'hsmHost': host.get_name()}
    return False, {'hsmHost': None}


def getSPMPriority(hostName):
    """
    Description: Get SPM priority of host
    Author: mbourvin
    Parameters:
    * hostName - name/ip of host
    Return: The SPM priority of the host.
    """

    attribute = 'spm'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                              hostName, attribute)
        return False

    spmPriority = hostObj.get_spm().get_priority()
    HOST_API.logger.info("checkSPMPriority - SPM Value of host %s is %s",
                         hostName, spmPriority)
    return spmPriority


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

    attribute = 'spm'
    hostObj = HOST_API.find(hostName)

    if not hasattr(hostObj, attribute):
        HOST_API.logger.error("Element host %s doesn't have attribute %s",
                              hostName, attribute)
        return False

    # Update host
    HOST_API.logger.info("Updating Host %s priority to %s", hostName,
                         spmPriority)
    updateStat = updateHost(
        positive=positive, host=hostName, spm_priority=spmPriority
    )

    # no need to continue checking what the new priority is in case of
    # negative test
    if not positive:
        return updateStat

    if not updateStat:
        return False

    hostObj = HOST_API.find(hostName)
    new_priority = hostObj.get_spm().get_priority()
    HOST_API.logger.info("setSPMPriority - SPM Value of host %s is set to %s",
                         hostName, new_priority)

    return new_priority == int(spmPriority)


# noinspection PyBroadException
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
        nic_obj = get_host_nic(host, nic)
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
        res, out = getHostNicAttr(host, nic, 'status')
        if res and regex.match(out['attrValue']):
            return True
        time.sleep(interval)
        attempts -= 1
    return False


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


def check_network_filtering(positive, vds_resource):
    """
    Check that network filtering is enabled via VDSM

    Args:
        positive (bool): Expected status
        vds_resource (resource.VDS): VDS resource

    Returns:
        bool: True if network filtering is enabled, False otherwise
    """
    log_txt = "not found" if positive else "found"
    cmd = VIRSH_CMD[:]
    cmd.extend(["nwfilter-list"])
    rc, out, _ = vds_resource.run_command(cmd)
    if rc:
        return False

    if VDSM_MAC_SPOOFING not in out:
        logger.error("%s %s in virsh", VDSM_MAC_SPOOFING, log_txt)
        return not positive

    if not vds_resource.fs.exists(NWF_XML_FILE):
        logger.error("%s.xml file %s", VDSM_MAC_SPOOFING, log_txt)
        return not positive

    if not check_nwfilter_virsh(vds_resource):
        return not positive
    return positive


def check_nwfilter_virsh(vds_resource):
    """
    Checking that NWfilter is enable in dumpxml and in virsh

    Args:
        vds_resource (resource.VDS): VDS resource

    Returns:
        bool: True if all the elements were found, False otherwise
    """
    cmd = VIRSH_CMD[:]
    cmd.extend(["nwfilter-dumpxml", VDSM_MAC_SPOOFING])
    rc1, out1, _ = vds_resource.run_command(["cat", NWF_XML_FILE])
    rc2, out2, _ = vds_resource.run_command(cmd)
    logger.info(
        "Compare %s with running configuration on virsh", NWF_XML_FILE
    )
    if rc1 or rc2:
        return False

    if VDSM_MAC_SPOOFING not in (out1 and out2):
        logger.error(
            "%s and virsh running configuration are not equal", NWF_XML_FILE
        )
        return False
    return True


def check_network_filtering_dumpxml(positive, vds_resource, vm, nics):
    """
    Check that network filtering is enabled via dumpxml

    Args:
        positive (bool): Expected status
        vds_resource (resource.VDS): VDS resource
        vm (str): Name of the vm
        nics (str): Number of NICs for vm in dumpxml

    Returns:
        bool: True if network filtering is enabled, False otherwise
    """
    cmd = VIRSH_CMD[:]
    cmd.extend(["dumpxml", vm])
    log_txt = "all" if positive else "none of"
    rc, out, _ = vds_resource.run_command(cmd)
    logger.info(
        "Check that %s VM NICs have network filter enabled on VM %s",
        log_txt, vm
    )
    if out.count(
            "<filterref filter='vdsm-no-mac-spoofing'/>") != int(nics):
        logger.error(
            "%s VM NICs have network filter enabled on VM %s", log_txt, vm
        )
        return not positive
    return positive


def check_network_filtering_ebtables(host_obj, vm_macs):
    """
    Check that network filtering is enabled via ebtables

    Args:
        host_obj (resources.VDS): Host object.
        vm_macs (list): list of vm_macs.

    Returns:
        bool: True if network filtering is enabled, False otherwise.
    """
    logger.info(
        "Check ebtables rules on host %s for VM MACs %s", host_obj, vm_macs
    )
    cmd = "ebtables -t nat -L"
    rc, output, err = host_obj.run_command(shlex.split(cmd))
    if rc:
        return False

    for mac in vm_macs:
        vm_mac = ":".join(
            [i[1] if i.startswith('0') else i for i in mac.split(':')]
        )
        num_macs_ebtable = output.count(vm_mac)
        if num_macs_ebtable != 2:
            logger.info("%s MACs found instead of 2", num_macs_ebtable)
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


def select_host_as_spm(
    positive, host, data_center, timeout=HOST_STATE_TIMEOUT, sleep=10,
    wait=True
):
    """
    Selects the host to be spm

    Args:
        positive (bool): Expected result
        host (str): Name of a host to be selected as spm
        datacenter (str): Datacenter name
        timeout (int): Timeout to wait for the host to be SPM
        sleep (int): Time to sleep between iterations
        wait (bool): True to wait for spm election to be completed before
            returning (only waits if positive and wait are both true)

    Returns:
        bool: True if host was elected as spm properly, False otherwise
    """
    if not checkHostSpmStatus(True, host):
        host_obj = HOST_API.find(host)
        HOST_API.logger.info('Selecting host %s as SPM', host)
        response = HOST_API.syncAction(host_obj, "forceselectspm", positive)
        if response:
            if positive and wait:
                waitForSPM(data_center, timeout=timeout, sleep=sleep)
                return checkHostSpmStatus(True, host)
            else:
                return positive
        else:
            logger.error("Failed to select host %s as SPM", host)
        return response == positive
    else:
        logger.info("Host %s already SPM", host)
        return positive


def set_host_non_operational_nic_down(host_resource, nic):
    """
    Helper Function for check_vm_migration.
    It puts the NIC with required network down and causes the Host
    to become non-operational

    Args:
        host_resource (Host): Host resource
        nic (str): NIC name with required network.

    Returns:
        bool: True if Host became non-operational by putting NIC down,
            otherwise False
    """
    host_name = get_host_name_from_engine(vds_resource=host_resource)
    if not host_resource.network.if_down(nic=nic):
        return False

    return waitForHostsStates(
        True, names=host_name, states='non_operational', timeout=TIMEOUT * 2
    )


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


def kill_vm_process(resource, vm_name):
    """
    Kill VM process of a given vm

    Args:
        resource (VDS): resource
        vm_name (str): name of VM to kill

    Returns:
        bool: True, if function succeed to kill VM process, otherwise False
    """
    vm_pid = resource.get_vm_process_pid(vm_name=vm_name)
    if not vm_pid:
        logger.error("Failed to get VM pid from resource %s", resource)
        return False
    rc = resource.run_command(['kill', '-9', vm_pid])[0]
    return not bool(rc)


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


def check_host_nic_status(host_resource, nic, status):
    """
    Get NIC status from host

    Args:
        host_resource (Host): Host resource
        nic (str): Host NIC name
        status (str): Status to check for

    Returns:
        bool: True/False
    """
    logger.info("Check if host NIC %s status is %s", nic, status)
    status = "yes" if status.lower() == "up" else "no"
    cmd = ["ethtool", nic]
    rc, out, _ = host_resource.run_command(cmd)
    if not rc:
        return False

    cmd_out = out.rsplit("\r\n\t", 1)[1].split(":")[-1].strip()
    nic_status = cmd_out.lower()
    if nic_status == status:
        logger.error(
            "Host NIC %s status is %s. Should be %s", nic, nic_status, status
        )
        return True
    return False


def wait_for_host_nic_status(
    host_resource, nic, status, interval=1, attempts=1
):
    """
    Wait for host NIC status

    Args:
        host_resource (Host): Host resource
        nic (str): Host NIC name
        status (str): Status to check for
        interval (int): Time to sleep between attempts
        attempts (int): How many attempts before return False

    Returns:
        bool: True/False
    """
    sample = TimeoutingSampler(
        timeout=attempts, sleep=interval, func=check_host_nic_status,
        host_resource=host_resource, nic=nic, status=status
    )
    return sample.waitForFuncStatus(result=True)


def get_host_name_from_engine(vds_resource):
    """
    Get host name from engine by host IP

    Args:
        vds_resource (VDS): resources.VDS object

    Returns:
        str: Host name or None
    """

    engine_hosts = HOST_API.get(absLink=False)
    for host in engine_hosts:
        if (
            host.get_address() == vds_resource.fqdn or host.get_address() ==
            vds_resource.ip or host.name == vds_resource.fqdn
        ):
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

    Args:
        host (str): Host name
        start_event_id (str): Event id to search from

    Returns:
        bool: True/False
    """
    host_obj = HOST_API.find(host)
    code = [606, 607]
    query = "type={0} OR type={1}".format(code[0], code[1])
    HOST_API.syncAction(entity=host_obj, action="refresh", positive=True)
    logger.info("Refresh capabilities for %s", host)
    for event in EVENT_API.query(query):
        if int(event.get_id()) < int(start_event_id):
            return False
        if event.get_code() in code:
            return True if event.get_code() == code[0] else False

    logger.error("Failed to refresh capabilities for: %s", host)
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
                if host.get_status() == host_status]
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
    host_nic = get_host_nic(host, nic)
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


def get_fence_agents_list(host_name):
    """
    Get host fence agents collection

    Args:
        host_name (str): Host name

    Returns:
        list: Agent objects
    """
    host_obj = get_host_object(host_name)
    logger.info("Get host %s fence agents collection", host_name)
    return HOST_API.getElemFromLink(host_obj, 'fenceagents', 'agent')


def get_fence_agents_link(host_name):
    """
    Get host fence agents collection link

    Args:
        host_name (str): Host name

    Returns:
        str: Link to fence agents collection
    """
    host_obj = get_host_object(host_name)
    logger.info("Get host %s fence agents link", host_name)
    return HOST_API.getElemFromLink(host_obj, 'fenceagents', get_href=True)


def get_fence_agent_by_address(host_name, agent_address):
    """
    Get fence agent by address

    Args:
        host_name (str): Host name
        agent_address (str): Agent address

    Returns:
        Agent: Instance of Agent
    """
    agents = get_fence_agents_list(host_name=host_name)
    logger.info("Search for fence agent with address %s", agent_address)
    for agent in agents:
        if agent.get_address() == agent_address:
            return agent
    logger.error(
        "Failed to find fence agent with address % under host %s",
        agent_address, host_name
    )
    return None


def __prepare_fence_agent_object(**kwargs):
    """
    Prepare fence agent object

    Keyword Arguments:
        type_ (str): Agent type
        address (str): Agent address
        username (str): Agent user
        password (str): Agent password
        concurrent (bool): Agent concurrent use
        order (int): Agent use order
        port (int): Agent port
        secure (bool): Secure connection to agent
        options (dict): Agent options

    Returns:
        Agent: Instance of agent
    """
    options_obj = None
    options = kwargs.pop("options", None)
    if options:
        options_obj = Options()
        for name, value in options.iteritems():
            option = Option(name=name, value=value)
            options_obj.add_option(option)
    agent_obj = ll_general.prepare_ds_object("Agent", **kwargs)
    agent_obj.set_options(options_obj)
    return agent_obj


def add_fence_agent(
    host_name,
    agent_type,
    agent_address,
    agent_username,
    agent_password,
    concurrent=False,
    order=1,
    **kwargs
):
    """
    Add fence agent to host

    Args:
        host_name (str): Host name
        agent_type (str): Agent type
        agent_address (str): Agent address
        agent_username (str): Agent user
        agent_password (str): Agent password
        concurrent (bool): Agent concurrent use
        order (int): Agent use order

    Keyword Arguments:
        port (int): Agent port
        secure (bool): Secure connection to agent
        options (dict): Agent options

    Returns:
        bool: True if add fence agent succeed, otherwise False
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Add", obj_type=FENCE_AGENT, obj_name=agent_address,
        extra_txt="to host %s" % host_name
    )
    agent_obj = __prepare_fence_agent_object(
        type_=agent_type,
        address=agent_address,
        username=agent_username,
        password=agent_password,
        concurrent=concurrent,
        order=order,
        **kwargs
    )
    agents_link = get_fence_agents_link(host_name=host_name)
    logger.info(log_info)
    status = AGENT_API.create(
        entity=agent_obj, positive=True, collection=agents_link
    )[1]
    if not status:
        logger.info(log_error)
    return status


def update_fence_agent(host_name, agent_address, **kwargs):
    """
    Update fence agent

    Args:
        host_name (str): Host name
        agent_address (str): Update agent with address

    Keyword Args:
        agent_type (str): Agent type
        agent_address (str): Agent address
        agent_username (str): Agent user
        agent_password (str): Agent password
        concurrent (bool): Agent concurrent use
        order (int): Agent use order
        port (int): Agent port
        secure (bool): Secure connection to agent
        options (dict): Agent options

    Returns:
        bool: True, if fence agent update succeed, otherwise False
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Update", obj_type=FENCE_AGENT, obj_name=agent_address,
        extra_txt="on host %s" % host_name
    )
    old_agent_obj = get_fence_agent_by_address(
        host_name=host_name, agent_address=agent_address
    )
    new_agent_obj = __prepare_fence_agent_object(**kwargs)
    logger.info(log_info)
    status = AGENT_API.update(old_agent_obj, new_agent_obj, True)[1]
    if not status:
        logger.info(log_error)
    return status


def remove_fence_agent(fence_agent_obj):
    """
    Remove fence agent object

    Args:
        fence_agent_obj (Agent): instance of Agent

    Returns:
        bool: True, if remove succeed, otherwise False
    """
    agent_address = fence_agent_obj.get_address()
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type=FENCE_AGENT, obj_name=agent_address
    )
    logger.info(log_info)
    status = AGENT_API.delete(entity=fence_agent_obj, positive=True)
    if not status:
        logger.info(log_error)
    return status


def get_host_cores(host_name):
    """
    Get the host cores number

    :param host_name: host name
    :type host_name: str
    :return: number of host cores
    :rtype: int
    """
    cores = get_host_topology(host_name).cores
    if cores:
        return cores
    logger.error("Failed to get cpu cores from %s", host_name)
    return 0


def get_host_sockets(host_name):
    """
    Get the host sockets number

    :param host_name: host name
    :type host_name: str
    :return: number of host sockets
    :rtype: int
    """
    sockets = get_host_topology(host_name).sockets
    if sockets:
        return sockets
    logger.error("Failed to get cpu sockets from %s", host_name)
    return 0


def get_host_threads(host_name):
    """
    Get the host sockets number

    :param host_name: host name
    :type host_name: str
    :return: number of host threads
    :rtype: int
    """
    threads = get_host_topology(host_name).threads
    if threads:
        return threads
    logger.error("Failed to get cpu threads from %s", host_name)
    return 0


def get_host_processing_units_number(host_name):
    """
    Get the host processing units number
    ( sockets * cores * threads )

    :param host_name: host name
    :type host_name: str
    :return: number of host processing units
    :rtype: int
    """
    return (
        get_host_cores(host_name) *
        get_host_sockets(host_name) *
        get_host_threads(host_name)
    )


def get_host_devices(host_name):
    """
    Get all host devices

    Args:
        host_name (str): Host name

    Returns:
        list: All host devices
    """
    host_obj = HOST_API.find(host_name)
    logger.info("Get all devices from host %s", host_name)
    return HOST_API.getElemFromLink(host_obj, "devices", "host_device")


def get_host_device_by_name(host_name, device_name):
    """
    Get host device object by device name

    Args:
        host_name (str): Host name
        device_name (str): Device name

    Returns:
        HostDevice: Instance of HostDevice
    """
    host_devices = get_host_devices(host_name=host_name)
    logger.info(
        "Get host device with name %s from host %s", device_name, host_name
    )
    host_devices = filter(
        lambda host_device: host_device.get_name() == device_name, host_devices
    )
    if not host_devices:
        logger.error(
            "Failed to find host device with name %s under host %s",
            device_name, host_name
        )
        return None
    return host_devices[0]


def get_host_device_id_by_name(host_name, device_name):
    """
    Get host device id by name

    Args:
        host_name (str): Host name
        device_name (str): Device name

    Returns:
        str: Device id
    """
    host_device_obj = get_host_device_by_name(
        host_name=host_name, device_name=device_name
    )
    if host_device_obj:
        return host_device_obj.get_id()
