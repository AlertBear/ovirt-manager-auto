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
from Queue import Queue
from threading import Thread

from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api, split
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level.hosts import activateHost, \
    deactivateHost, updateHost
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.rhevm_api.utils.test_utils import searchForObj
from art.core_api import is_action

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

xpathMatch = is_action('xpathClusters', id_name='xpathMatch')(XPathMatch(util))


def _prepareClusterObject(**kwargs):

    cl = Cluster()

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
            transparentHugepages = \
                TransparentHugePages(enabled=kwargs.
                                     pop('transparent_hugepages'))

        memoryPolicy = MemoryPolicy(overcommit=overcommit,
                                    transparent_hugepages=transparentHugepages)

        cl.set_memory_policy(memoryPolicy)

    if 'scheduling_policy' in kwargs:
        thresholds = None
        thresholdLow = kwargs.get('thrhld_low')
        thresholdHigh = kwargs.get('thrhld_high')
        thresholdDuration = kwargs.get('duration')

        # If at least one threshold tag parameter is set.
        if max(thresholdLow, thresholdHigh, thresholdDuration) is not None:
            thresholds = SchedulingPolicyThresholds(high=thresholdHigh,
                                                    duration=thresholdDuration,
                                                    low=thresholdLow)

        schedulingPolicy = \
            SchedulingPolicy(policy=kwargs.pop('scheduling_policy'),
                             thresholds=thresholds)

        cl.set_scheduling_policy(schedulingPolicy)

    errorHandling = None
    if 'on_error' in kwargs:
        errorHandling = ErrorHandling(on_error=kwargs.pop('on_error'))
        cl.set_error_handling(errorHandling)

    threads = kwargs.pop('threads_as_cores', None)
    if threads is not None:
        cl.set_threads_as_cores(threads)

    return cl


@is_action()
def addCluster(positive, **kwargs):
    '''
    Description: add cluster
    Author: edolinin
    Parameters:
       * name - name of a cluster
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
       * transparent_hugepages - boolean, Defines the availability of
                                Transparent Hugepages
       * on_error - in case of non - operational
                    (migrate, do_not_migrate, migrate_highly_available)
       * threads - if True, will count threads as cores, otherwise counts
                   only cores
    Return: status (True if cluster was removed properly, False otherwise)
    '''

    cl = _prepareClusterObject(**kwargs)
    cl, status = util.create(cl, positive)
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
       * transparent_hugepages - boolean, Defines the availability of
                                Transparent Hugepages
       * on_error - in case of non - operational
                    (migrate, do_not_migrate, migrate_highly_available)
       * threads - if True, will count threads as cores, otherwise counts
                    only cores
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

    tasksQ = Queue()
    resultsQ = Queue()
    threads = set()
    clsList = split(clusters)
    num_worker_threads = len(clsList)
    for i in range(num_worker_threads):
        t = Thread(target=removeClusterAsynch, name='Cluster removing',
                   args=(positive, tasksQ, resultsQ))
        threads.add(t)
        t.daemon = False
        t.start()

    for cl in clsList:
        tasksQ.put(cl)
    tasksQ.join()  # block until all tasks are done
    util.logger.info(threads)
    for t in threads:
        t.join()

    status = True
    while not resultsQ.empty():
        cl, removalOK = resultsQ.get()
        if removalOK:
            util.logger.info("Cluster '%s' deleted asynchronously.", cl)
        else:
            util.logger.error("Failed to asynchronously remove cluster '%s'.",
                              cl)
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
        clObj = util.find(cluster)
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

            if (None is not thrhld_low) and \
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
