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
import logging
from Queue import Queue

from art.core_api import is_action
from art.core_api.apis_utils import getDS
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.test_handler.exceptions as exceptions
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.utils.test_utils import get_api, split
from art.rhevm_api.tests_lib.low_level.general import prepare_ds_object
from art.rhevm_api.tests_lib.low_level.hosts import(
    activateHost, deactivateHost, updateHost
)
from art.rhevm_api.utils.xpath_utils import XPathMatch
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
CPU = getDS('CPU')
KSM = getDS('KSM')
CLUSTER_API = get_api('cluster', 'clusters')
AFFINITY_API = get_api('affinity_group', 'affinity_groups')
CPU_PROFILE_API = get_api('cpu_profile', 'cpu_profiles')
VM_API = get_api('vm', 'vms')

xpathMatch = is_action('xpathClusters', id_name='xpathMatch')(XPathMatch(util))
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
        clVersion = Version(major=majorV, minor=minorV)
        cl.set_version(clVersion)

    if 'cpu' in kwargs:
        clCPU = CPU(id=kwargs.pop('cpu'))
        cl.set_cpu(clCPU)

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

    if 'scheduling_policy' in kwargs:
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
            name=kwargs.pop('scheduling_policy'),
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
        cl.set_ksm(KSM(enabled=kwargs.pop('ksm_enabled')))

    if 'ha_reservation' in kwargs:
        cl.set_ha_reservation(kwargs.pop('ha_reservation'))

    return cl


@is_action()
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


@is_action()
def updateCluster(positive, cluster, **kwargs):
    '''
    Description: Update cluster
    Author: edolinin
    Parameters:
       * cluster - name of a cluster
       * name - change cluster name
       * cpu - CPU name
       * data_center - name of data center attached to cluster
       * description - description of cluster
       * version - supported version (2.2, 3)
       * gluster_support - Gluster support (boolean)
       * virt_support - virt support (boolean)
       * mem_ovrcmt_prc - The percentage of host memory allowed
                          Recommended values include 100 (None),
                          150 (Server Load) and 200 (Desktop Load)
       * thrhld_high - The highest CPU usage percentage the host can have
                       before being considered overloaded
       * thrhld_low - the lowest CPU usage percentage the host can have
                       before being considered underutilized.
       * duration - the number of seconds the host needs to be overloaded
                    before the scheduler starts and moves the load to
                    another host
       * scheduling_policy - VM scheduling mode for hosts in the cluster
                             (evenly_distributed, power_saving)
       * properties - properties of scheduling policy
       * transparent_hugepages - boolean, Defines the availability of
                                Transparent Hugepages
       * on_error - in case of non - operational
                    (migrate, do_not_migrate, migrate_highly_available)
       * threads - if True, will count threads as cores, otherwise counts
                    only cores
       * ballooning_enabled - if True, enables ballooning on cluster
       * ksm_enabled - if True, enables KSM on cluster
       * ha_reservation - if True, enables Ha Reservation on cluster
    Return: status (True if cluster was removed properly, False otherwise)
    '''

    cl = util.find(cluster)
    clUpd = _prepareClusterObject(**kwargs)
    clUpd, status = util.update(cl, clUpd, positive)

    return status


@is_action()
def removeCluster(positive, cluster):
    '''
    Description: remove cluster
    Author: edolinin
    Parameters:
       * cluster - name of a cluster that should be removed
    Return: status (True if cluster was removed properly, False otherwise)
    '''

    cl = util.find(cluster)

    return util.delete(cl, positive)


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


@is_action()
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


@is_action()
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


@is_action()
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
                   hostObj.get_status().get_state() == "up", hostObjList)
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


def attachHostToCluster(positive, host, cluster):
    """
    Function attaches host to cluster.
        host       = host name
        cluster    = cluster name
    """

    util.logger.info("Attach Host %s to Cluster %s" % (host, cluster))
    # Find cluster
    try:
        util.find(cluster)
        hostObj = hostUtil.find(host)
    except EntityNotFound:
        return not positive

    # Deactivate host if not already in 'Maintenance'
    if not hostObj.get_status() == 'Maintenance':
        util.logger.info("Suspending Host %s" % host)
        if not deactivateHost(positive, host):
            util.logger.error("Failed to deactivate Host %s" % host)
            return False

    # Update host cluster
    util.logger.info("Updating Host %s" % host)
    updateStat = updateHost(positive=positive, host=host, cluster=cluster)
    if not updateStat:
        util.logger.error('updateHost Failed')
        return False

    # Activate host
    if not activateHost(positive, host):
        util.logger.error("Failed to activate Host %s" % host)
        return False

    # Verify host indeed attached to cluster
    return isHostAttachedToCluster(positive, host, cluster)


