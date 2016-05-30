"""
High-level functions above data-center
"""

import logging
from art.core_api import apis_exceptions
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
from concurrent.futures import ThreadPoolExecutor
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd

LOGGER = logging.getLogger("art.hl_lib.hosts")
ENUMS = opts['elements_conf']['RHEVM Enums']


def add_hosts(hosts_list, passwords, cluster):
    """
    Description: Adds all hosts from config
    Parameters:
        * hosts_list - list of hosts
        * passwords - list of hosts' passwords
        * cluster - name of the cluster hosts will be placed to
    """
    results = list()
    # Workers should be defined somewhere
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, host in enumerate(hosts_list):
            password = passwords[index]
            LOGGER.info("Adding host %s", host)
            results.append(executor.submit(ll_hosts.addHost, True, name=host,
                                           root_password=password,
                                           cluster=cluster))

    for index, result in enumerate(results):
        if not result.result():
            raise errors.HostException("addHost of host %s failed." %
                                       hosts_list[index])
        LOGGER.debug("Host %s installed", hosts_list[index])

    if not ll_hosts.waitForHostsStates(True, ",".join(hosts_list)):
        raise errors.HostException("Some of hosts didn't come to up status")


def move_host_to_another_cluster(host, cluster, activate=True):
    """
    Switch host to different cluster

    :param host: Host name that will be switched to different cluster
    :type host: str
    :param cluster:Cluster name where the host should be moved to
    :type cluster: str
    :param activate: Activate the host after move
    :type activate: bool
    :return: True if succeed to move it False otherwise
    :rtype: bool
    """
    LOGGER.info("Set %s to maintenance", host)
    if not ll_hosts.deactivateHost(True, host):
        LOGGER.error("Failed to set %s to maintenance", host)
        return False

    LOGGER.info("Moving %s to %s", host, cluster)
    if not ll_hosts.updateHost(positive=True, host=host, cluster=cluster):
        LOGGER.error("Failed to move %s to %s", host, cluster)
        return False

    if activate:
        LOGGER.info("Activate %s", host)
        if not ll_hosts.activateHost(positive=True, host=host):
            LOGGER.error("Failed to activate %s", host)
            return False
    return True


def deactivate_host_if_up(host):
    """
    Deactivate host if it's not in maintenance

    __author__: 'ratamir'

    Args:
        host (str): Name of the host to deactivate.

    Returns:
        bool: True if host was deactivated properly and positive,
            False otherwise.
    """
    LOGGER.info("Deactivate Host %s", host)
    if not ll_hosts.isHostInMaintenance(True, host):
        if not ll_hosts.deactivateHost(True, host):
            LOGGER.error("Failed to deactivate Host %s")
            return False
    return True


def deactivate_hosts_if_up(hosts_list):
    """
    Deactivate hosts that are in status up

    __author__ = "ratamir"
    :param hosts_list: List or string of hosts to be deactivated
    :type hosts_list: list
    :returns: True if operation succeded, False otherwise
    :rtype: bool
    """
    if isinstance(hosts_list, str):
        _hosts_list = hosts_list.split(',')
    else:
        _hosts_list = hosts_list[:]

    spm = None
    try:
        spm = ll_hosts.getSPMHost(_hosts_list)
        LOGGER.info("spm host - %s", spm)
    except apis_exceptions.EntityNotFound:
        LOGGER.warning("No SPM host was found from the input hosts_list")

    sorted_hosts = ll_hosts._sort_hosts_by_priority(_hosts_list, False)
    if spm:
        sorted_hosts.remove(spm)
        sorted_hosts.append(spm)

    for host in sorted_hosts:
        if not deactivate_host_if_up(host):
            return False
    return True


