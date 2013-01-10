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


