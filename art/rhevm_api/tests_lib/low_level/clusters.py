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
from art.rhevm_api.tests_lib.low_level import (
    general as ll_general,
    networks as ll_networks,
    vmpools as ll_vmpools,
    datacenters as ll_dc,
)
import art.test_handler.exceptions as exceptions
from art.core_api.apis_utils import getDS, data_st
from art.rhevm_api.tests_lib.low_level.scheduling_policies import (
    get_scheduling_policy_id
)
from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.utils.test_utils import searchForObj

ELEMENT = 'cluster'
COLLECTION = 'clusters'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
hostUtil = get_api('host', 'hosts')

Cluster = getDS('Cluster')
Version = getDS('Version')
MemoryOverCommit = getDS('MemoryOverCommit')
TransparentHugePages = getDS('TransparentHugePages')
MemoryPolicy = getDS('MemoryPolicy')
SchedulingPolicyThresholds = getDS('SchedulingPolicyThresholds')
SchedulingPolicy = getDS('SchedulingPolicy')
ErrorHandling = getDS('ErrorHandling')
CPU = getDS('Cpu')
KSM = getDS('Ksm')
CLUSTER_API = get_api('cluster', 'clusters')
AFFINITY_API = get_api('affinity_group', 'affinity_groups')
CPU_PROFILE_API = get_api('cpu_profile', 'cpu_profiles')
VM_API = get_api('vm', 'vms')
Migration_Options = getDS('MigrationOptions')
Migration_Policy = getDS('MigrationPolicy')
MigrationBandwidth = getDS('MigrationBandwidth')

CLUSTER_NAME = "cluster"
AFFINITY_GROUP_NAME = "affinity group"
CPU_PROFILE_NAME = "cpu profile"

# Scheduler policy properties
OVER_COMMITMENT_DURATION = "CpuOverCommitDurationMinutes"
HIGH_UTILIZATION = "HighUtilization"
LOW_UTILIZATION = "LowUtilization"

# Affinity group constants
VMS_NAME = "vms"
HOSTS_NAME = "hosts"
API_NAME = "api"
ENTITY_NAME = "entity_name"

AFFINITY_GROUP_PARAMS = {
    VMS_NAME: {
        API_NAME: VM_API,
        ENTITY_NAME: "Vm"
    },
    HOSTS_NAME: {
        API_NAME: hostUtil,
        ENTITY_NAME: "Host"
    }
}

logger = logging.getLogger(__name__)


