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

import logging
import shlex
import socket
import time

from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    general as ll_general
)
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from art.core_api.apis_utils import TimeoutingSampler, data_st, getDS
from art.rhevm_api.tests_lib.low_level.datacenters import (
    waitForDataCenterState
)
from art.rhevm_api.tests_lib.low_level.vms import (
    stopVm, get_vm_host, get_vm_state, get_all_vms
)
from art.rhevm_api.utils.test_utils import (
    get_api, getStat, searchElement, searchForObj, stopVdsmd,
    startVdsmd
)
from art.test_handler.settings import ART_CONFIG
from utilities import machine
from utilities.rhevm_tools.errors import ExecuteDBQueryError

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
Value = getDS("Value")
PowerManagement = getDS("PowerManagement")
PmProxyTypes = getDS("PmProxyTypes")
PmProxy = getDS("PmProxy")
PmProxies = getDS("PmProxies")
Agent = getDS("Agent")
Agents = getDS("Agents")
Tag = getDS("Tag")

SED = '/bin/sed'
SERVICE = '/sbin/service'
ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
RHEVM_UTILS = ART_CONFIG['elements_conf']['RHEVM Utilities']
KSM_STATUSFILE = '/sys/kernel/mm/ksm/run'
HOST_STATE_TIMEOUT = 1000
KSMTUNED_CONF = '/etc/ksmtuned.conf'
MEGABYTE = 1024 ** 2
IP_PATTERN = '10.35.*'
TIMEOUT = 120
TIMEOUT_NON_RESPONSIVE_HOST = 360
SPM_TIMEOUT = 180
FIND_QEMU = 'ps aux |grep qemu | grep -e "-name %s"'

VIRSH_CMD = ["virsh", "-r"]
VDSM_MAC_SPOOFING = "vdsm-no-mac-spoofing"
NWF_XML_FILE = RHEVM_UTILS["NWFILTER_DUMPXML"]
MAC_SPOOF_LINES = [
    "<filterref filter='no-mac-spoofing'/>",
    "<filterref filter='no-arp-mac-spoofing'/>"
]
FENCE_AGENT = "fence agent"

ACTIVATION_MAX_TIME = 300
INSTALLATION_MAX_TIME = 3600
LLDPS = "linklayerdiscoveryprotocolelements"
LLDP = "link_layer_discovery_protocol_element"

logger = logging.getLogger("art.ll_lib.hosts")


def get_host_list():
    """
    Get list of all hosts

    Returns:
        list: List of host objects
    """
    return HOST_API.get(abs_link=False)


def get_host_names_list():
    """
    Get list of all host names

    Returns:
        list: List of host names(string)
    """
    return [host.get_name() for host in get_host_list()]


@ll_general.generate_logs()
def get_host_status(host):
    """
    Returns host status

    Args:
        host (str): Host name

    Returns:
        str: Host status

    Raises:
        EntityNotFound: If host not found
    """
    return get_host_object(host_name=host).get_status()


@ll_general.generate_logs()
def get_host_ip(host):
    """
    Get IP of a host with given name in RHEVM

    Args:
        host (str): Host name in rhevm to check

    Returns:
        str: Host IP

    Raises:
        EntityNotFound: If host not found
    """
    return get_host_object(host_name=host).get_address()


@ll_general.generate_logs()
def get_host_cluster(host):
    """
    Get the name of the cluster that contains the host

    Args:
        host (str): host name

    Returns:
        str: Cluster name

    Raises:
        EntityNotFound: If host not found
    """
    host_obj = get_host_object(host_name=host)
    cluster = CL_API.find(host_obj.get_cluster().get_id(), attribute='id')
    return cluster.get_name()


@ll_general.generate_logs()
def is_host_up(positive, host):
    """
    Checks if host is in state "up"

    Args:
        positive (bool): True if action should succeed, False otherwise
        host (str): Name of the host

    Returns:
        bool: True if host is in state "up", False otherwise
    """
    host_status = get_host_status(host)

    return (host_status == ENUMS['host_state_up']) == positive


