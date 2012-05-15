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

from utils.data_structures import Cluster, Version, MemoryOverCommit, \
    TransparentHugePages, MemoryPolicy, SchedulingPolicyThresholds, \
    SchedulingPolicy, ErrorHandlingOptions, CPU
from utils.test_utils import get_api
import re
from utils.validator import compareCollectionSize
from utils.test_utils import split
from Queue import Queue
from threading import Thread
from utils.apis_exceptions import EntityNotFound
import time
from rhevm_api.hosts import activateHost


ELEMENT = 'cluster'
COLLECTION = 'clusters'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
hostUtil = get_api('host', 'hosts')


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
    Return: status (True if cluster was removed properly, False otherwise)
    '''
    
    cpu = kwargs.pop('cpu')
    clusterCPU = CPU(id = cpu)

    majorV, minorV = kwargs.pop('version').split(".")
    cpuVersion = Version(major=majorV, minor = minorV)

    clusterDC = dcUtil.find(kwargs.pop('data_center'))
    
    overcommit = None
    transparentHugepages = None
  
    if kwargs.get('mem_ovrcmt_prc'):
        overcommit = MemoryOverCommit(percent = kwargs.pop('mem_ovrcmt_prc'))

    if kwargs.get('transparent_hugepages'):
        transparentHugepages = TransparentHugePages(enabled = \
                        kwargs.pop('transparent_hugepages'))

    memoryPolicy = MemoryPolicy(overcommit = overcommit,
            transparent_hugepages = transparentHugepages)

    schedulingPolicy = None
    if kwargs.get('scheduling_policy'):
        thresholds = None
        thresholdLow = kwargs.get('thrhld_low')
        thresholdHigh = kwargs.get('thrhld_high')
        thresholdDuration = kwargs.get('duration')

        # If at least one threshold tag parameter is set.
        if max(thresholdLow, thresholdHigh, thresholdDuration) is not None:
            thresholds = SchedulingPolicyThresholds(high = thresholdHigh,
                        duration = thresholdDuration, low = thresholdLow)

        schedulingPolicy = SchedulingPolicy(policy = kwargs.pop('scheduling_policy'),
                            thresholds = thresholds)

    errorHandling = None
    if kwargs.get('on_error'):
        errorHandling = ErrorHandlingOptions(on_error = kwargs.pop('on_error').split(','))

    cl = Cluster(cpu = clusterCPU, version = cpuVersion, 
                data_center = clusterDC, memory_policy = memoryPolicy,
                scheduling_policy = schedulingPolicy,
                error_handling = errorHandling, **kwargs)

    cl, status = util.create(cl, positive)

    return status


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
    Return: status (True if cluster was removed properly, False otherwise)
    '''

    cl = util.find(cluster)

    clUpd = Cluster()

    if 'name' in kwargs:
        clUpd.set_name(kwargs.pop('name'))

    if 'description' in kwargs:
        clUpd.set_description(kwargs.pop('description'))

    if 'version' in kwargs:
        majorV, minorV = kwargs.pop('version').split(".")
        clVersion = Version(major=majorV, minor = minorV)
        clUpd.set_verion(clVersion)

    if 'cpu' in kwargs:
        clCPU = CPU(id = kwargs.pop('cpu'))
        clUpd.set_cpu(clCPU)

    if 'data_center' in kwargs:
        clDC = dcUtil.find(kwargs.pop('data_center'))
        clUpd.set_data_center(clDC)

    if 'mem_ovrcmt_prc' in kwargs or \
    'transparent_hugepages' in kwargs:

        if kwargs.get('mem_ovrcmt_prc'):
            overcommit = MemoryOverCommit(percent = kwargs.pop('mem_ovrcmt_prc'))

        if kwargs.get('transparent_hugepages'):
            transparentHugepages = TransparentHugePages(enabled = \
                            kwargs.pop('transparent_hugepages'))

        memoryPolicy = MemoryPolicy(overcommit = overcommit,
            transparent_hugepages = transparentHugepages)

        clUpd.set_memory_policy(memoryPolicy)

    if 'scheduling_policy' in kwargs:
        thresholds = None
        thresholdLow = kwargs.get('thrhld_low')
        thresholdHigh = kwargs.get('thrhld_high')
        thresholdDuration = kwargs.get('duration')

        # If at least one threshold tag parameter is set.
        if max(thresholdLow, thresholdHigh, thresholdDuration) is not None:
            thresholds = SchedulingPolicyThresholds(high = thresholdHigh,
                        duration = thresholdDuration, low = thresholdLow)

        schedulingPolicy = SchedulingPolicy(policy = kwargs.pop('scheduling_policy'),
                            thresholds = thresholds)

        clUpd.set_scheduling_policy(schedulingPolicy)

    errorHandling = None
    if 'on_error' in kwargs:
        errorHandling = ErrorHandlingOptions(on_error = kwargs.pop('on_error').split(','))
        clUpd.set_error_handling(errorHandling)

    clUpd, status = util.update(cl, clUpd, positive)
    
    return status


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
    Wait for clusters to disappear from the setup. This function will block up to `timeout`
    seconds, sampling the clusters list every `samplingPeriod` seconds,
    until no cluster specified by names in `clusters` exists.

    Parameters:
        * clusters - comma (and no space) separated string of cluster names to wait for.
        * timeout - Time in seconds for the clusters to disapear.
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

        if len(remainingCls)>0:
            util.logger.info("Waiting for %d clusters to disappear.",
                                                len(remainingCls))
            time.sleep(samplingPeriod)
        else:
            util.logger.info("All %d clusters are gone.", len(clsList))
            return positive

    remainingClsNames = [cl.name for cl in remainingCls]
    util.logger.error("Clusters %s didn't disappear until timeout." % remainingClsNames)
    return not positive



def removeClusters(positive, clusters):
    '''
    Removes the clusters specified by `clusters` commas separated list of cluster names.
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
    tasksQ.join() # block until all tasks are done
    util.logger.info(threads)
    for t in threads:
        t.join()

    status = True
    while not resultsQ.empty():
        cl, removalOK = resultsQ.get()
        if removalOK:
            util.logger.info("Cluster '%s' deleted asynchronously." % cl)
        else:
            util.logger.error("Failed to asynchronously remove cluster '%s'." % cl)
            status = False

    return status and waitForClustersGone(positive, clusters)


def searchForCluster(positive, query_key, query_val, key_name):
    '''
    Description: search for clusters by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in cluster object equivalent to query_key, required if expected_count is not set
       * expected_count - expected number of clusters, if not provided - get automatically
    Return: status (True if expected number of clusters equal to found by search, False otherwise)
    '''

    expected_count = 0
    clusters = util.get(absLink=False)

    for cl in clusters:
        clProperty = getattr(cl, key_name)
        if re.match(r'(.*)\*$',query_val):
            if re.match(r'^' + query_val, clProperty):
                expected_count = expected_count + 1
        else:
            if clProperty == query_val:
                expected_count = expected_count + 1

    contsraint = "{0}={1}".format(query_key, query_val)
    query_cls = util.query(contsraint)
    status = compareCollectionSize(query_cls, expected_count, util.logger)

    return status


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
    If cluster's "datacenter" field is empty, it will be updated with datacenter
    else, function will return False, since cluster's datacenter field cannot be updated, if not empty
        cluster    = cluster name
        datacenter = data center name
    """
    hostList = []
    dcFieldExist = True

    # Search for datacenter
    try:
        dcId = dcUtil.find(datacenter).get_id()
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
    hosts = filter(lambda hostObj: hostObj.get_cluster().get_id() == clId and \
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