def _prepareClusterObject(**kwargs):

    cl = Cluster()
    if kwargs.get("management_network"):
        net_obj = ll_networks.find_network(
            kwargs.get("management_network"),
            data_center=kwargs.get("data_center")
        )
        cl.set_management_network(net_obj)

    if 'name' in kwargs:
        cl.set_name(kwargs.pop('name'))

    if 'description' in kwargs:
        cl.set_description(kwargs.pop('description'))

    if 'version' in kwargs:
        majorV, minorV = kwargs.pop('version').split(".")
        clVersion = Version(major=int(majorV), minor=int(minorV))
        cl.set_version(clVersion)

    if 'cpu' in kwargs:
        cpu = data_st.Cpu()
        cpu.set_type(kwargs.pop('cpu'))
        cl.set_cpu(cpu)

    if 'data_center' in kwargs:
        clDC = dcUtil.find(kwargs.pop('data_center'))
        cl.set_data_center(clDC)

    if 'gluster_support' in kwargs:
        cl.set_gluster_service(kwargs.pop('gluster_support'))

    if 'virt_support' in kwargs:
        cl.set_virt_service(kwargs.pop('virt_support'))

    if 'mem_ovrcmt_prc' in kwargs or 'transparent_hugepages' in kwargs:

        transparentHugepages = None
        overcommit = None

        if kwargs.get('mem_ovrcmt_prc'):
            overcommit = MemoryOverCommit(percent=kwargs.pop('mem_ovrcmt_prc'))

        if kwargs.get('transparent_hugepages'):
            transparentHugepages = TransparentHugePages(
                enabled=kwargs.pop('transparent_hugepages')
            )

        memoryPolicy = MemoryPolicy(
            over_commit=overcommit,
            transparent_hugepages=transparentHugepages
        )

        cl.set_memory_policy(memoryPolicy)

    scheduling_policy = kwargs.pop('scheduling_policy', None)
    if scheduling_policy:
        scheduling_policy_id = get_scheduling_policy_id(
            scheduling_policy_name=scheduling_policy
        )
        scheduling_policy = SchedulingPolicy(id=scheduling_policy_id)

        cl.set_scheduling_policy(scheduling_policy)

    custom_sch_policy_properties = kwargs.pop('properties', None)
    if custom_sch_policy_properties:
        properties = getDS('Properties')()
        for name, value in custom_sch_policy_properties.iteritems():
            properties.add_property(
                getDS('Property')(name=name, value=value)
            )
        cl.set_custom_scheduling_policy_properties(properties)

    ballooning_enabled = kwargs.pop('ballooning_enabled', None)
    if ballooning_enabled is not None:
        cl.set_ballooning_enabled(ballooning_enabled)

    errorHandling = None
    if 'on_error' in kwargs:
        errorHandling = ErrorHandling(on_error=kwargs.pop('on_error'))
        cl.set_error_handling(errorHandling)

    threads = kwargs.pop('threads_as_cores', None)
    if threads is not None:
        cl.set_threads_as_cores(threads)

    if 'ksm_enabled' in kwargs:
        ksm_merge_across_nodes = kwargs.pop(
            'ksm_merge_across_nodes', None
        )
        cl.set_ksm(
            KSM(
                enabled=kwargs.pop('ksm_enabled'),
                merge_across_nodes=ksm_merge_across_nodes
            )
        )

    if 'rng_sources' in kwargs:
        cl.set_required_rng_sources(
            data_st.required_rng_sourcesType(
                kwargs.pop('rng_sources')
            )
        )

    if 'ha_reservation' in kwargs:
        cl.set_ha_reservation(kwargs.pop('ha_reservation'))
    # migration policy and bandwidth
    migration_policy_id = kwargs.pop('migration_policy_id', None)
    migration_bandwidth = kwargs.pop('migration_bandwidth', None)
    custom_bw = kwargs.pop('migration_custom_bandwidth', None)
    if migration_policy_id:
        migration_policy = Migration_Policy(id=migration_policy_id)
    else:
        migration_policy = Migration_Policy()
    if migration_bandwidth:
        if custom_bw:  # with custom bandwidth
            bandwidth = MigrationBandwidth(
                assignment_method=migration_bandwidth,
                custom_value=custom_bw
            )
        else:  # without custom bandwidth, method only
            bandwidth = MigrationBandwidth(
                assignment_method=migration_bandwidth
            )
        migration_options = Migration_Options(
            policy=migration_policy,
            bandwidth=bandwidth
        )
    else:  # without bandwidth
        migration_options = Migration_Options(policy=migration_policy)
    cl.set_migration(migration_options)

    mac_pool = kwargs.get('mac_pool')
    if mac_pool:
        cl.set_mac_pool(mac_pool)

    return cl


def addCluster(positive, **kwargs):
    """
    Add cluster

    __Author__: edolinin

    Args:
        positive (bool): Expected status

    Keyword arguments:
        name (str): Name of a cluster
        cpu (str): CPU name
        data_center (str): Name of data-center that cluster will be attached to
        description (str): Description of cluster
        version (str): Supported version
        gluster_support (bool): Gluster support
        virt_support (bool): virt support
        mem_ovrcmt_prc (str): The percentage of host memory allowed
            Recommended values include 100 (None), 150 (Server Load) and 200
            (Desktop Load)
        scheduling_policy (str): VM scheduling mode for hosts in the cluster
            (evenly_distributed, power_saving)
        properties (str): Properties of scheduling policy
        transparent_hugepages (bool): Defines the availability of Transparent
            Hugepages
        on_error (str): In case of non-operational (migrate, do_not_migrate,
            migrate_highly_available)
        threads (bool): If True, will count threads as cores, otherwise counts
            only cores
        ballooning_enabled (bool): If True, enables ballooning on cluster
        ksm_enabled (bool): If True, enables KSM on cluster
        ksm_merge_across_nodes (bool): Merge KSM pages across NUMA nodes
        rng_sources (list of str): Random number generator sources
        migration_policy_id (str): Migration policy name
        migration_bandwidth (str): Bandwidth assignment method
        migration_custom_bandwidth (int): Custom bandwidth
        mac_pool (str): New MAC pool for the cluster

    Returns:
        bool: True if cluster was created properly, False otherwise
    """
    name = kwargs.get("name")
    logger.info("Create cluster %s with %s", name, kwargs)
    cl = _prepareClusterObject(**kwargs)
    status = util.create(cl, positive)[1]
    if not status:
        logger.error("Failed to create cluster %s", name)
    return status


