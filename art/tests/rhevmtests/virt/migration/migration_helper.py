#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt migration helper
"""

import logging
import copy
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
import config


logger = logging.getLogger("Virt_Network_Migration_Init")


def remove_migration_job():
    """
    Remove migration job
    """

    remove_migration_job_query = (
        "UPDATE job SET status = 'FINISHED' WHERE status = 'STARTED' "
        "and action_type='MigrateVM'"
    )
    logger.info('Check for unfinished migration jobs in DB')
    active_jobs = ll_jobs.get_active_jobs()
    if active_jobs:
        for job in active_jobs:
            if 'Migrating VM' in job.description:
                logger.warning(
                    'There is unfinished migration job : %s', job.description
                )
                logger.info("Remove migration job")
                config.ENGINE.db.psql(remove_migration_job_query)


def activate_hosts():
    """
    Activating all hosts in setup
    """
    for host in config.HOSTS:
        hl_hosts.activate_host_if_not_up(host=host)


def init_network_dict(
    hosts_nets_nic_dict,
    networks,
    bond_name=None,
    hosts=1,
):
    """
    Update hosts and network dict with case network,
    Nic (bond or not) and return updated dict

    Args:
        hosts_nets_nic_dict(dict): Dict with network configuration
        networks (list): List with case network names
        bond_name (str): Bond name according to case
        hosts (int): Number of hosts

    Returns:
        dict: Return updated dict

    """
    # Go over hosts network dict and update network name and nic in case bond
    # is used.
    updated_dict = copy.deepcopy(hosts_nets_nic_dict)
    for host_index in xrange(hosts):
        net_info = updated_dict[host_index]
        for network_name, test_network in zip(config.NETWORK_NAMES, networks):
            for key, val in net_info[network_name].iteritems():
                if key == 'network':
                    # update network name
                    net_info[network_name][key] = test_network
                if (
                    key == 'nic' and bond_name and
                    network_name == config.NETWORK_NAMES[0]
                ):
                    # if bond and first network on host
                    net_info[network_name][key] = bond_name

    return updated_dict
