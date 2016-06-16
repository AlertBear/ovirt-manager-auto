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
import time
from Queue import Queue

import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.test_handler.exceptions as exceptions
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import getDS, data_st
from art.rhevm_api.tests_lib.low_level.hosts import(
    activateHost, deactivateHost,
)
from art.rhevm_api.tests_lib.low_level.scheduling_policies import (
    get_scheduling_policy_id
)
from art.rhevm_api.utils.test_utils import get_api, split
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

CLUSTER_NAME = "cluster"
AFFINITY_GROUP_NAME = "affinity group"

logger = logging.getLogger(__name__)


def _prepareClusterObject(**kwargs):

    cl = Cluster()
    if 'management_network' in kwargs:
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

        memoryPolicy = MemoryPolicy(overcommit=overcommit,
                                    transparent_hugepages=transparentHugepages)

        cl.set_memory_policy(memoryPolicy)

    scheduling_policy = kwargs.pop('scheduling_policy', None)
    if scheduling_policy:
        scheduling_policy_id = get_scheduling_policy_id(
            scheduling_policy_name=scheduling_policy
        )
        properties = None
        thresholds = None
        threshold_low = kwargs.get('thrhld_low')
        threshold_high = kwargs.get('thrhld_high')
        threshold_dur = kwargs.get('duration')
        if 'properties' in kwargs:
            properties = getDS('Properties')()
            for name, value in kwargs.get('properties').iteritems():
                properties.add_property(
                    getDS('Property')(name=name, value=value)
                )

        # If at least one threshold tag parameter is set.
        if max(threshold_low, threshold_high, threshold_dur) is not None:
            thresholds = SchedulingPolicyThresholds(
                high=threshold_high, duration=threshold_dur, low=threshold_low
            )

        scheduling_policy = SchedulingPolicy(
            id=scheduling_policy_id,
            thresholds=thresholds,
            properties=properties
        )

        cl.set_scheduling_policy(scheduling_policy)

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

    if 'ha_reservation' in kwargs:
        cl.set_ha_reservation(kwargs.pop('ha_reservation'))

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
        thrhld_high (str): The highest CPU usage percentage the host can have
            before being considered overloaded
        thrhld_low (str): The lowest CPU usage percentage the host can have
            before being considered underutilized.
        duration (int): The number of seconds the host needs to be overloaded
            before the scheduler starts and moves the load to another host
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
        thrhld_high (int): The highest CPU usage percentage the host can have
            before being considered overloaded
        thrhld_low (int): The lowest CPU usage percentage the host can have
            before being considered underutilized.
        duration (int): The number of seconds the host needs to be overloaded
            before the scheduler starts and moves the load to another host
        scheduling_policy (str): Cluster scheduling policy
        properties (dict): Scheduling policy properties
        transparent_hugepages (booL): Defines the availability of
            Transparent Hugepages
        on_error (str): Migration behaviour for VM's on non-operational host
        threads (bool): Count threads as cores
        ballooning_enabled (bool): Enables ballooning on cluster
        ksm_enabled (bool): Enables KSM on cluster
        ha_reservation (bool): Enables HA Reservation on cluster
        ksm_merge_across_nodes (bool): Merge KSM pages across NUMA nodes

    Returns:
        bool: True, if update succeed, otherwise False
    """
    old_cluster_obj = util.find(cluster)
    new_cluster_obj = _prepareClusterObject(**kwargs)
    log_info, log_error = ll_general.get_log_msg(
        action="Update", obj_type=CLUSTER_NAME, obj_name=cluster,
        positive=positive, **kwargs
    )
    logger.info(log_info)
    new_cluster_obj, status = util.update(
        old_cluster_obj, new_cluster_obj, positive
    )
    if not status:
        logger.error(log_error)
    return status


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
        action="Remove", obj_type="cluster", obj_name=cluster,
        positive=positive
    )
    logger.info(log_info)
    cluster_obj = util.find(cluster)
    res = util.delete(cluster_obj, positive)
    if not res:
        logger.error(log_error)
    return res


def removeClusterAsynch(positive, tasksQ, resultsQ):
    '''
    Removes the cluster. It's supposed to be a worker of Thread.
    '''

    cl = tasksQ.get(True)
    status = False
    try:
        clObj = util.find(cl)
        status = util.delete(clObj, positive)
    except EntityNotFound as e:
        util.logger.error(str(e))
    finally:
        resultsQ.put((cl, status))
        tasksQ.task_done()


def waitForClustersGone(positive, clusters, timeout=30, samplingPeriod=5):
    '''
    Wait for clusters to disappear from the setup. This function will block up
    to `timeout` seconds, sampling the clusters list every
    `samplingPeriod` seconds, until no cluster specified by
    names in `clusters` exists.

    Parameters:
        * clusters - comma (and no space) separated string of cluster names
                     to wait for.
        * timeout - Time in seconds for the clusters to disappear.
        * samplingPeriod - Time in seconds for sampling the cluster list.
    '''

    clsList = split(clusters)
    t_start = time.time()
    while time.time() - t_start < timeout and 0 < timeout:
        clusters = util.get(absLink=False)
        remainingCls = []
        for cl in clusters:
            clName = getattr(cl, 'name')
            if clName in clsList:
                remainingCls.append(clName)

        if len(remainingCls) > 0:
            util.logger.info("Waiting for %d clusters to disappear.",
                             len(remainingCls))
            time.sleep(samplingPeriod)
        else:
            util.logger.info("All %d clusters are gone.", len(clsList))
            return positive

    remainingClsNames = [cl for cl in remainingCls]
    util.logger.error("Clusters %s didn't disappear until timeout.",
                      remainingClsNames)
    return not positive


def removeClusters(positive, clusters):
    '''
    Removes the clusters specified by `clusters` commas separated list of
    cluster names.
    Author: jhenner
    Parameters:
        * clusters - Comma (no space) separated list of cluster names.
    '''

    resultsQ = Queue()
    clsList = split(clusters)
    for cl in clsList:
        resultsQ.put((cl, removeCluster(positive, cl)))

    status = True
    while not resultsQ.empty():
        cl, removalOK = resultsQ.get()
        if removalOK:
            util.logger.info("Cluster '%s' deleted.", cl)
        else:
            util.logger.error("Failed to remove cluster '%s'.", cl)
            status = False

    return status and waitForClustersGone(positive, clusters)


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


def isHostAttachedToCluster(positive, host, cluster):
    """
    Function checks if host attached to cluster.
        host       = host name
        cluster    = cluster name
    """
    # Find cluster
    try:
        clId = util.find(cluster).get_id()
        hostObj = hostUtil.find(host)
    except EntityNotFound:
        return not positive

    # Check if host connected to cluster
    return hostObj.get_cluster().get_id() == clId


def connectClusterToDataCenter(positive, cluster, datacenter):
    """
    Function connects cluster to dataCenter
    If cluster already connected to datacenter, it will just return true
    If cluster's "datacenter" field is empty, it will be updated with
    datacenter else, function will return False, since cluster's
    datacenter field cannot be updated, if not empty
        cluster    = cluster name
        datacenter = data center name
    """
    hostList = []
    dcFieldExist = True

    # Search for datacenter
    try:
        dcId = dcUtil.find(datacenter).get_id()
        util.logger.info("Looking for cluster %s" % cluster)
        clusterObj = util.find(cluster)
    except EntityNotFound:
        return not positive

    clId = clusterObj.get_id()

    # Check if datacenter field exist in cluster object
    try:
        clusterdcId = clusterObj.get_data_center().get_id()
    except:
        dcFieldExist = False

    # Check if cluster already connected to datacenter
    if dcFieldExist and clusterdcId == dcId:
        return positive
    # Get all hosts in setup
    try:
        hostObjList = hostUtil.get(absLink=False)
    except EntityNotFound:
        return not positive

    # Deactivate all "UP" hosts, which are connected to cluster
    hosts = filter(lambda hostObj: hostObj.get_cluster().get_id() == clId and
                   hostObj.get_status() == "up", hostObjList)
    for hostObj in hosts:
        if not deactivateHost(positive, hostObj.get_name()):
            util.logger.error('deactivateHost Failed')
            return False
        hostList.append(hostObj)

    # Update cluster: will work only in case data center is empty
    if not updateCluster(positive, cluster=cluster, data_center=datacenter):
        util.logger.error('updateCluster with dataCenter failed')
        return False

    # Activate the hosts that were deactivated earlier
    for hostObj in hostList:
        if not activateHost(positive, hostObj.get_name()):
            util.logger.error('activateHost Failed')
            return False
    return True


def checkClusterParams(positive, cluster, thrhld_low=None, thrhld_high=None,
                       duration=None, scheduling_policy=None,
                       mem_ovrcmt_prc=None, mem_trnspt_hp=None,
                       gluster_support=None, virt_support=None):

    cl = util.find(cluster)

    ERROR = "%s of %s has wrong value, expected: %s, actual: %s."
    status = True

    try:
        # Check the scheduling policy thresholds and duration if requested:
        if max(thrhld_low, thrhld_high, duration, scheduling_policy) \
                is not None:
            clspth = cl.get_scheduling_policy().get_thresholds()
            if (None is not thrhld_low) and \
                    (clspth.get_low() != int(thrhld_low)):
                status = False
                util.logger.error(ERROR % ("Thresholds low", cl.get_name(),
                                           thrhld_low, clspth.get_low()))

            if (None is not thrhld_high) and \
                    (clspth.get_high() != int(thrhld_high)):
                status = False
                util.logger.error(ERROR % ("Thresholds high", cl.get_name(),
                                           thrhld_high, clspth.get_high()))

            if (None is not duration) and \
                    (clspth.get_duration() != int(duration)):
                status = False
                util.logger.error(ERROR % ("Duration", cl.get_name(), duration,
                                           clspth.get_duration()))

            # Check the scheduling_policy strategy if requested:
            if (None is not scheduling_policy) and \
                    (cl.get_scheduling_policy().get_policy() !=
                     scheduling_policy):
                status = False
                util.logger.error(ERROR % ("Scheduling policy", cl.get_name(),
                                           scheduling_policy,
                                           cl.get_scheduling_policy().
                                           get_policy()))

        # Check the memory policy if requested:
        if (None is not mem_ovrcmt_prc) \
                and (cl.get_memory_policy().get_overcommit().get_percent()
                     != int(mem_ovrcmt_prc)):
            status = False
            util.logger.error(ERROR % ("Memory overcommit percent",
                                       cl.get_name(), mem_ovrcmt_prc,
                                       cl.get_memory_policy().
                                       get_overcommit().get_percent()))

        # Check gluster support policy if requested:
        if (None is not gluster_support)\
                and (cl.get_gluster_service() != gluster_support):
            status = False
            util.logger.error(ERROR % ("Gluster support", cl.get_name(),
                                       gluster_support,
                                       cl.get_gluster_service()))

        # Check virt support policy if requested:
        if (None is not virt_support)\
                and (cl.get_virt_service() != virt_support):
            status = False
            util.logger.error(ERROR % ("Virt support", cl.get_name(),
                                       virt_support, cl.get_virt_service()))

    except AttributeError as e:
        util.logger.error("checkClusterParams: %s" % str(e))
        return not positive
    return status == positive


def get_cluster_object(cluster_name):
    """
    Description: get cluster object by name
    Author: ratamir
    Parameters:
        * cluster_name - cluster name
    Return: cluster object, or raise EntityNotFound exception
    """
    cluster_obj = CLUSTER_API.find(cluster_name)
    return cluster_obj


def _prepare_affinity_group_object(**kwargs):
    """
    Prepare affinity group data structure object

    Keyword Args:
        name (str): Affinity group name
        description (str): Affinity group description
        positive (bool): Affinity group positive behaviour
        enforcing (bool): Affinity group enforcing behaviour

    Returns:
        AffinityGroup: AffinityGroup instance
    """
    return ll_general.prepare_ds_object('AffinityGroup', **kwargs)


def get_affinity_groups_from_cluster(cluster_name):
    """
    Get list of affinity groups objects from cluster

    Args:
        cluster_name (str): Cluster name

    Returns:
        list: Affinity Groups
    """
    logger.info("Get all affinity groups from cluster %s", cluster_name)
    cluster_obj = get_cluster_object(cluster_name=cluster_name)
    return CLUSTER_API.getElemFromLink(
        elm=cluster_obj, link_name="affinitygroups", attr="affinity_group"
    )


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
        cluster_obj, link_name='affinitygroups', attr='affinity_group'
    )
    for affinity_group in affinity_groups:
        if affinity_group.get_name() == affinity_name:
            return affinity_group
    return None


def create_affinity_group(cluster_name, **kwargs):
    """
    Create new affinity group under given cluster

    Args:
        cluster_name (str): Cluster name

    Keyword Args:
        name (str): Affinity group name
        description (str): Affinity group description
        positive (bool): Affinity group positive behaviour
        enforcing (bool): Affinity group enforcing behaviour

    Returns:
        bool: True, if add new affinity group action succeed, otherwise False
    """
    link_name = 'affinitygroups'
    cluster_obj = get_cluster_object(cluster_name)
    affinity_name = kwargs.get("name")
    affinity_groups_obj = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name=link_name, get_href=True
    )
    log_info, log_error = ll_general.get_log_msg(
        action="Create", obj_type=AFFINITY_GROUP_NAME, obj_name=affinity_name,
        extra_txt="on cluster %s with parameters: %s" % (cluster_name, kwargs)
    )
    try:
        affinity_group_obj = _prepare_affinity_group_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    logger.info(log_info)
    status = AFFINITY_API.create(
        affinity_group_obj, True, collection=affinity_groups_obj
    )[1]
    if not status:
        logger.error(log_error)
    return status


def update_affinity_group(cluster_name, affinity_name, **kwargs):
    """
    Update affinity group

    Args:
        cluster_name (str): Cluster name
        affinity_name (str): Affinity group name

    Keyword Args:
        name (str): Affinity group name
        description (str): Affinity group description
        positive (bool): Affinity group positive behaviour
        enforcing (bool): Affinity group enforcing behaviour

    Returns:
        bool: True, if update affinity group action succeed, otherwise False
    """
    old_aff_group_obj = get_affinity_group_obj(cluster_name, affinity_name)
    log_info, log_error = ll_general.get_log_msg(
        action="Update", obj_type=AFFINITY_GROUP_NAME, obj_name=affinity_name,
        extra_txt="on cluster %s" % cluster_name, **kwargs
    )
    if not old_aff_group_obj:
        return False
    try:
        new_aff_group_obj = _prepare_affinity_group_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    logger.info(log_info)
    status = AFFINITY_API.update(
        old_aff_group_obj, new_aff_group_obj, True
    )[1]
    if not status:
        logger.error(log_error)


def remove_affinity_group(affinity_name, cluster_name):
    """
    Remove affinity group under given cluster

    Args:
        cluster_name (str): Cluster name
        affinity_name (str): Affinity group name

    Returns:
        bool: True, if remove affinity group action succeed, otherwise False
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type=AFFINITY_GROUP_NAME, obj_name=affinity_name,
        extra_txt="from cluster %s" % cluster_name
    )
    logger.info(log_info)
    affinity_group_obj = get_affinity_group_obj(affinity_name, cluster_name)
    status = AFFINITY_API.delete(affinity_group_obj, True)
    if not status:
        logger.error(log_error)
    return status