@ll_general.generate_logs(step=True)
def updateCluster(positive, cluster, **kwargs):
    """
    Update cluster

    Args:
        positive (bool): Positive or negative condition
        cluster (str): Cluster name

    Keyword Args:
        name (str): New cluster name
        cpu (str): CPU name
        data_center (str): Name of data center attached to cluster
        description (str): Description of cluster
        version (str): Supported version (2.2, 3)
        gluster_support (bool): Gluster support
        virt_support (bool): Virt support
        mem_ovrcmt_prc (int): Cluster memory overcommitment
        scheduling_policy (str): Cluster scheduling policy
        properties (dict): Scheduling policy properties
        transparent_hugepages (booL): Defines the availability of
            Transparent Hugepages
        on_error (str): Migration behaviour for VM's on non-operational host
        threads_as_cores (bool): Count threads as cores
        ballooning_enabled (bool): Enables ballooning on cluster
        ksm_enabled (bool): Enables KSM on cluster
        ha_reservation (bool): Enables HA Reservation on cluster
        ksm_merge_across_nodes (bool): Merge KSM pages across NUMA nodes
        rng_sources (list of str): Random number generator sources
        migration_policy_id (str): Migration policy name
        migration_bandwidth (str): Bandwidth assignment method
        migration_custom_bandwidth (int): Custom bandwidth
        mac_pool (str): New MAC pool for the DC
        compare (bool): True by default and run compareElements,
            otherwise compareElements doesn't run

    Returns:
        bool: True, if update succeed, otherwise False
    """
    compare = kwargs.get('compare', True)
    old_cluster_obj = util.find(cluster)
    new_cluster_obj = _prepareClusterObject(**kwargs)
    return util.update(
        old_cluster_obj, new_cluster_obj, positive, compare=compare
    )[1]