def wait_for_hosts_states(
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
        list_names = names.replace(',', ' ').split()
    else:
        list_names = names[:]

    [get_host_object(host_name=host) for host in list_names]
    number_of_hosts = len(list_names)

    sampler = TimeoutingSampler(timeout, 10, HOST_API.get, abs_link=False)

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

                    elif host.get_status() in states:
                        logger.info(
                            "Host %s has state %s", host.name, states
                        )
                        ok += 1

                    if ok == number_of_hosts:
                        return True

    except APITimeout:
        logger.error(
            "Timeout waiting for hosts (%s) in state %s", names, states
        )
        return False


@ll_general.generate_logs()
def add_host(name, address, root_password, wait=True, **kwargs):
    """
    Add new host

    Args:
        name (str): Host name
        address (str): Host FQDN or IP
        root_password (str): Host root password
        wait (bool): Wait until the host will have state UP

    Keyword Args:
        cluster (str): Host cluster name
        override_iptables (bool): Override host iptables
        deploy_hosted_engine (bool): Deploy hosted engine flag

    Returns:
        bool: True, if add action succeeds, otherwise False
    """
    host_cluster = kwargs.pop("cluster", "Default")
    host_cluster = ll_clusters.get_cluster_object(cluster_name=host_cluster)
    deploy_hosted_engine = kwargs.pop("deploy_hosted_engine", False)

    host_obj = Host(
        name=name,
        cluster=host_cluster,
        address=address,
        root_password=root_password,
        **kwargs
    )
    host, status = HOST_API.create(
        entity=host_obj,
        positive=True,
        deploy_hosted_engine=deploy_hosted_engine
    )

    if wait and status:
        return HOST_API.waitForElemStatus(host, status="up", timeout=800)

    return status


@ll_general.generate_logs(step=True)
def update_host(positive, host, **kwargs):
    """
    Update properties of host (provided in parameters)

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
        rng_sources (list of str): Supported random number generator sources

    Returns:
        bool: True if host was updated properly, False otherwise.
    """
    host_obj = get_host_object(host_name=host)
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

    if 'rng_sources' in kwargs:
        host_upd.set_hardware_information(
            data_st.HardwareInformation(
                supported_rng_sources=(
                    data_st.supported_rng_sourcesType(
                        kwargs.pop('rng_sources')
                    )
                )
            )
        )

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
    return status


@ll_general.generate_logs()
def remove_host(positive, host, deactivate=False, force=False):
    """
    Remove existing host

    Args:
        positive (bool): If positive or negative verification should be done
        host (str): Name of a host to be removed
        deactivate (bool): Flag to put host in maintenance before remove
        force (bool): True if the host should be forcefully removed

    Returns:
        bool: If the removal status is same as expected
    """

    host_obj = get_host_object(host_name=host)
    if deactivate:
        if not is_host_in_maintenance(positive, host):
            if not deactivate_host(positive=positive, host=host):
                return False

    operations = ['force=true'] if force else None

    return HOST_API.delete(host_obj, positive, operations=operations)


@ll_general.generate_logs(step=True)
def activate_host(positive, host, wait=True, host_resource=None):
    """
    Activate host (set status to UP)

    Args:
        positive (bool): Expected result
        host (str): Name of a host to be activated
        wait (bool): Wait for host to be up
        host_resource (VDS): Host resource

    Returns:
        bool: True if host was activated properly, False otherwise
    """
    host_obj = get_host_object(host_name=host)
    if not HOST_API.syncAction(host_obj, "activate", positive):
        return False

    if wait and positive:
        if not HOST_API.waitForElemStatus(host_obj, "up", ACTIVATION_MAX_TIME):
            return False

        if host_resource and is_hosted_engine_configured(host_name=host):
            return wait_for_hosted_engine_maintenance_state(
                host_resource=host_resource, enabled=False
            )

    return True


def sort_hosts_by_priority(hosts, reverse=True):
    """
    Sort hosts by priorities, default is DESC order

    Args:
        hosts (str or list): Hosts to be sorted

    Returns:
        list: A list of hosts, sorted by priority (default: DESC)
    """
    if isinstance(hosts, str):
        hosts = hosts.split(',')

    hosts_priorities_dic = {}
    for host in hosts:
        spm_priority = get_spm_priority(host)
        hosts_priorities_dic[host] = spm_priority

    sorted_list = sorted(
        hosts_priorities_dic, key=hosts_priorities_dic.get, reverse=reverse
    )
    logger.info('Sorted hosts list: %s', sorted_list)
    return sorted_list


@ll_general.generate_logs(error=False)
def is_host_in_maintenance(positive, host):
    """
    Checks if host is in maintenance state

    Args:
        host (str): Name of host to check
        positive (bool): Expected results

    Returns:
        bool: positive if host is up, False otherwise
    """
    try:
        host_status = get_host_status(host)
    except EntityNotFound:
        return False

    return (host_status == ENUMS['host_state_maintenance']) == positive


@ll_general.generate_logs(step=True)
def deactivate_host(
    positive, host, expected_status=ENUMS["host_state_maintenance"],
    timeout=None, host_resource=None
):
    """
    Deactivate the host.
    Check host state for SPM role, for 'timeout' seconds, and deactivate it
    if it is not contending to SPM. (set status to MAINTENANCE)

    Args:
        positive (bool): Expected result
        host (str): The name of a host to be deactivated.
        expected_status (str): The state to expect the host to remain in.
        timeout (int): Time interval for checking if the state is changed
        host_resource (VDS): Host resource

    Returns:
        bool: True if host was deactivated properly and positive,
            False otherwise
    """
    host_obj = get_host_object(host_name=host)
    he_host = is_hosted_engine_configured(host_name=host)
    if not timeout:
        timeout = 600 if he_host else 180

    sampler = TimeoutingSampler(
        timeout, 1, lambda x: x.get_spm().status, host_obj
    )

    try:
        for sample in sampler:
            if sample != ENUMS["spm_state_contending"]:
                if not HOST_API.syncAction(host_obj, "deactivate", positive):
                    return False

                if not positive:
                    return True

                if not HOST_API.waitForElemStatus(
                    host_obj, expected_status, timeout
                ):
                    return False

                if host_resource and he_host:
                    return wait_for_hosted_engine_maintenance_state(
                        host_resource=host_resource
                    )

                return True
    except APITimeout:
        logger.error(
            "Timeout waiting for the host %s state different from the %s",
            host, ENUMS["spm_state_contending"]
        )
        return not positive


@ll_general.generate_logs()
def install_host(host, root_password, **kwargs):
    """
    Install host

    Args:
        host (str): Host name
        root_password (str): Host root password

    Keyword Args:
        image (str): RHEV-H image
        override_iptables (bool): Override iptables
        deploy_hosted_engine (bool): Deploy hosted engine flag
        undeploy_hosted_engine (bool): Undeploy hosted engine flag

    Returns:
        bool: True, if host installation succeeds, otherwise False
    """
    override_iptables = kwargs.get("override_iptables", True)
    state_maintenance = ENUMS["host_state_maintenance"]
    state_installing = ENUMS["host_state_installing"]
    host_obj = get_host_object(host_name=host)
    response = HOST_API.syncAction(
        entity=host_obj,
        action="install",
        positive=True,
        root_password=root_password,
        override_iptables=override_iptables,
        **kwargs
    )
    if not (
        response and HOST_API.waitForElemStatus(
            host_obj, status=state_installing, timeout=120
        )
    ):
        return False
    return HOST_API.waitForElemStatus(
        host_obj, status=state_maintenance, timeout=800
    )


@ll_general.generate_logs()
def commit_network_config(host):
    """
    Save host network configuration

    Args:
        host (str): Name of a host to be committed

    Returns:
        bool: True if host network configuration was saved properly,
            False otherwise
    """
    host_obj = get_host_object(host_name=host)
    return bool(
        HOST_API.syncAction(host_obj, "commitnetconfig", True)
    )


@ll_general.generate_logs()
def fence_host(host, fence_type, timeout=500, wait_for_status=True):
    """
    Fence host

    Args:
        host (str): Host name
        fence_type (str): Fence type(start/stop/restart/status/manual)
        timeout (int): Wait for the host status timeout
        wait_for_status (bool): Wait for the host status
            after the fence command

    Returns:
        bool: True, if fence action succeeds and host receives expected state
            before timeout, otherwise False
    """
    host_obj = get_host_object(host_name=host)
    host_in_maintenance = (
        get_host_status(host=host) == ENUMS['host_state_maintenance']
    )
    status = HOST_API.syncAction(
        entity=host_obj,
        action="fence",
        positive=True,
        fence_type=fence_type.upper()
    )
    if not (wait_for_status and status):
        return status

    if fence_type in ("restart", "start"):
        status = "maintenance" if host_in_maintenance else "up"

    elif fence_type == "stop":
        status = "down"
    else:
        return True

    return HOST_API.waitForElemStatus(
        host_obj, status=status, timeout=timeout
    )


@ll_general.generate_logs()
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
    host_nics = get_host_nics_list(host=host, all_content=all_content)
    nic = filter(lambda x: nic == x.name, host_nics)
    return nic[0] if nic else None


@ll_general.generate_logs()
def get_host_nics_list(host, all_content=False):
    """
    Get host NICs

    Args:
        host (str): Host name
        all_content (bool): Get NICs objects with all content

    Returns:
        list: Host NICs list
    """
    host_obj = get_host_object(host_name=host)
    return HOST_API.getElemFromLink(
        host_obj, 'nics', 'host_nic', get_href=False, all_content=all_content
    )


@ll_general.generate_logs()
def search_for_host(positive, query_key, query_val, key_name=None, **kwargs):
    """
    Search for a host by desired property

    Args:
        positive (bool): Expected results
        query_key (str): Name of property to search for
        query_val (str): Value of the property to search for
        key_name (str): Name of the property in host object equivalent to
            query_key

    Returns:
        bool: True if expected number of hosts equal to found by search,
            False otherwise
    """
    return searchForObj(HOST_API, query_key, query_val, key_name, **kwargs)


@ll_general.generate_logs()
def reboot_host(host):
    """
    Rebooting host via ssh session

    Args:
        host (Host): Host resource

    Returns:
        bool: True if host was rebooted successfully, False otherwise
    """
    host_name = get_host_name_from_engine(vds_resource=host)
    rc = host.run_command(cmd=["reboot"])[0]
    if not rc:
        return False

    return wait_for_hosts_states(
        True, host_name, ENUMS['host_state_non_responsive'],
        TIMEOUT_NON_RESPONSIVE_HOST,
    )


@ll_general.generate_logs()
def run_delayed_control_service(
    positive, host, host_user, host_passwd, service, command='restart',
    delay=0
):
    """
    Restarts a service on the host after a delay

    Args:
        positive (bool): Expected results
        host (str): IP or fqdn of the host
        host_user (str):  User name for the host
        host_passwd (str): - Password for the user
        service (str): The name of the service (eg. vdsmd)
        command (str): Command to issue (eg. start/stop/restart)
        delay (int): The required delay in seconds

    Returns:
        bool: True if the command is sent successfully, False otherwise,
            or inverted in case of negative test
    """
    # TODO: Implement bg in Host.executor
    cmd = (
        '( sleep %d; service %s %s 1>/dev/null; echo $? )'
        % (delay, service, command)
    )
    host_obj = machine.Machine(
        host, host_user, host_passwd
    ).util(machine.LINUX)
    output = host_obj.runCmd(
        cmd.split(), bg=('/tmp/delayed-stdout', '/tmp/delayed-stderr')
    )
    return output[0] == positive


@ll_general.generate_logs()
def add_tag_to_host(positive, host, tag):
    """
    Add tag to a host

    Args:
        positive (bool): Expected results
        host (str): Name of a host to add a tag to
        tag (str): Tag name that should be added

    Returns:
        bool: True if tag was added properly, False otherwise
    """
    host_obj = get_host_object(host_name=host)
    tag_obj = Tag(name=tag)
    host_tags = HOST_API.getElemFromLink(
        host_obj, link_name='tags', attr='tag', get_href=True
    )
    return TAG_API.create(tag_obj, positive, collection=host_tags)[1]


@ll_general.generate_logs()
def remove_tag_from_host(positive, host, tag):
    """
    Remove tag from a host

    Args:
        positive (bool): Expected results
        host (str): Name of a host to remove a tag from
        tag (str): Tag name that should be removed

    Returns:
        bool: True if tag was removed properly, False otherwise
    """
    host_obj = get_host_object(host_name=host)
    tag_obj = HOST_API.getElemFromElemColl(host_obj, tag, 'tags', 'tag')
    if tag_obj:
        return HOST_API.delete(tag_obj, positive)
    else:
        logger.error("Tag {0} is not found at host {1}".format(tag, host))
        return False


@ll_general.generate_logs()
def check_host_spm_status(positive, host):
    """
    Checking Storage Pool Manager (SPM) status of the host.

    Args:
        positive (bool): Expected results
        host (str): Host name

    Returns:
        bool: True when the host is SPM status == positive, otherwise return
            False.
    """
    attribute = 'spm'
    host_object = get_host_object(host_name=host)

    if not hasattr(host_object, attribute):
        logger.error(
            "Element host %s doesn't have attribute %s", host, attribute
        )
        return False
    spm_status = host_object.get_spm().get_status()
    logger.info(
        "check_host_spm_status - SPM Status of host %s is: %s", host,
        spm_status
    )
    return (spm_status == 'spm') == positive


@ll_general.generate_logs()
def get_any_non_spm_host(hosts, expected_states=None, cluster_name=None):
    """
    Get any not SPM host from the list of hosts in the expected state

    Args:
        hosts (list): The list of hosts to be searched through
        expected_states (list): List of states to filter hosts by. Set to
            None to disable filtering by host state
        cluster_name (str): Filter for hosts belonging to a specific cluster

    Returns:
        tuple: (bool, dict() with HSM host name)
    """
    if isinstance(hosts, str):
        hosts = hosts.split(',')

    hosts = [get_host_object(host_name=host) for host in hosts]

    if expected_states:
        logger.info(
            'Filtering host list for hosts in states %s', expected_states
        )
        hosts = [
            host for host in hosts if host.get_status() in expected_states
        ]
        logger.info(
            'New hosts list is %s', [host.get_name() for host in hosts]
        )

    for host in hosts:
        if cluster_name and cluster_name != CL_API.find(
                host.get_cluster().get_id(),  attribute='id').get_name():
            continue

        if host.get_spm().get_status() != 'spm':
            return True, {'hsmHost': host.get_name()}
    return False, {'hsmHost': None}


def get_spm_priority(host):
    """
    Get SPM priority of host

    Args:
        host (str): Name/ip of host

    Returns:
        str: The SPM priority of the host.
    """
    attribute = 'spm'
    host_obj = get_host_object(host_name=host)

    if not hasattr(host_obj, attribute):
        logger.error(
            "Element host %s doesn't have attribute %s", host, attribute
        )
        return False

    spm_priority = host_obj.get_spm().get_priority()
    logger.info(
        "check_spm_priority - SPM Value of host %s is %s", host, spm_priority
    )
    return spm_priority


@ll_general.generate_logs()
def check_spm_priority(positive, host, expected_priority):
    """
    Check SPM priority of host

    Args:
        positive (bool): Expected results
        host (str): nName/ip of host
        expected_priority (str): Expected value of SPM priority on host

    Returns:
        True if SPM priority value is equal to expected value.
            False in other case.
    """
    spm_priority = get_spm_priority(host)

    return str(spm_priority) == expected_priority


def set_spm_priority(positive, host, spm_priority):
    """
    Set SPM priority on host

    Args:
        positive (bool): Expected results
        host (str): Name/ip of host
        spm_priority (str): Expecded value of SPM priority on host

    Returns:
        True if spm value is set OK. False in other case.
    """
    attribute = 'spm'
    host_obj = get_host_object(host_name=host)

    if not hasattr(host_obj, attribute):
        logger.error(
            "Element host %s doesn't have attribute %s", host, attribute
        )
        return False

    # Update host
    logger.info("Updating Host %s priority to %s", host, spm_priority)
    update_stat = update_host(
        positive=positive, host=host, spm_priority=spm_priority
    )

    # no need to continue checking what the new priority is in case of
    # negative test
    if not positive:
        return update_stat

    if not update_stat:
        return False

    new_priority = get_spm_priority(host=host)
    logger.info(
        "set_spm_priority - SPM Value of host %s is set to %s", host,
        new_priority
    )

    return new_priority == int(spm_priority)


# noinspection PyBroadException
@ll_general.generate_logs()
def set_spm_priority_in_db(host_name, spm_priority, engine):
    """
    Set SPM priority for host in DB

    Args:
        host_name (str): The name of the host
        spm_priority (int): SPM priority to be set for host
        engine (Engine): Engine machine

    Returns
        bool: True if update of db success, otherwise False
    """
    sql = "UPDATE vds_static SET vds_spm_priority = '%s' WHERE vds_name = '%s'"
    try:
        engine.db.psql(sql, spm_priority, host_name)
    except ExecuteDBQueryError:
        return False
    return True


@ll_general.generate_logs()
def get_spm_host(hosts):
    """
    Get SPM host from the list of hosts

    Args:
        hosts (list): List of hosts to be searched through

    Returns:
        str: SPM host name

    Raises:
        EntityNotFound: If host not found
    """
    for host in hosts:
        if check_host_spm_status(True, host):
            return host
    else:
        raise EntityNotFound('SPM not found among these hosts: %s' % hosts)


def get_hsm_host(hosts):
    """
    Get HSM host from the list of hosts

    Args:
        hosts (list): List of hosts to be searched through

    Returns:
        str: HSM host name

    Raises:
        EntityNotFound: If host not found
    """
    for host in hosts:
        if not check_host_spm_status(True, host):
            return host
    else:
        raise EntityNotFound('HSM not found among these hosts: %s' % hosts)


@ll_general.generate_logs()
def get_host(positive, datacenter='Default', spm=True, host=None):
    """
    Locate and return SPM or HSM host from specific datacenter

    Args:
        positive (bool): Expeted results
        datacenter (str): The data center name
        spm (bool): When true return SPM host, false locate and return the
            HSM host
        host (str): Optionally, when the host name exist, the function
            locates the specific HSM host. When such host doesn't exist,
            the first HSM found will be returned.

    Returns:
        tuple: (bool, dict() with host name)
    """

    try:
        clusters = CL_API.get(abs_link=False)
        data_center_obj = DC_API.find(datacenter)
    except EntityNotFound:
        return False, {'host': None}

    clusters = (
        cl for cl in clusters if
        hasattr(cl, 'data_center') and
        cl.get_data_center() and
        cl.get_data_center().id == data_center_obj.id
    )
    for cluster in clusters:
        element_status, hosts = searchElement(
            positive, ELEMENT, COLLECTION, 'cluster', cluster.name
        )
        if not element_status:
            continue

        for host in hosts:
            spm_status = check_host_spm_status(positive, host.name)
            if spm and spm_status:
                return True, {'host': host.name}

            elif not spm and not spm_status and (
                (not host or host == host.name)
            ):
                return True, {'host': host.name}
    return False, {'host': None}


@ll_general.generate_logs()
def wait_for_spm(datacenter, timeout=SPM_TIMEOUT, sleep=10):
    """
    Waits until SPM gets elected in DataCenter

    Args:
        datacenter (str): The name of the datacenter
        timeout (int): How much seconds to wait until it fails
        sleep (int): How much to sleep between checks

    Returns:
        bool: True if an SPM gets elected before timeout.

    Raises:
        RESTTimeout: If no SPM in given time
    """
    sampler = TimeoutingSampler(
        timeout, sleep, get_host, True, datacenter, True
    )
    sampler.timeout_exc_args = (
        "Timeout when waiting for SPM to appear in DC %s." % datacenter,
    )
    for s in sampler:
        if s[0]:
            return True


@ll_general.generate_logs()
def is_host_exist(host):
    """
    Check if host exists under engine

    Args:
        host (str): Host name

    Returns:
        bool: True, if host exists under the engine, otherwise False
    """
    return host in get_host_names_list()


@ll_general.generate_logs()
def get_host_compatibility_version(host):
    """
    Get Host compatibility version

    Args:
        host(str): Host name

    Returns:
        str or None: Compatibility version if found else None
    """
    # check if given hostname exists in the setup
    try:
        host_obj = get_host_object(host_name=host)
    except EntityNotFound:
        return None

    # Since host returned from API supplies the cluster ID, cluster *must*
    # exist in rhevm - no need to check
    cl_id = host_obj.get_cluster().get_id()
    cl_obj = CL_API.find(cl_id, 'id')

    cluster = cl_obj.get_name()
    return get_cluster_compatibility_version(cluster)


@ll_general.generate_logs()
def get_cluster_compatibility_version(cluster):
    """
    Get Cluster compatibility version

    Args:
        cluster(str): Cluster name

    Returns:
        str: Compatibility version or None
    """
    try:
        cluster_obj = CL_API.find(cluster)
    except EntityNotFound as err:
        logger.error(err)
        return None

    cl_version = '{0}.{1}'.format(
        cluster_obj.get_version().get_major(),
        cluster_obj.get_version().get_minor()
    )
    return cl_version


def wait_for_host_pm_operation(host, engine):
    """
    Wait for next PM operation availability

    Args:
        host (str): vds host name
        engine (Engine): engine

    Returns:
        bool: True if success, False otherwise
    """
    time_to_wait = 0
    return_val = True
    db = engine.db
    try:
        sql = (
            "select option_value from vdc_options "
            "where option_name = 'FenceQuietTimeBetweenOperationsInSec';"
        )
        res = db.psql(sql)
        wait_sec = res[0][0]
        events = ['USER_VDS_STOP', 'USER_VDS_START', 'USER_VDS_RESTART']
        for event in events:
            sql = (
                "select get_seconds_to_wait_before_pm_operation("
                "'%s','%s', %s);"
            )
            res = db.psql(sql, host, event, wait_sec)
            time_sec = int(res[0][0])
            if time_sec > time_to_wait:
                time_to_wait = time_sec
    except Exception as ex:
        logger.error(
            'Failed to get wait time before host %s PM operation: %s',
            host, ex
        )
        return_val = False
    if time_to_wait > 0:
        logger.info(
            'Wait %d seconds until PM operation will be permitted.',
            time_to_wait
        )
        time.sleep(time_to_wait)
    return return_val


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


@ll_general.generate_logs()
def select_host_as_spm(
    positive, host, data_center, timeout=HOST_STATE_TIMEOUT, sleep=10,
    wait=True
):
    """
    Selects the host to be spm

    Args:
        positive (bool): Expected result
        host (str): Name of a host to be selected as spm
        data_center (str): Datacenter name
        timeout (int): Timeout to wait for the host to be SPM
        sleep (int): Time to sleep between iterations
        wait (bool): True to wait for spm election to be completed before
            returning (only waits if positive and wait are both true)

    Returns:
        bool: True if host was elected as spm properly, False otherwise
    """
    if not check_host_spm_status(True, host):
        host_obj = get_host_object(host_name=host)
        response = HOST_API.syncAction(host_obj, "forceselectspm", positive)
        if response:
            if positive and wait:
                wait_for_spm(data_center, timeout=timeout, sleep=sleep)
                return check_host_spm_status(True, host)
            else:
                return positive
        return response == positive
    else:
        logger.info("Host %s already SPM", host)
        return positive


def set_host_non_operational_nic_down(host_resource, nic):
    """
    Set host NIC with required network down and causes the Host
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

    return wait_for_hosts_states(
        True, names=host_name, states='non_operational', timeout=TIMEOUT * 2
    )


def start_vdsm(host, password, datacenter):
    """
    Start vdsm. Before that stop all vms and deactivate host.

    Args:
        host(str): Host name in RHEVM
        password (str): Password of host
        datacenter (str): Datacenter of host

    Returns:
        bool: True if VDSM started, otherwise False
    """
    ip = get_host_ip(host)
    if not startVdsmd(vds=ip, password=password):
        logger.error("Unable to start vdsm on host %s", host)
        return False

    if not activate_host(True, host):
        logger.error("Unable to activate host %s", host)
        return False

    return waitForDataCenterState(datacenter)


def stop_vdsm(host, password):
    """
    Stop vdsm. Before that stop all vms and deactivate host.

    Args:
        host (str): Host name in RHEVM
        password (str): Password of host

    Returns:
        bool: True if VDSM stopped, otherwise False
    """
    for vm in get_all_vms():
        if get_vm_state(vm.name) == ENUMS['vm_state_down']:
            continue

        vm_host = get_vm_host(vm_name=vm)
        if not vm_host:
            return False

        if vm_host == host:
            logger.error("Stopping vm %s", vm.name)
            if not stopVm(True, vm.name):
                return False

    if not deactivate_host(True, host):
        logger.error("Unable to deactivate host %s", host)
        return False

    ip = get_host_ip(host)
    return stopVdsmd(vds=ip, password=password)


def kill_vm_process(resource, vm_name):
    """
    Kill VM process of a given vm

    Args:
        resource (VDS): Host resource
        vm_name (str): Name of VM to kill

    Returns:
        bool: True, if function succeed to kill VM process, otherwise False
    """
    vm_pid = resource.get_vm_process_pid(vm_name=vm_name)
    if not vm_pid:
        logger.error("Failed to get VM pid from resource %s", resource)
        return False

    rc = resource.run_command(['kill', '-9', vm_pid])[0]
    return not bool(rc)


def kill_vdsmd(resource):
    """
    Kill VDSM process on a given host

    Args:
        resource (VDS): resource

    Returns:
        bool: True, if function succeed to kill VDSM process, otherwise False
    """
    rc, out, err = resource.run_command(shlex.split('pgrep vdsm'))
    if rc:
        logger.error(
            "Failed to get VDSM pid from resource %s out: %s error: %s",
            resource, out, err
        )
        return False

    vdsm_process = out.rstrip('\n').split('\n')
    rc, out, err = resource.run_command(shlex.split('pgrep super'))
    if rc:
        logger.error(
            "Failed to get super VDSM pid from resource %s out: %s error: %s",
            resource, out, err
        )
        return False

    super_vdsm_process = out.rstrip('\n').split('\n')
    vdsm_pid = set(vdsm_process).symmetric_difference(super_vdsm_process).pop()
    logger.info("kill VDSM pid: %s on host %s", vdsm_pid, resource.ip)
    rc, out, err = resource.run_command(['kill', '-9', vdsm_pid])
    return not bool(rc)


@ll_general.generate_logs()
def get_host_object(host_name, attribute="name"):
    """
    Get host object by host_name.

    Args:
        host_name (str): Name of host.
        attribute (str): The key for search - 'name' or 'id'

    Returns:
        host: Host object.
    """
    return HOST_API.find(host_name,  attribute=attribute)


def get_host_topology(host_name):
    """
    Get host topology object by host name.

    Args:
        host_name (str): Name of host.

    Returns:
        Topology: Host topology object.

    Raises:
        EntityNotFound: If host not found
    """
    host_obj = get_host_object(host_name)
    if not host_obj:
        raise EntityNotFound("No host with name %s" % host_name)
    return host_obj.cpu.topology


def run_command(host, user, password, cmd):
    """
    Ssh to user@hostname and run cmd on cli

    Args:
        host (str): The name of the host
        user (str): User name
        password (str): User password
        cmd (str): Command to run

    Returns:
        str: the command's output.
    """
    #  TODO: Remove usage of Machine
    connection = machine.Machine(
        host=get_host_ip(host), user=user, password=password
    ).util(machine.LINUX)
    rc, out = connection.runCmd(shlex.split(cmd))
    if not rc:
        raise RuntimeError("Output: %s" % out)

    return out


@ll_general.generate_logs()
def get_host_name_from_engine(vds_resource):
    """
    Get host name from engine by host IP (vds_resource)

    Args:
        vds_resource (VDS): resources.VDS object

    Returns:
        str or None: Host name or None
    """
    engine_hosts = get_host_list()
    for host in engine_hosts:
        if (
                host.get_address() == vds_resource.fqdn
                or host.get_address() == vds_resource.ip
                or host.name == vds_resource.fqdn
                or vds_resource.ip == socket.gethostbyname(host.address)
        ):
            return host.name
    return None


@ll_general.generate_logs()
def get_host_ip_from_engine(host):
    """
    Get host IP from engine by host name

    Args:
        host (Host): resources.VDS object

    Returns:
        str or None: Host.name or None
    """

    host_name = get_host_object(host_name=host)
    return host_name.get_address()


@ll_general.generate_logs(step=True)
def refresh_host_capabilities(host, start_event_id):
    """
    Refresh Host Capabilities

    Args:
        host (str): Host name
        start_event_id (str): Event id to search from

    Returns:
        bool: True/False
    """
    host_obj = get_host_object(host_name=host)
    code = [606, 607]
    query = "type={0} OR type={1}".format(code[0], code[1])
    HOST_API.syncAction(entity=host_obj, action="refresh", positive=True)
    for event in EVENT_API.query(query):
        if int(event.get_id()) < int(start_event_id):
            return False
        if event.get_code() in code:
            return True if event.get_code() == code[0] else False

    return False


def get_cluster_hosts(cluster_name, host_status=ENUMS['host_state_up']):
    """
    Get a list of host names for a given cluster.

    Args:
        cluster_name (str): Name of the cluster
        host_status (str): Status of the host

    Returns:
        list: List of host names in a cluster with host_status or empty list
    """
    elm_status, hosts = searchElement(
        True, ELEMENT, COLLECTION, 'cluster', cluster_name
    )
    if elm_status:
        return [
            host.get_name() for host in hosts if
            host.get_status() == host_status
        ]
    return list()


def get_host_max_scheduling_memory(host_name):
    """
    Get host max scheduling memory

    Args:
        host_name (str): Host name

    Returns:
        int: Host max scheduling memory
    """
    host_obj = get_host_object(host_name)
    return host_obj.get_max_scheduling_memory()


def get_host_free_memory(host_name):
    """
    Get host free memory

    Args:
        host_name (str): host name

    Returns:
        int: Total host free memory
    """
    stats = getStat(host_name, ELEMENT, COLLECTION, ["memory.free"])
    return stats["memory.free"]


@ll_general.generate_logs()
def get_host_nic_statistics(host, nic):
    """
    Get host NIC statistics collection

    Args:
        host (str): Host name
        nic (str): NIC name

    Returns:
        list: Host NIC statistics list
    """
    host_nic = get_host_nic(host, nic)
    return HOST_NICS_API.getElemFromLink(
        host_nic, link_name="statistics", attr="statistic"
    )


def get_numa_nodes_from_host(host_name):
    """
    Get list of host numa nodes objects

    Args:
        host_name (str): Name of host

    Returns:
        list: List of NumaNode objects
    """
    host_obj = get_host_object(host_name)
    return HOST_API.getElemFromLink(host_obj, "numanodes", "host_numa_node")


def get_numa_node_memory(numa_node_obj):
    """
    Get numa node memory

    Args:
        numa_node_obj (NumaNode): Object of NumaNode

    Returns:
        int: Total amount of memory of numa node
    """
    return numa_node_obj.get_memory()


def get_numa_node_cpus(numa_node_obj):
    """
    Get numa node cpu's

    Args:
        numa_node_obj (NumaNode): object of NumaNode

    Returns:
        list: List of cores indexes of numa node
    """
    cores = list()
    numa_node_cpus = numa_node_obj.get_cpu()
    if numa_node_cpus:
        numa_node_cores = numa_node_cpus.get_cores().get_core()
        cores = [numa_node_core.index for numa_node_core in numa_node_cores]
    return cores


def get_numa_node_index(numa_node_obj):
    """
    Get numa node index

    Args:
        numa_node_obj (NumaNode): Object of NumaNode

    Returns:
        int: Index of numa node
    """
    return numa_node_obj.get_index()


def get_numa_node_by_index(host_name, index):
    """
    Get numa node by index

    Args:
        host_name (str): Name of host
        index (int): Index of numa node

    Returns:
        NumaNode or None: NumaNode object or None
    """
    numa_nodes = get_numa_nodes_from_host(host_name)
    for numa_node in numa_nodes:
        if numa_node.index == index:
            return numa_node
    return None


def get_num_of_numa_nodes_on_host(host_name):
    """
    Get number of numa nodes that host has

    Args:
        host_name (str): Name of host

    Returns:
        int: Number of numa nodes
    """
    return len(get_numa_nodes_from_host(host_name))


def get_numa_nodes_indexes(host_name):
    """
    Get list of host numa indexes

    Args:
        host_name (str): Name of host

    Returns:
        list: List of host numa indexes
    """
    return [
        get_numa_node_index(
            node_obj
        ) for node_obj in get_numa_nodes_from_host(host_name)
    ]


def upgrade_host(host_name, image=None):
    """
    Upgrade host

    Ags:
        host_name (str): Name of the host to be upgraded
        image (str): Image to use in upgrading host (RHEV-H only)

    Returns:
        bool: True if host was upgraded, otherwise False
    """
    host = get_host_object(host_name=host_name)
    if bool(HOST_API.syncAction(host, 'upgrade', True, image=image)):
        return wait_for_hosts_states(True, [host_name], states='up')

    return False


def is_upgrade_available(host_name):
    """
    Check if upgrade is available for host

    Args:
        host_name (str): Name of the host to be upgraded

    Returns:
        bool: True if upgrade is available for host, otherwise False
    """
    return bool(get_host_object(host_name=host_name).get_update_available())


def get_host_vm_run_on(vm_name):
    """
    Return host address where vm run

    Args:
        vm_name (str): Name of vm

    Returns:
        str: Address of the host where vm run
    """
    vm_obj = VM_API.find(vm_name)
    return HOST_API.find(vm_obj.host.id, 'id').get_address()


def get_host_cpu_load(host_name):
    """
    Get host cpu load

    Args:
        host_name (str): Host name

    Returns:
        float: Host current cpu load
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
        log_action="Add", obj_type=FENCE_AGENT, obj_name=agent_address,
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
        log_action="Update", obj_type=FENCE_AGENT, obj_name=agent_address,
        extra_txt="on host %s" % host_name
    )
    old_agent_obj = get_fence_agent_by_address(
        host_name=host_name, agent_address=agent_address
    )
    kwargs['type_'] = kwargs.pop('agent_type', None)
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
        log_action="Remove", obj_type=FENCE_AGENT, obj_name=agent_address
    )
    logger.info(log_info)
    status = AGENT_API.delete(entity=fence_agent_obj, positive=True)
    if not status:
        logger.info(log_error)
    return status


