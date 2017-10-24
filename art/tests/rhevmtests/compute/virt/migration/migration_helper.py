#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt migration helper
"""

import copy
import logging
import shlex
import time

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.compute.virt.helper as helper
import rhevmtests.helpers as helpers
from art.unittest_lib.common import testflow
from utilities import jobs

logger = logging.getLogger("Virt_Network_Migration_Init")

VIRSH_VM_LIST_CMD = ["virsh", "-r", "list", "|grep"]
VIRSH_DOM_JOB_INFO_CMD = "virsh -r domjobinfo %s | grep bandwidth:"
SAMPLER_TIMEOUT = 3


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


def migrate_vm_with_policy(
    migration_policy,
    vm_name=config.MIGRATION_VM,
    cluster_name=None,
    bandwidth_method=None,
    custom_bandwidth=None,
    expected_bandwidth=None,
    auto_converge="inherit",
    compressed="inherit",
    migration_timeout=config.MIGRATION_TIMEOUT
):
    """
    Handles 2 case: update policy in cluster or VM level
    Actions:
    1. Update policy
    2. Migrate vm
    3. Checks migration BW
    (with virsh domjobinfo, if expected_bandwidth != None)

    Args:
        migration_policy (str): Migration policy name
        vm_name (str): vm_name default config.MIGRATION_VM
        cluster_name (str): Cluster name
        bandwidth_method (str): Bandwidth assignment method
        custom_bandwidth (int): Custom bandwidth (method must be custom)
        expected_bandwidth (int): Expected bandwidth while migrate
        auto_converge (bool): auto converge (3.6 optimize features)
        compressed (bool): compressed (3.6 optimize_features)
        migration_timeout (int): migration time out, default is: 300 sec

    Returns:
        bool: True if migrate with policy pass, otherwise False
    """
    if cluster_name:
        logger.info(
            "Update to migration policy %s on cluster", migration_policy
        )
        update_migration_policy_on_cluster(
            migration_policy=migration_policy,
            cluster_name=cluster_name,
            bandwidth=bandwidth_method,
            custom_bandwidth=custom_bandwidth
        )
    else:
        logger.info(
            "Update to migration policy %s on vm", migration_policy
        )
        update_migration_policy_on_vm(
            migration_policy=migration_policy,
            vm_name=vm_name,
            auto_converge=auto_converge,
            compressed=compressed
        )
    testflow.step("Migrate VM and check bandwidth")
    if expected_bandwidth:
        if (
            bandwidth_method == config.BW_CUSTOM and
            migration_policy == config.MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED
        ):
            expected_bandwidth = custom_bandwidth
        logger.info(
            "Policy: %s, Bandwidth: %s ,Expected bandwidth: %s",
            migration_policy, bandwidth_method, expected_bandwidth
        )
        check_bandwidth_kwargs = {
            'vm_name': vm_name,
            'expected_bandwidth': expected_bandwidth
        }
        vm_migration_kwargs = {
            'positive': True,
            'vm': vm_name,
            'timeout': migration_timeout
        }
        check_bandwidth_job = jobs.Job(
            check_migration_bandwidth, (), check_bandwidth_kwargs
        )
        migration_job = jobs.Job(
            ll_vms.migrateVm, (), vm_migration_kwargs
        )
        job_set = jobs.JobsSet()
        job_set.addJobs([check_bandwidth_job, migration_job])
        job_set.start()
        job_set.join()
        return check_bandwidth_job.result and migration_job.result
    else:
        return ll_vms.migrateVm(
            positive=True,
            vm=vm_name
        )


def update_migration_policy_on_cluster(
    migration_policy,
    cluster_name,
    bandwidth=None,
    custom_bandwidth=None,

):
    """
    Update cluster with migration policy and bandwidth.
    In order to update policy use id from config.MIGRATION_POLICY
    For bandwidth use config.MIGRATION_BANDWIDTH, in case of custom bandwidth
    NOTE:
    bandwidth=config.MIGRATION_BANDWIDTH_CUSTOM, custom_bandwidth=<new BW>

    Args:
        migration_policy (str): Migration policy name
        cluster_name (str): cluster name
        bandwidth (str): Bandwidth method ('auto', 'hypervisor_default',
        'custom')
        custom_bandwidth (int): Custom bandwidth value

    Returns:
        bool: True is cluster updated successfully, otherwise False
    """
    return ll_clusters.updateCluster(
        positive=True,
        cluster=cluster_name,
        migration_policy_id=config.MIGRATION_POLICIES[migration_policy],
        migration_bandwidth=bandwidth,
        migration_custom_bandwidth=custom_bandwidth
    )


def update_migration_policy_on_vm(
    migration_policy,
    vm_name,
    auto_converge="inherit",
    compressed="inherit"

):
    """
    Update VM with migration policy.
    In order to update policy use id from config.MIGRATION_POLICY

    Args:
        migration_policy (str): Migration policy name
        vm_name (str): vm name
        auto_converge (bool): Enable auto converge (only with Legacy policy)
        compressed (bool): Enable compressed (only with Legacy policy)

    Returns:
        bool: True is VM updated successfully, otherwise False
    """
    return ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        migration_policy_id=config.MIGRATION_POLICIES[migration_policy],
        auto_converge=auto_converge,
        compressed=compressed
    )


def check_migration_bandwidth(
    vm_name,
    expected_bandwidth
):
    """
    Check migration bandwidth on source host
    Args:
        vm_name (str): VM name
        expected_bandwidth (int): expected bandwidth according to policy

    Returns:
        bool: True if bandwidth as expected
    """
    host_resource = helpers.get_host_resource_of_running_vm(vm_name)
    vm_id = helper.get_vm_id(vm_name)
    bw_results = []
    ll_vms.wait_for_vm_states(
        vm_name=vm_name,
        states=[
            config.ENUMS['vm_state_migrating'],
            config.ENUMS['vm_state_migrating_from']
        ]
    )

    logger.info("check bandwidth on vm %s for ~60 sec", vm_name)
    for i in range(1, 20):
        bw_results.append(
            monitor_bandwidth(
                iteration_number=i,
                host_resource=host_resource,
                vm_id=vm_id
            )
        )
        i += 1
        time.sleep(1)
    return check_bandwidth_results(bw_results, expected_bandwidth)


def monitor_bandwidth(vm_id, host_resource, iteration_number=0):
    """
    Get migration bandwidth from virsh

    Args:
        iteration_number (int): index for logger output
        vm_id (str): VM id
        host_resource (Host): host resource

    Returns:
        int: bandwidth value
    """
    cmd = shlex.split(VIRSH_DOM_JOB_INFO_CMD % vm_id)
    rc, out, err = host_resource.executor().run_cmd(cmd)
    if iteration_number % 5 == 0:
        logger.info("#%d: bandwidth output: %s", iteration_number, out)
    if rc or err:
        logger.warn(
            "Did not get bandwidth value with virsh cmd: %s on: %s, err: %s"
            % (cmd, host_resource, err)
        )
        return -1
    return int(float(out.split(" ")[2]))


def check_bandwidth_results(
    bandwidth_results,
    expected_bandwidth
):
    """
    Check if bandwidth as expected (not over the expected bandwidth)

    Args:
        bandwidth_results (list): list of bandwidth samples
        expected_bandwidth (int): expected bandwidth according to policy

    Returns:
        bool: True if bandwidth is as expected
    """
    logger.info("bandwidth results list: %s", bandwidth_results)
    for val in bandwidth_results:
        if val > expected_bandwidth:
            logger.error(
                "Bandwidth pass limitation. Found: %s Expected: %s",
                val, expected_bandwidth
            )
            return False
    return True