def add_power_management(host_name, pm_agents, **kwargs):
    """
    Add fence agents and enable host power management

    Args:
        host_name (str): Host name
        pm_agents (list): Power management agents

    Keyword Args:
        pm_automatic(bool): Enable automatic shutdown of host
            under power saving policy
        pm_proxies (list): Power management proxies

    Returns:
        bool: True, if add succeed, otherwise False

    Examples:
        agent_d = {
            "agent_type": "test_type",
            "agent_address": "test_address",
            "agent_username": "test_username",
            "agent_password": "test_password",
            "concurrent": False,
            "order": 1,
            "options": {"slot": 1}
        }
        add_power_management("test_host", [agent_d])
    """

    for agent in pm_agents:
        if not ll_hosts.add_fence_agent(host_name, **agent):
            return False
    LOGGER.info("Enable power management under host %s", host_name)

    if not ll_hosts.updateHost(
        positive=True,
        host=host_name,
        pm=True,
        **kwargs
    ):
        LOGGER.error(
            "Failed to enable power management under host %s", host_name
        )
        return False
    return True


def remove_power_management(host_name):
    """
    Remove all fence agents from host and disable power management

    Args:
        host_name (str): Host name

    Returns:
        bool: True, if remove succeed, otherwise False
    """

    agents = ll_hosts.get_fence_agents_list(host_name)
    for agent in agents:
        if not ll_hosts.remove_fence_agent(agent):
            return False
    LOGGER.info("Disable power management on host %s", host_name)

    if not ll_hosts.updateHost(
        positive=True, host=host_name, pm=False
    ):
        LOGGER.error(
            "Cannot disable power management on host: %s" % host_name
        )
        return False
    return True


def activate_host_if_not_up(host):
    """
    Activate the host if the host is not up

    Args:
        host (str): IP/FQDN of the host

    Returns:
        bool: True if host was activated properly False otherwise
    """
    if not ll_hosts.getHostState(host) == ENUMS["host_state_up"]:
        LOGGER.info(
            "Host %s status is %s. activating", host, ENUMS["host_state_up"]
        )
        if not ll_hosts.activateHost(True, host):
            LOGGER.error("Failed to activate host %s", host)
            return False
    return True


def restart_services_under_maintenance_state(
    services, host_resource, timeout=None
):
    """
    Put host to maintenance, restart given services then activate host.
    The services will be restarted by the list order.

    :param services: List of services to restart
    :type services: list
    :param host_resource: host resource
    :type host_resource: instance of VDS
    :param timeout: Timeout for restart service operation
    :type timeout: int
    :raises: HostException
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    if not ll_hosts.deactivateHost(True, host_name):
        raise errors.HostException(
            "Failed to put host %s to maintenance" % host_name
        )
    LOGGER.info("Restart services %s on %s ", services, host_name)
    for srv in services:
        if not host_resource.service(srv, timeout).restart():
            LOGGER.error(
                "Failed to restart %s, activating host %s", srv, host_name
            )
            ll_hosts.activateHost(True, host_name)
            raise errors.HostException(
                "Failed to restart %s services on host %s" % (host_name, srv)
            )
    if not ll_hosts.activateHost(True, host_name):
        raise errors.HostException()


def restart_vdsm_and_wait_for_activation(
        hosts_resource, dc_name, storage_domain_name
):
    """
    Restart vdsmd service and wait until storage will be active,

    :param hosts_resource: list of host resource
    :type hosts_resource: list of host resource
    :param dc_name: dc name
    :type dc_name: str
    :param storage_domain_name: storage domain name
    :type storage_domain_name: str
    :raises: HostException or StorageDomainException
    """

    for host in hosts_resource:
        host_name = ll_hosts.get_host_name_from_engine(host.ip)
        restart_services_under_maintenance_state(['vdsmd'], host)
        ll_hosts.waitForHostsStates(True, host_name)
    ll_hosts.waitForSPM(dc_name, 200, 5)

    for host in hosts_resource:
        host_name = ll_hosts.get_host_name_from_engine(host.ip)
        if ll_hosts.checkHostSpmStatus(True, host_name):
            if not ll_sd.waitForStorageDomainStatus(
                True, dc_name, storage_domain_name,
                ENUMS["storage_domain_state_active"]
            ):
                raise errors.StorageDomainException(
                    "Failed to activate storage domain"
                    " %s after restart of VDSM" % storage_domain_name
                )