@is_action()
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


@is_action()
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

    :param kwargs: name: type=str
                   positive: type=str
                   enforcing: type=str
    :return: AffinityGroup instance or raise exception
    """
    return prepare_ds_object('AffinityGroup', **kwargs)


def get_affinity_group_obj(affinity_name, cluster_name):
    """
    Get affinity group object by name.

    :param affinity_name: name of affinity group
    :type affinity_name: str
    :param cluster_name: cluster name
    :type cluster_name: str
    :returns: affinity group object if exist, otherwise None
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
    Create new affinity group under given cluster.

    :param cluster_name: name of cluster where to create affinity group
    :type cluster_name: str
    :param kwargs: name: type=str
                   description: type=str
                   positive: type=str
                   enforcing: type=str
    :return: True, if affinity creation success, else False
    """
    link_name = 'affinitygroups'
    cluster_obj = get_cluster_object(cluster_name)
    affinity_groups_obj = CLUSTER_API.getElemFromLink(
        cluster_obj, link_name=link_name, get_href=True
    )
    try:
        affinity_group_obj = _prepare_affinity_group_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False
    return AFFINITY_API.create(
        affinity_group_obj, True, collection=affinity_groups_obj)[1]


def update_affinity_group(cluster_name, affinity_name, **kwargs):
    """
    Update affinity group

    :param cluster_name: name of cluster where affinity group
    :param affinity_name: name of affinity group
    :param kwargs: name: type=str
                   description: type=str
                   positive: type=str
                   enforcing: type=str
    :return: True, if affinity group update success, else False
    """
    old_aff_group_obj = get_affinity_group_obj(cluster_name, affinity_name)
    if not old_aff_group_obj:
        return False
    try:
        new_aff_group_obj = _prepare_affinity_group_object(**kwargs)
    except exceptions.RHEVMEntityException:
        return False

    return AFFINITY_API.update(
        old_aff_group_obj, new_aff_group_obj, True)[1]


def remove_affinity_group(affinity_name, cluster_name):
    """
    Remove affinity group under given cluster.

    :param affinity_name: name of affinity group
    :type affinity_name: str
    :param cluster_name: cluster name
    :type cluster_name: str
    :returns: True, if affinity group removed, otherwise False
    """
    affinity_group_obj = get_affinity_group_obj(affinity_name, cluster_name)
    return AFFINITY_API.delete(affinity_group_obj, True)


def populate_affinity_with_vms(affinity_name, cluster_name, vms):
    """
    Populate affinity group with vms under given cluster.

    :param affinity_name: name of affinity group
    :type affinity_name: str
    :param cluster_name: cluster name
    :type cluster_name: str
    :param vms: name of vms to insert into affinity group
    :type vms: list
    :returns: True, if affinity group populated successfully, otherwise False
    """
    affinity_group_obj = get_affinity_group_obj(affinity_name, cluster_name)
    affinity_vms_obj = AFFINITY_API.getElemFromLink(
        affinity_group_obj, link_name='vms', get_href=True
    )
    for vm in vms:
        vm_id = VM_API.find(vm).get_id()
        vm_id_obj = getDS('VM')(id=vm_id)
        out, status = VM_API.create(
            vm_id_obj, True, async=True, collection=affinity_vms_obj
        )
        if not status:
            return False
    return True


def check_vm_affinity_group(affinity_name, cluster_name, vm_name):
    """
    Check if vm in specific affinity group.

    :param affinity_name: name of affinity group
    :type affinity_name: str
    :param cluster_name: cluster name
    :type cluster_name: str
    :param vm_name: name of vm
    :type vm_name: str
    :returns: True, if vm in specific affinity group, otherwise False
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
    return prepare_ds_object('CpuProfile', **kwargs)


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
