"""
High-level functions above data-center
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from art.core_api import is_action
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd

LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']


@is_action()
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


@is_action()
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
    logging.info("Set %s to maintenance", host)
    if not ll_hosts.deactivateHost(True, host):
        logging.error("Failed to set %s to maintenance", host)
        return False

    logging.info("Moving %s to %s", host, cluster)
    if not ll_hosts.updateHost(positive=True, host=host, cluster=cluster):
        logging.error("Failed to move %s to %s", host, cluster)
        return False

    if activate:
        logging.info("Activate %s", host)
        if not ll_hosts.activateHost(positive=True, host=host):
            logging.error("Failed to activate %s", host)
            return False
    return True


@is_action()
def deactivate_host_if_up(host):
    """
    Description: Deactivate host if it's not in maintenance
    Author: ratamir
    Parameters:
        * host - name of the host to deactivate
    Return: status (True if host was deactivated properly and positive,
                    False otherwise)
    """
    if not ll_hosts.isHostInMaintenance(True, host):
        if not ll_hosts.deactivateHost(True, host):
            return False
    return True


@is_action()
def deactivate_hosts_if_up(hosts_list):
    """
    Description: Deactivate hosts that are in status up
    Author: ratamir
    Parameters:
    * hosts_list - List or string of hosts to be deactivated
    Returns: True (success) / False (failure)
    """
    if isinstance(hosts_list, str):
        _hosts_list = hosts_list.split(',')
    else:
        _hosts_list = hosts_list[:]
    spm = ll_hosts.getSPMHost(_hosts_list)
    logging.info("spm host - %s", spm)
    sorted_hosts = ll_hosts._sort_hosts_by_priority(_hosts_list, False)
    sorted_hosts.remove(spm)
    sorted_hosts.append(spm)

    for host in sorted_hosts:
        status = deactivate_host_if_up(host)
        if not status:
            return status
    return True


def add_power_management(host, pm_type, pm_address, pm_user, pm_password,
                         pm_secure='false', **kwargs):
    """
    Description: Add power management to host
    Author: slitmano
    Parameters:
    * host - Name of the host
    * pm_type - Name of power management type (ipmilan, apc_snmp and so on)
    * pm_address - Address of the power management agent
    * pm_user - Username for the power management agent
    * pm_password = Password for the power management agent
    """
    logging.info("Add power management type %s for host: %s", pm_type, host)
    if not ll_hosts.updateHost(
            True, host=host, pm='true', pm_type=pm_type,
            pm_address=pm_address, pm_username=pm_user,
            pm_password=pm_password, pm_secure=pm_secure, **kwargs
    ):
        raise errors.HostException(
            "Cannot add power management to host: %s" % host)


def remove_power_management(host, pm_type):
    """
    Description: Add power management to host
    Author: slitmano
    Parameters:
    * host - Name of the host
    * pm_type - Name of power management type (ipmilan, apc_snmp and so on)
    """
    logging.info("disable power management for host: %s", host)
    if not ll_hosts.updateHost(
            True, host=host, pm='false', pm_type=pm_type,
            pm_password='', pm_address='', pm_username=''
    ):
        raise errors.HostException(
            "Cannot remove power management from host: %s" % host
        )


def activate_host_if_not_up(host):
    """
    Activate the host if the host is not up

    :param host: IP/FQDN of the host
    :return: True if host was activated properly False otherwise
    """
    if not ll_hosts.getHostState(host) == ENUMS["host_state_up"]:
        return ll_hosts.activateHost(True, host)
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
    logging.info("Put host %s to maintenance", host_name)
    if not ll_hosts.deactivateHost(True, host_name):
        raise errors.HostException(
            "Failed to put host %s to maintenance" % host_name
        )
    logging.info("Restart services %s on %s ", services, host_name)
    for srv in services:
        if not host_resource.service(srv, timeout).restart():
            logging.error(
                "Failed to restart %s, activating host %s", srv, host_name
            )
            ll_hosts.activateHost(True, host_name)
            raise errors.HostException(
                "Failed to restart %s services on host %s" % (host_name, srv)
            )
    logging.info("Activate host %s", host_name)
    if not ll_hosts.activateHost(True, host_name):
        raise errors.HostException(
            "Failed to activate host %s" % host_name
        )


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
