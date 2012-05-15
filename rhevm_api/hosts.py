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

from utils.data_structures import Host
from utils.test_utils import get_api

ELEMENT = 'host'
COLLECTION = 'hosts'
util = get_api(ELEMENT, COLLECTION)


def activateHost(positive, host, wait=False):
    '''
    Description: activate host (set status to UP)
    Author: edolinin
    Parameters:
       * host - name of a host to be activated
    Return: status (True if host was activated properly, False otherwise)
    '''
    hostObj = util.find(host)

    status = util.syncAction(hostObj, "activate", positive)
    
    if status and wait and positive:
        testHostStatus = util.waitForElemStatus(hostObj, "up", 10)
    else:
        testHostStatus = True

    return status and testHostStatus


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
        logger.error('updateHost Failed')
        return False

    # Activate host
    if not activateHost(positive, host):
        logger.error("Failed to activate Host %s" % host)
        return False

    # Verify host indeed attached to cluster
    return isHostAttachedToCluster(positive, host, cluster)