def removeCluster(positive, cluster):
    """
    Remove cluster

    Args:
        positive (bool): Expected result
        cluster (str): Name of a cluster that should be removed

    Returns:
        bool: True if cluster was removed properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="Remove", obj_type="cluster", obj_name=cluster,
        positive=positive
    )
    logger.info(log_info)
    cluster_obj = util.find(cluster)
    res = util.delete(cluster_obj, positive)
    if not res:
        logger.error(log_error)
    return res


def searchForCluster(positive, query_key, query_val, key_name, **kwargs):
    '''
    Description: search for clusters by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in object equivalent to query_key
    Return: status:
       True if expected number is equal to found by search.
       False otherwise
    '''

    return searchForObj(util, query_key, query_val, key_name, **kwargs)


def check_cluster_params(positive, cluster, **kwargs):
    """

    Args:
        positive (bool): Wait for positive or negative behaviour
        cluster (str): Cluster name

    Keyword Args:
        scheduling_policy (str): Scheduling policy name
        properties (dict): Scheduling policy properties
        over_commit (int): Memory over commitment
    Returns:

    """
    cluster_obj = util.find(cluster)

    error_msg = "%s of %s has wrong value, expected: %s, actual: %s."
    status = True

    # Check the scheduling policy properties
    scheduling_policy_obj = cluster_obj.get_scheduling_policy()
    scheduling_policy = kwargs.get("scheduling_policy")
    if scheduling_policy:
        if scheduling_policy_obj.get_name() != scheduling_policy:
            status = False
            util.logger.error(
                error_msg % (
                    "Scheduling policy",
                    cluster_obj.get_name(),
                    scheduling_policy,
                    scheduling_policy_obj.get_name()
                )
            )
    properties = kwargs.get("properties")
    if properties:
        properties_obj = scheduling_policy_obj.get_properties()
        for property_name in (
            LOW_UTILIZATION, HIGH_UTILIZATION, OVER_COMMITMENT_DURATION
        ):
            if property_name in properties:
                for property_obj in properties_obj:
                    if property_obj.get_name() == property_name:
                        property_val = property_obj.get_value().get_datum()
                        if property_val != properties[property_name]:
                            status = False
                            util.logger.error(
                                error_msg % (
                                    property_name,
                                    cluster_obj.get_name(),
                                    properties[property_name],
                                    property_val
                                )
                            )

    # Check the cluster memory over commitment
    over_commit = kwargs.get("over_commit")
    if over_commit:
        over_commit_obj = cluster_obj.get_memory_policy().get_over_commit()
        if over_commit_obj.get_percent() != over_commit:
            status = False
            util.logger.error(
                error_msg % (
                    "Memory overcommit percent",
                    cluster_obj.get_name(), over_commit,
                    over_commit_obj.get_percent()
                )
            )

    return status == positive


def get_cluster_object(cluster_name, all_content=False):
    """
    Get cluster object by name

    Args:
        cluster_name (str): cluster name
        all_content (bool): Get all content with object

    Returns:
        Cluster: Cluster object
    """
    return CLUSTER_API.find(cluster_name, all_content=all_content)


def _prepare_affinity_group_object(**kwargs):
    """
    Prepare affinity group data structure object

    Keyword Args:
        name (str): Affinity group name
        description (str): Affinity group description
        positive (bool): Affinity group positive behaviour
            (deprecated, use hosts_rule and vms_rule instead of)
        enforcing (bool): Affinity group enforcing behaviour
            (deprecated, use hosts_rule and vms_rule instead of)
        hosts_rule (dict): Host to VM affinity group rules
            (positive, enforcing, enabled)
        vms_rule (dict): VM to VM affinity group rules
            (positive, enforcing, enabled)
        hosts (list): Hosts names to add to the affinity group
        vms (list): VM's names to add to the affinity group

    Returns:
        AffinityGroup: AffinityGroup instance
    """
    rules = {}
    for rule in ("hosts_rule", "vms_rule"):
        rule_params = kwargs.pop(rule, {})
        if rule_params:
            rules[rule] = getDS("AffinityRule")(**rule_params)
    kwargs.update(rules)

    affinity_group_elements = {}
    for collection_name, params in AFFINITY_GROUP_PARAMS.iteritems():
        if collection_name in kwargs:
            collection = kwargs.pop(collection_name)
            collection_obj = getDS(collection_name.capitalize())()
            add_method_name = "add_{0}".format(params[ENTITY_NAME].lower())
            for element_name in collection:
                element_id = params[API_NAME].find(element_name).get_id()
                element_obj = getDS(params[ENTITY_NAME])(id=element_id)
                getattr(collection_obj, add_method_name)(element_obj)
            affinity_group_elements[collection_name] = collection_obj
    kwargs.update(affinity_group_elements)

    return ll_general.prepare_ds_object("AffinityGroup", **kwargs)


@ll_general.generate_logs()
def get_affinity_group_obj(affinity_name, cluster_name):
    """
    Get affinity group object by name.

    Args:
        affinity_name (str): Affinity group name
        cluster_name (str): Cluster name

    Returns:
        AffinityGroup: Affinity group object if exist, otherwise None
    """
    cluster_obj = get_cluster_object(cluster_name)
    affinity_groups = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name="affinitygroups", attr="affinity_group"
    )
    for affinity_group in affinity_groups:
        if affinity_group.get_name() == affinity_name:
            return affinity_group
    return None


def get_affinity_groups_obj(cluster_name):
    """
    Get affinity groups object from the cluster

    Args:
        cluster_name (str): Cluster name

    Returns:
        AffinityGroups: Cluster affinity groups object
    """
    link_name = "affinitygroups"
    cluster_obj = get_cluster_object(cluster_name)
    return CLUSTER_API.getElemFromLink(
        cluster_obj, link_name=link_name, get_href=True
    )


@ll_general.generate_logs(step=True)
def create_affinity_group(cluster_name, **kwargs):
    """
    Create new affinity group under given cluster

    Args:
        cluster_name (str): Cluster name

    Keyword Args:
        name (str): Affinity group name
        description (str): Affinity group description
        positive (bool): Affinity group positive behaviour
            (deprecated, use hosts_rule and vms_rule instead of)
        enforcing (bool): Affinity group enforcing behaviour
            (deprecated, use hosts_rule and vms_rule instead of)
        hosts_rule (dict): Host to VM affinity group rules
            (positive, enforcing)
        vms_rule (dict): VM to VM affinity group rules
            (positive, enforcing, enabled)
        hosts (list): Hosts names to add to the affinity group
        vms (list): VM's names to add to the affinity group

    Returns:
        bool: True, if add new affinity group action succeed, otherwise False
    """
    affinity_groups_obj = get_affinity_groups_obj(cluster_name=cluster_name)
    try:
        affinity_group_obj = _prepare_affinity_group_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    return AFFINITY_API.create(
        affinity_group_obj, True, collection=affinity_groups_obj
    )[1]


@ll_general.generate_logs(step=True)
def update_affinity_group(cluster_name, old_name, **kwargs):
    """
    Update affinity group under the given cluster

    Args:
        cluster_name (str): Cluster name
        old_name (str): Affinity group name

    Keyword Args:
        name (str): Affinity group new name
        description (str): Affinity group description
        positive (bool): Affinity group positive behaviour
            (deprecated, use hosts_rule and vms_rule instead of)
        enforcing (bool): Affinity group enforcing behaviour
            (deprecated, use hosts_rule and vms_rule instead of)
        hosts_rule (dict): Host to VM affinity group rules
            (positive, enforcing)
        vms_rule (dict): VM to VM affinity group rules
            (positive, enforcing, enabled)
        hosts (list): Hosts names to add to the affinity group
        vms (list): VM's names to add to the affinity group

    Returns:
        bool: True, if add new affinity group action succeed, otherwise False
    """
    old_affinity_group = get_affinity_group_obj(
        affinity_name=old_name, cluster_name=cluster_name
    )
    try:
        affinity_group_obj = _prepare_affinity_group_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    return AFFINITY_API.update(
        old_affinity_group, affinity_group_obj, positive=True
    )[1]


@ll_general.generate_logs()
def remove_affinity_group(affinity_name, cluster_name):
    """
    Remove affinity group under given cluster

    Args:
        cluster_name (str): Cluster name
        affinity_name (str): Affinity group name

    Returns:
        bool: True, if remove affinity group action succeed, otherwise False
    """
    affinity_group_obj = get_affinity_group_obj(affinity_name, cluster_name)
    status = AFFINITY_API.delete(affinity_group_obj, True)
    return status


def vm_exists_under_affinity_group(affinity_name, cluster_name, vm_name):
    """
    Check if VM exist under affinity group

    Args:
        affinity_name (str): Affinity group name
        cluster_name (str): Cluster name
        vm_name (str): VM name

    Returns:
        bool: True, if VM exist under affinity group, otherwise False
    """
    vm_id = VM_API.find(vm_name).get_id()
    affinity_group_obj = get_affinity_group_obj(affinity_name, cluster_name)
    affinity_vms_obj = AFFINITY_API.getElemFromLink(
        affinity_group_obj, link_name=VMS_NAME, attr="vm"
    )
    for vm in affinity_vms_obj:
        if vm_id == vm.get_id():
            return True
    return False


def _prepare_cpu_profile_object(**kwargs):
    """
    Prepare cpu profile object

    :param kwargs: name: type=str
                   description: type=str
                   qos: type=QoS Instance
    :return: CpuProfile object or raise exception
    """
    return ll_general.prepare_ds_object('CpuProfile', **kwargs)


def get_cpu_profile_obj(cluster_name, cpu_prof_name):
    """
    Get cpu profile by name from specific cluster

    :param cluster_name: cpu profile cluster
    :param cpu_prof_name: name of cpu profile to get
    :return: CpuProfile instance or None
    """
    cluster_obj = get_cluster_object(cluster_name)
    cpu_profiles = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name='cpuprofiles', attr='cpu_profile'
    )
    for cpu_profile in cpu_profiles:
        if cpu_profile.get_name() == cpu_prof_name:
            return cpu_profile
    return None


def add_cpu_profile(cluster_name, **kwargs):
    """
    Add new cpu profile to cluster

    :param cluster_name: cluster to create cpu profile
    :param kwargs: name: type=str
                   description: type=str
                   qos: type=QOS instance
    :return: True, if creation success, otherwise False
    """
    cpu_profile_name = kwargs.get("name")
    cluster_obj = get_cluster_object(cluster_name)
    cpu_profiles_obj = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name='cpuprofiles', get_href=True
    )
    try:
        cpu_profile_obj = _prepare_cpu_profile_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    log_info, log_error = ll_general.get_log_msg(
        log_action="Add",
        obj_type=CPU_PROFILE_NAME,
        obj_name=cpu_profile_name,
        positive=True, **kwargs
    )
    logger.info(log_info)
    status = CPU_PROFILE_API.create(
        cpu_profile_obj, True, collection=cpu_profiles_obj
    )[1]
    if not status:
        logger.error(log_error)
    return status


def remove_cpu_profile(cluster_name, cpu_prof_name):
    """
    Remove cpu profile from cluster

    :param cluster_name: cpu profile cluster
    :param cpu_prof_name: name of cpu profile to remove
    :return: True, if cpu profile removed, otherwise False
    """
    cpu_profile_obj = get_cpu_profile_obj(cluster_name, cpu_prof_name)
    if not cpu_profile_obj:
        return False
    return CPU_PROFILE_API.delete(cpu_profile_obj, True)


def get_cpu_profile_id_by_name(cluster_name, cpu_profile_name):
    """
    Get Cpu Profile id by name

    :param cluster_name: cpu profile cluster
    :param cpu_profile_name: cpu profile name
    :return: cpu profile id or None
    """
    cpu_profile_obj = get_cpu_profile_obj(cluster_name, cpu_profile_name)
    return cpu_profile_obj.id if cpu_profile_obj else None


def get_cluster_management_network(cluster):
    """
    Get management network object for Cluster

    Args:
        cluster (Cluster): Cluster object

    Returns:
        Network: Network management object
    """
    return cluster.get_management_network()


def get_cluster_list():
    """
    Get list of cluster objects

    Returns:
        list: List of cluster objects
    """
    return util.get(abs_link=False)


def get_cluster_names_list():
    """
    Get list of cluster names

    Returns:
        list: List of cluster names
    """
    return [cl.get_name() for cl in get_cluster_list()]


def get_rng_sources_from_cluster(cluster_name):
    """
    Get list of random number generator sources from cluster

    Args:
        cluster_name (str): Name of the Cluster

    Returns:
        list of str: Rng sources
    """
    cl_obj = get_cluster_object(cluster_name)
    return cl_obj.get_required_rng_sources().get_required_rng_source()


def get_all_vm_pools_in_cluster(cluster_name):
    """
    Get a list of vm pools in the cluster

    Args:
        cluster_name (str): cluster name

    Returns:
        list: List of vm pools names in the cluster
    """
    all_vm_pools = ll_vmpools.get_all_vm_pools()
    cluster_obj = get_cluster_object(cluster_name)
    cluster_vm_pools = [
        pool_obj.get_name() for pool_obj in all_vm_pools if
        pool_obj.get_cluster().get_id() == cluster_obj.get_id()
    ]
    logger.info(
        "Existing vm pools in cluster %s: %s", cluster_name, cluster_vm_pools
    )
    return cluster_vm_pools


def get_cluster_cpu_level(cluster_name):
    """
    Get cluster CPU level

    Args:
        cluster_name (str): cluster name

    Returns:
        str: cluster CPU level
    """
    cluster_obj = get_cluster_object(cluster_name=cluster_name)
    cpu_type = cluster_obj.get_cpu().get_type()
    logger.info("Cluster CPU type is %s", cpu_type)
    return cpu_type


def set_cluster_cpu_level(cluster_name, cluster_cpu_level):
    """
    Set cluster CPU level

    Args:
        cluster_name (str): cluster name
        cluster_cpu_level (str): cluster CPU level to set

    Returns:
        bool: True if it was successful, otherwise False
    """
    if cluster_cpu_level == get_cluster_cpu_level(cluster_name=cluster_name):
        return True

    if not updateCluster(
        positive=True, cluster=cluster_name, cpu=cluster_cpu_level
    ):
        return False

    return cluster_cpu_level == get_cluster_cpu_level(
        cluster_name=cluster_name
    )


def get_cluster_data_center_name(cluster_name):
    """
    Get name of the cluster's data center

    Args:
        cluster_name (str): Name of the cluster

    Returns:
         str: Name of data center
    """
    dc_id = get_cluster_object(cluster_name).data_center.get_id()
    return ll_dc.get_data_center(dc_id, key='id').name