def get_host_cores(host_name):
    """
    Get the host cores number

    Args:
        host_name (str): Host name

    Returns:
        int: Number of host cores
    """
    cores = get_host_topology(host_name).cores
    if cores:
        return cores
    logger.error("Failed to get cpu cores from %s", host_name)
    return 0


def get_host_sockets(host_name):
    """
    Get the host sockets number

    Args:
        host_name (str): Host name

    Returns:
        int: Number of host sockets
    """
    sockets = get_host_topology(host_name).sockets
    if sockets:
        return sockets
    logger.error("Failed to get cpu sockets from %s", host_name)
    return 0


def get_host_threads(host_name):
    """
    Get the host sockets number

    Args:
        host_name (str): Host name

    Returns:
        int: Number of host threads
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

    Args:
        host_name (str): host name

    Returns:
        int: Number of host processing units
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
    host_obj = get_host_object(host_name=host_name)
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


@ll_general.generate_logs()
def get_hosted_engine_obj(host_name):
    """
    Get host hosted-engine object

    Args:
        host_name (str): Host name

    Returns:
        HostedEngine: HostedEngine instance
    """
    name_query = "name=%s" % host_name
    hosts_obj = HOST_API.query(name_query, all_content=True)
    if hosts_obj:
        return hosts_obj[0].get_hosted_engine()
    return None


def is_hosted_engine_configured(host_name):
    """
    Check if host configure as HostedEngine host

    Args:
        host_name (str): Host name

    Returns:
        bool: True, if host configured as HostedEngine, otherwise False
    """
    hosted_engine_obj = get_hosted_engine_obj(host_name=host_name)
    if hosted_engine_obj:
        return hosted_engine_obj.get_configured()
    return False


def is_hosted_engine_active(host_name):
    """
    Check if host is active under the hosted engine environment via engine

    Args:
        host_name (str): Host name

    Returns:
        bool: True, if host is active under the hosted engine environment,
            otherwise False
    """
    if not is_hosted_engine_configured(host_name=host_name):
        return False
    return get_hosted_engine_obj(host_name=host_name).get_active()


def add_affinity_label(host_name, affinity_label_name):
    """
    Add affinity label to the host

    Args:
        host_name (str): Host name
        affinity_label_name (str): Affinity label name

    Returns:
        bool: True, if add action succeed, otherwise False
    """
    from art.rhevm_api.tests_lib.low_level.affinitylabels import (
        add_affinity_label_to_element
    )
    host_obj = get_host_object(host_name=host_name)
    return add_affinity_label_to_element(
        element_obj=host_obj,
        element_api=HOST_API,
        element_type="host",
        affinity_label_name=affinity_label_name
    )


def remove_affinity_label(host_name, affinity_label_name):
    """
    Remove affinity label from the host

    Args:
        host_name (str): Host name
        affinity_label_name (str): Affinity label name

    Returns:
        bool: True, if remove action succeed, otherwise False
    """
    from art.rhevm_api.tests_lib.low_level.affinitylabels import (
        remove_affinity_label_from_element
    )
    host_obj = get_host_object(host_name=host_name)
    return remove_affinity_label_from_element(
        element_obj=host_obj,
        element_api=HOST_API,
        element_type="host",
        affinity_label_name=affinity_label_name
    )


def check_host_upgrade(host_name):
    """
    Check for update of packages on host by engine
    Note: this is async task

    Args:
        host_name (str): Name of the host to be check upgrade for

    Returns:
        bool: True if action succeeds otherwise False
    """
    host = get_host_object(host_name=host_name)
    return bool(HOST_API.syncAction(host, 'upgradecheck', True))


def wait_for_hosted_engine_maintenance_state(
    host_resource, enabled=True, timeout=300, sleep=10
):
    """
    Wait until the hosted-engine host will have expected maintenance state

    Args:
        host_resource (VDS): Host resource
        enabled (bool): Wait for enabled or disable maintenance state
        timeout (int): Sampler timeout in seconds
        sleep (int): Sampler sleep time in seconds

    Returns:
        bool: True, if the hosted-engine has correct maintenance state,
            otherwise False
    """
    sampler = TimeoutingSampler(
        timeout=timeout, sleep=sleep, func=host_resource.get_he_stats
    )

    try:
        for sample in sampler:
            if sample and sample["maintenance"] == enabled:
                logger.info(
                    "%s: hosted-engine maintenance state equal to %s",
                    host_resource, enabled
                )
                return True
    except APITimeout:
        logger.error(
            "%s :Timeout waiting for hosted-engine maintenance state",
            host_resource
        )
        return False


@ll_general.generate_logs(step=True)
def get_lldp_nic_info(host, nic):
    """
    Get host NIC LLDP info

    Args:
        host (str): Host name
        nic (str): NIC name

    Returns:
        dict: LLDP content
    """
    host_nic = get_host_nic(host=host, nic=nic)
    data = HOST_NICS_API.getElemFromLink(
        elm=host_nic, link_name=LLDPS, attr=LLDP
    )
    return {elm.name: elm.properties.property[0].value for elm in data}
