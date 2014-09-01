"""
High-level functions above data-center
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from art.core_api import is_action
import art.rhevm_api.tests_lib.low_level.hosts as hosts
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts

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
            results.append(executor.submit(hosts.addHost, True, name=host,
                                           root_password=password,
                                           cluster=cluster))

    for index, result in enumerate(results):
        if not result.result():
            raise errors.HostException("addHost of host %s failed." %
                                       hosts_list[index])
        LOGGER.debug("Host %s installed", hosts_list[index])

    if not hosts.waitForHostsStates(True, ",".join(hosts_list)):
        raise errors.HostException("Some of hosts didn't come to up status")


@is_action()
def switch_host_to_cluster(host, cluster):
    """
    Description: Puts host host into cluster cluster
    Parameters:
        * host - host that will be switched to different cluster
        * cluster - cluster to which host will be placed
    """
    assert hosts.deactivateHost(True, host)
    assert hosts.updateHost(True, host, cluster=cluster)
    assert hosts.activateHost(True, host)


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
    if not hosts.isHostInMaintenance(True, host):
        if not hosts.deactivateHost(True, host):
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
        hosts_list = hosts_list.split(',')
    spm = hosts.getSPMHost(hosts_list)
    logging.info("spm host - %s", spm)
    sorted_hosts = hosts._sort_hosts_by_priority(hosts_list, False)
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
    if not hosts.updateHost(True, host=host, pm='true', pm_type=pm_type,
                            pm_address=pm_address, pm_username=pm_user,
                            pm_password=pm_password, pm_secure=pm_secure,
                            **kwargs):
        raise errors.HostException("Cannot add power management to host: %s"
                                   % host)


def remove_power_management(host, pm_type):
    """
    Description: Add power management to host
    Author: slitmano
    Parameters:
    * host - Name of the host
    * pm_type - Name of power management type (ipmilan, apc_snmp and so on)
    """
    logging.info("disable power management for host: %s", host)
    if not hosts.updateHost(True, host=host, pm='false', pm_type=pm_type,
                            pm_password='', pm_address='', pm_username=''):
        raise errors.HostException("Cannot remove power management"
                                   " from host: %s" % host)


def activate_host_if_not_up(host):
    """
    Activate the host if the host is not up
    :param host: IP/FQDN of the host
    :return: True if host was activated properly False otherwise
    """
    if not hosts.getHostState(host) == ENUMS["host_state_up"]:
        return hosts.activateHost(True, host)
    return True