def populate_affinity_with_vms(affinity_name, cluster_name, vms):
    """
    Populate affinity group with VM's

    Args:
        affinity_name (str): Affinity group name
        cluster_name (str): Cluster name
        vms (list): VM's to insert into affinity group

    Returns:
        bool: True, if affinity group populated successfully, otherwise False
    """
    affinity_group_obj = get_affinity_group_obj(affinity_name, cluster_name)
    affinity_vms_obj = AFFINITY_API.getElemFromLink(
        affinity_group_obj, link_name='vms', get_href=True
    )
    for vm in vms:
        vm_id = VM_API.find(vm).get_id()
        vm_id_obj = getDS('VM')(id=vm_id)
        logger.info("Add VM %s to affinity group %s", vm, affinity_name)
        out, status = VM_API.create(
            vm_id_obj, True, async=True, collection=affinity_vms_obj
        )
        if not status:
            logger.error(
                "Failed to add VM %s to affinity group %s", vm, affinity_name
            )
            return False
    return True


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
        affinity_group_obj, link_name='vms', attr='vm'
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


def get_all_cpu_profile_names(cluster_name):
    """
    Get all CPU profile from a specific cluster

    :param cluster_name: cluster name
    :type cluster_name: str
    :return: list with CPUs instances
    :rtype: CPUs instances
    """
    cluster_obj = get_cluster_object(cluster_name)
    cpu_profiles = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name='cpuprofiles', attr='cpu_profile'
    )
    return [cpu_profile.get_name() for cpu_profile in cpu_profiles]


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
    cluster_obj = get_cluster_object(cluster_name)
    cpu_profiles_obj = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name='cpuprofiles', get_href=True
    )
    try:
        cpu_profile_obj = _prepare_cpu_profile_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    return CPU_PROFILE_API.create(
        cpu_profile_obj, True, collection=cpu_profiles_obj)[1]


def update_cpu_profile(cluster_name, cpu_prof_name, **kwargs):
    """
    Update cpu profile

    :param cluster_name: cpu profile cluster
    :param cpu_prof_name: name of cpu profile to update
    :param kwargs: name: type=str
                   description: type=str
                   qos: type=QOS instance
    :return: True, if cpu profile updated, otherwise False
    """
    old_cpu_profile_obj = get_cpu_profile_obj(cluster_name, cpu_prof_name)
    if not old_cpu_profile_obj:
        return False
    try:
        new_cpu_profile_obj = _prepare_cpu_profile_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    return CPU_PROFILE_API.update(
        old_cpu_profile_obj, new_cpu_profile_obj, True)[1]


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


def get_cluster_management_network(cluster_name):
    """
    Get management network object for Cluster
    :param cluster_name: Name of the Cluster
    :type cluster_name: str
    :return: network management object
    :rtype: Network
    """
    try:
        cl_obj = CLUSTER_API.query(
            "name=%s" % cluster_name, all_content=True
        )[0]
    except IndexError:
        return None
    return cl_obj.get_management_network()


def get_cluster_list():
    """
    Get list of cluster objects

    :return: List of cluster objects
    :rtype: list
    """
    return util.get(absLink=False)
