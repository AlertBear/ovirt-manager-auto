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

from utils.apis_utils import getDS
from rhevm_api.test_utils import get_api, split

ELEMENT = 'gluster_volume'
COLLECTION = 'glustervolumes'
util = get_api(ELEMENT, COLLECTION)
clUtil = get_api('cluster', 'clusters')

GlusterVolume = getDS('GlusterVolume')
TransportTypes = getDS('TransportTypes')
AccessProtocols = getDS('AccessProtocols')
AccessControlList = getDS('AccessControlList')
Options = getDS('Options')
IP = getDS('IP')
GlusterBricks = getDS('GlusterBricks')
GlusterBrick = getDS('GlusterBrick')


def _prepareVolume(**kwargs):
    '''
    Prepare volume object from provided dictionary
    '''

    vol = GlusterVolume()

    name = kwargs.pop('name')
    if name:
        vol.set_name(name)

    description = kwargs.pop('description', None)
    if description:
        vol.set_description(description)

    volume_type = kwargs.pop('volume_type', None)
    if volume_type:
        vol.set_volume_type(volume_type)

    transport_types = kwargs.pop('transport_types', None)
    if transport_types:
        volTT = TransportTypes()
        for tt in split(transport_types):
            volTT.add_transport_type(tt)
        vol.set_transport_types(volTT)

    replica_count = kwargs.pop('replica_count', None)
    if replica_count:
        vol.set_replica_count(replica_count)

    stripe_count = kwargs.pop('stripe_count', None)
    if stripe_count:
        vol.set_stripe_count(stripe_count)
        
    access_protocols = kwargs.pop('access_protocols', None)
    if access_protocols:
        volAP = AccessProtocols()
        for ap in split(access_protocols):
            volAP.add_access_protocol(ap)
        vol.set_access_protocols(volAP)

    access_control_list = kwargs.pop('access_control_list', None)
    if access_control_list:
        volACL = AccessControlList()
        for acl in access_control_list:
            netmask = acl.get('netmask', '')
            gateway = acl.get('gateway', '')
            address = acl.get('address', '')
            volACL.add_ip(IP(address=address, netmask=netmask, gateway=gateway))
        vol.set_access_control_list(volACL)

    options = kwargs.pop('options', None)
    if options:
        opts = Options()
        for opt in options:
            type = opt.get('type', '')
            name = opt.get('name', '')
            value = opt.get('value', '')
            opts.add_option(Option(name=name, value=value, type=type))
        vol.set_options(opts)

    bricks = kwargs.pop('bricks', None)
    if bricks:
        volBricks = GlusterBricks()
        for brick in bricks:
            server_id = brick.get('server_id', '')
            brick_dir = brick.get('brick_dir', '')
            volBricks.add_brick(GlusterBrick(server_id=server_id, brick_dir=brick_dir))
        vol.set_bricks(volBricks)

    return vol


def addClusterVolume(positive, cluster, **kwargs):
    '''
    Description: Add new cluster volume
    Parameters:
        * cluster - cluster name
        * name - volume name
        * description - volume description
        * volume_type - volume type
        * transport_types - comma separated transport types
        * replica_count - replica count
        * stripe_count - stripe_count
        * access_protocols - comma separated access protocols
        * access_control_list - comma separated dictinaries of access controls ips,
            example: {'netmask': ..., 'gateway': ...., 'address': ...}, {...}
        * options - comma separated dictinaries of options,
            example: {'type': ..., 'name': ...., 'value': ...}, {...}
        * bricks - comma separated dictinaries of bricks,
            example: {'server_id': ..., 'brick_dir': ....}, {...}
    Return: status (True if data center was added properly, False otherwise)
    '''

    clObj = clUtil.find(cluster)
    clVolumes = util.getElemFromLink(clObj, link_name='glustervolumes', get_href=True)
    vol = _prepareVolume(**kwargs)
    vol, status = util.create(vol, positive, collection=clVolumes)
  
    return status


def removeClusterVolume(positive, cluster, volume):
    '''
    Description: Remove cluster volume
    Author: edolinin
    Parameters:
       * cluster - name of a the cluster
       * volume - volume name
    Return: status (True if volume was removed properly, False otherwise)
     '''

    clObj = clUtil.find(cluster)
    clVolumes = util.getElemFromLink(clObj, get_href=False)
    vol  = util.find(volume, absLink=False, collection=clVolumes)
    return util.delete(vol, positive)


def searchForClusterVolumes(positive, cluster, query_key, query_val, key_name):
    '''
    Description: search for a cluster volume by desired property
    Parameters:
       * cluster - name of desired cluster
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in volume object equivalent to query_key
    Return: status (True if expected number of volumes equal to
                    found by search, False otherwise)
    '''

    expected_count = 0
    clObj = clUtil.find(cluster)
    clVolumes = util.getElemFromLink(clObj, get_href=True)

    for clVol in clVolumes:
        volProperty = getattr(clVol, key_name)
        if re.match(r'(.*)\*$',query_val):
            if re.match(r'^' + query_val, volProperty):
                expected_count = expected_count + 1
        else:
            if volProperty == query_val:
                expected_count = expected_count + 1

    contsraint = "{0}={1}".format(query_key, query_val)
    query_vols = util.query(contsraint, href=clVolumes)
    status = compareCollectionSize(query_vols, expected_count, util.logger)

    return status == positive


def removeClusterVolumesAsynch(positive, cluster, volume, queue):
    '''
    Description: Remove cluster volume, using threading for removing of multiple objects
    Parameters:
       * cluster -  name of the cluster
       * volumes - name of volume that should be removed
       * queue - queue of threads
    Return: status (True if volume was removed properly, False otherwise)
    '''
    
    vol = None
    try:
        clObj = clUtil.find(cluster)
        clVolumes = util.getElemFromLink(clObj, get_href=True)
        vol  = util.find(volume, collection=clVolumes)
    except EntityNotFound:
        queue.put(False)
        return False

    status = util.delete(vol, positive)
    time.sleep(30)

    queue.put(status)
    

def removeClusterVolumes(positive, cluster, volumes):
    '''
     Description: Remove several cluster volumes, using threading
     Parameters:
        * cluster -  name of the cluster
        * volumes - name of volumes that should be removed separated by comma
     Return: status (True if all volumes were removed properly, False otherwise)
     '''

    volumeList = split(volumes)
    status = True

    threadQueue = Queue.Queue()
    for vol in volumeList:
        thread = threading.Thread(target=removeClusterVolumesAsynch,
            name="Remove Volume " + vol, args=(positive, cluster, vol, threadQueue))
        thread.start()
        thread.join()

    while not threadQueue.empty():
        volStatus = threadQueue.get()
        if not volStatus:
            status = False

    return status



