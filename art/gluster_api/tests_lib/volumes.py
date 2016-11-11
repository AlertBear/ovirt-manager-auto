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

import re
import time
import threading
import Queue

from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api, split
from art.core_api.validator import compareCollectionSize
from art.core_api.apis_exceptions import EntityNotFound, TestCaseError
from utilities.machine import Machine
from art.rhevm_api.tests_lib.low_level.hosts import deactivate_host, removeHost

ELEMENT = 'gluster_volume'
COLLECTION = 'glustervolumes'
util = get_api(ELEMENT, COLLECTION)
clUtil = get_api('cluster', 'clusters')
hostUtil = get_api('host', 'hosts')
brickUtil = get_api('brick', 'bricks')
bricksUtil = get_api('bricks', 'bricks')

GlusterVolume = getDS('GlusterVolume')
TransportTypes = getDS('TransportTypes')
AccessProtocols = getDS('AccessProtocols')
AccessControlList = getDS('AccessControlList')
Options = getDS('Options')
IP = getDS('IP')
GlusterBricks = getDS('GlusterBricks')
GlusterBrick = getDS('GlusterBrick')
Option = getDS('Option')

VOL_ACTION_TIMEOUT = 180


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
            volACL.add_ip(acl)
        vol.set_access_control_list(volACL)

    options = kwargs.pop('options', None)
    if options:
        opts = Options()
        for opt in options:
            type = opt.get('type', '')
            name = opt.get('name', '')
            value = opt.get('value', '')
            opts.add_option(Option(name=name, value=value, type_=type))
        vol.set_options(opts)

    bricks = kwargs.pop('bricks', None)
    if bricks:
        volBricks = _prepareBricks(bricks)
        vol.set_bricks(volBricks)

    return vol


def _prepareBricks(bricks):

    volBricks = GlusterBricks()
    for brick in bricks:
        host = brick.get('server', '')
        server_id = hostUtil.find(host).id
        brick_dir = brick.get('brick_dir', '')
        volBricks.add_brick(GlusterBrick(server_id=server_id,
                                         brick_dir=brick_dir))

    return volBricks


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
        * access_control_list - list of dictinaries of access controls ips,
            example: ['192.168.*.*','10.4.10.*']
        * options - list of dictinaries of options,
            example: [{'type': ..., 'name': ...., 'value': ...}, {...}]
        * bricks - list of dictinaries of bricks,
            example: [{'server': ..., 'brick_dir': ....}, {...}]
     Parameters string example:
    <params_pattern>
        cluster='',name='',volume_type='',transport_types='',replica_count='',
        stripe_count='',access_protocols'',
        access_control_list=[{'netmask':'','gateway':'','address':''},],
        bricks=[{'server':'','brick_dir':''},],
        options=[{'name':'','type':'','value':''},]
    </params_pattern>

    Return: status (True if data center was added properly, False otherwise)
    '''

    clObj = clUtil.find(cluster)
    clVolumes = util.getElemFromLink(clObj, link_name='glustervolumes',
                                     get_href=True)
    vol = _prepareVolume(**kwargs)
    vol, status = util.create(vol, positive, collection=clVolumes)

    return status


def getClusterVolume(cluster, volume):

    clObj = clUtil.find(cluster)
    clVolumes = util.getElemFromLink(clObj, get_href=False)
    return util.find(volume, absLink=False, collection=clVolumes)


def removeClusterVolume(positive, cluster, volume):
    '''
    Description: Remove cluster volume
    Author: edolinin
    Parameters:
       * cluster - name of a the cluster
       * volume - volume name
    Return: status (True if volume was removed properly, False otherwise)
     '''

    vol = getClusterVolume(cluster, volume)
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
    clVolumes = getClusterVolumes(cluster)

    for clVol in clVolumes:
        volProperty = getattr(clVol, key_name)
        if re.match(r'(.*)\*$', query_val):
            if re.match(r'^' + query_val, volProperty):
                expected_count = expected_count + 1
        else:
            if volProperty == query_val:
                expected_count = expected_count + 1

    clVolumes = getClusterVolumes(cluster, True)
    contsraint = "{0}={1}".format(query_key, query_val)
    query_vols = util.query(contsraint, href=clVolumes + '?search={query}')
    status = compareCollectionSize(query_vols, expected_count, util.logger)

    return status == positive


def removeClusterVolumesAsynch(positive, cluster, volume, queue):
    '''
    Description: Remove cluster volume, using threading
                 for removing of multiple objects
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
        vol = util.find(volume, collection=clVolumes)
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
     Return status:
        True if all volumes were removed properly, False otherwise
     '''

    volumeList = split(volumes)
    status = True

    threadQueue = Queue.Queue()
    for vol in volumeList:
        thread = threading.Thread(target=removeClusterVolumesAsynch,
                                  name="Remove Volume %s" % vol,
                                  args=(positive, cluster, vol, threadQueue))
        thread.start()
        thread.join()

    while not threadQueue.empty():
        volStatus = threadQueue.get()
        if not volStatus:
            status = False

    return status


def getClusterVolumes(cluster, get_href=False):

    clObj = clUtil.find(cluster)
    return util.getElemFromLink(clObj, get_href=get_href)


def runVolAction(positive, cluster, volume, action, wait_for_status, **opts):

    if not positive:
        wait_for_status = None

    vol = getClusterVolume(cluster, volume)
    if not util.syncAction(vol, action, positive, **opts):
        return False

    if wait_for_status is None:
        return True

    query = "name={0} and status={1}".format(volume, wait_for_status.lower())
    clVols = '%s?search={query}' % getClusterVolumes(cluster, True)
    return util.waitForQuery(
        query, href=clVols, timeout=VOL_ACTION_TIMEOUT, sleep=10,
    )


def startVolume(positive, cluster, volume):
    '''
    Description: start volume
    Parameters:
       * cluster - name of cluster
       * volume - name of volume

    Return: status (True if volume was started properly, False otherwise)
    '''

    return runVolAction(positive, cluster, volume, 'start', 'up')


def stopVolume(positive, cluster, volume):
    '''
    Description: stop volume
    Parameters:
       * cluster - name of cluster
       * volume - name of volume

    Return: status (True if volume was started properly, False otherwise)
    '''

    return runVolAction(positive, cluster, volume, 'stop', 'down')


def rebalanceVolume(positive, cluster, volume):
    '''
    Description: rebalance volume
    Parameters:
       * cluster - name of cluster
       * volume - name of volume

    Return: status (True if volume was started properly, False otherwise)
    '''

    return runVolAction(positive, cluster, volume, 'rebalance', None)


def resetAllVolumeOptions(positive, cluster, volume):
    '''
    Description: start volume
    Parameters:
       * cluster - name of cluster
       * volume - name of volume

    Return: status (True if volume was started properly, False otherwise)
    '''

    return runVolAction(positive, cluster, volume, 'resetAllOptions', None)


def setVolumeOption(positive, cluster, volume, opt_name, opt_value):
    '''
    Description: start volume
    Parameters:
       * cluster - name of cluster
       * volume - name of volume
       * opt_name - option name
       * opt_value - option value

    Return: status (True if volume was started properly, False otherwise)
    '''

    option = Option(name=opt_name, value=opt_value)
    return runVolAction(
        positive, cluster, volume, 'setOption', None, option=option,
    )


def resetVolumeOption(positive, cluster, volume, opt_name):
    '''
    Description: start volume
    Parameters:
       * cluster - name of cluster
       * volume - name of volume
       * opt_name - option name

    Return: status (True if volume was started properly, False otherwise)
    '''

    option = Option(name=opt_name)
    return runVolAction(
        positive, cluster, volume, 'resetOption', None, option=option,
    )


def addBrickToVolume(positive, cluster, volume, bricks):
    '''
    Description: Add brick to volume
    Parameters:
        * cluster - cluster name
        * volume - volume name
        * bricks - list of dictinaries of bricks,
            example: [{'server': ..., 'brick_dir': ....}, {...}]
    Parameters string example:
    <params_pattern>
        cluster='',volume='',bricks=[{'server':'','brick_dir':''},]
    </params_pattern>

    Return: status (True if data center was added properly, False otherwise)
    '''

    vol = getClusterVolume(cluster, volume)
    volBricksColl = util.getElemFromLink(vol, link_name='bricks',
                                         get_href=True)
    volBricks = _prepareBricks(bricks)

    volBricks, status = bricksUtil.create(
        volBricks, positive,
        collection=volBricksColl,
        coll_elm_name='brick',
        async=True
    )
    return status


def _getVolumeBricks(cluster, volume, bricks):
    '''
    Description: get brick
    Author: imeerovi
    Parameters:
        * cluster - cluster name
        * volume - volume name
        * bricks - list of dictionaries of bricks,
            example: [{'server': ..., 'brick_dir': ....}, {...}]
    Parameters string example:
    <params_pattern>
        cluster='',volume='',bricks=[{'server':'','brick_dir':''},]
    </params_pattern>

    Return: list with bricks for volume.
            EntityNotFound exception will be raised if
            no matching bricks were found
    '''
    bricksObjs = []

    vol = getClusterVolume(cluster, volume)
    volBricks = util.getElemFromLink(vol, link_name='bricks', attr='brick',
                                     get_href=False)

    for brick in bricks:
        # in case of EntityNotFound exception from util/hostUtil.find
        # exception will be not caught and passed to higher levels
        hostObj = hostUtil.find(brick['server'])
        brick_tmp = util.find(val=brick['brick_dir'],
                        attribute='brick_dir', absLink=False,
                        collection=volBricks, server_id=hostObj.id)
        bricksObjs.append(brick_tmp)

    if not bricksObjs:
            raise EntityNotFound("Volume %s doesn't contains these bricks: %s"\
                                 % (volume, bricks))
    return bricksObjs


def removeBrickFromVolume(positive, cluster, volume, bricks, force=True):
    '''
    Description: remove bricks from volume
    Author: imeerovi
    Parameters:
        * cluster - cluster name
        * volume - volume name
        * bricks - list of dictionaries of bricks,
            example: [{'server': ..., 'brick_dir': ....}, {...}]
        * force - force removal even if removal of previous brick failed
    Parameters string example:
    <params_pattern>
        cluster='',volume='',bricks=[{'server':'','brick_dir':''},]
    </params_pattern>

    Return: status (True if all bricks were removed properly, False otherwise)
    '''
    bricks = _getVolumeBricks(cluster, volume, bricks)
    vol = getClusterVolume(cluster, volume)

    index = None
    for i, link in enumerate(vol.link):
        if link.rel == "bricks":
            index = i
            break
    else:
        return False

    if vol.volume_type in ('replicate', 'distributed_replicate',
                           'distributed_stripe'):
        delBricks = GlusterBricks()
        delBricks.set_replica_count((vol.replica_count -1) \
                                    if vol.volume_type == 'replicate' \
                                    else vol.replica_count)
        delBricks.set_brick(bricks)
        return util.delete(vol.link[index], positive, body=delBricks,
                         element_name='bricks')
    else:
        for brick in bricks:
            status = util.delete(brick, positive)
            if not force and not status:
                return False
        return status


def checkVolumeParam(positive, cluster, volume, key, value):
    '''
    Description: Checks volume parameter
    Author: imeerovi
    Parameters:
    * cluster - cluster name
    * volume - volume name
    * key - the name of option
    * value - the value of options
    Returns: True if actual value is equal to value of key
             False in case that values are not equal
    '''
    vol = getClusterVolume(cluster, volume)
    ERROR = "%s of %s has wrong value, expected: %s, actual: %s."
    status = True

    try:
        options = vol.options.get_option()
        actualValue = None
        for option in options:
            if option.name == key:
                actualValue = option.value
        if value != actualValue:
            status = False
            util.logger.error(ERROR % ("Parameter",
                      vol.get_name(), value, actualValue))

    except AttributeError as e:
        util.logger.error("checkVolumeParams: %s", str(e))
        return not positive
    return status == positive


def removeGlusterHost(positive, host):
    '''
    Description: removes host
                 (including putting it into maintenance state before)
    Parameters:
    * host - host name
    Returns: True (success) / False (failure)
    '''
    hostObj = hostUtil.find(host)
    if not deactivate_host(positive, host):
        util.logger.error("Host deactivation failed: %s." % hostObj.name)
        return False
    if not removeHost(positive, host):
        util.logger.error("Host removal failed: %s." % hostObj.name)
        return False

    return True


def glusterVolumeMountDDTest(
    positive, volumeIP, volumeExportDir, host, mountPoint, volumeType,
    user='root', password='qum5net', osType='linux',
    ddParams='if=/dev/zero bs=1024 count=1024', mountOpts='',
):
    '''
    Description: mount test for gluster volume on remote host
    Author: imeerovi
    Parameters:
    * volumeIP - volume virtual ip
                 (for now ip of brick host)
    * volumeExportDir - volume export directory
                 (for now directory of brick)
    * host - host ip/name
    * mountPoint - mount point on host
    * volumeType (nfs/glusterfs)
    * user - username [root]
    * password - password [qum5net]
    * osType - only 'linux' supported
    Returns: True if volume mounted OK
            False in other cases
    '''
    fileName = 'test_file'

    machine = Machine(host, user, password).util(osType)
    if machine is None:
        return False

    mountCmd = [
        'mount', '-t', volumeType, '%s:%s' % (volumeIP, volumeExportDir),
        mountPoint,
    ]
    mountCmd.extend(mountOpts.split())

    mkdirCmd = ['mkdir', '-p', mountPoint]

    ddCmd = ['dd', 'of=%s/%s' % (mountPoint, fileName)]
    ddCmd.extend(ddParams.split())

    try:
        for cmd in [mkdirCmd, mountCmd, ddCmd]:
            rc, out = machine.runCmd(cmd)
            if not rc:
                util.logger.debug(out)
                raise TestCaseError(
                    "Command:\n%s\n failed to run on host: %s" % (
                        ' '.join(cmd), host,
                    )
                )
            else:
                util.logger.debug('Command: \'%s\' successfully done on'
                                  ' host: %s' % (' '.join(cmd), host))
    finally:
        rc = machine.removeFile("%s/%s" % (mountPoint, fileName))
        if not rc:
            raise TestCaseError(
                "Failed to remove %s/%s on host %s" % (
                    mountPoint, fileName, host,
                )
            )

        umountCmd = ['umount', mountPoint]
        rmdirCmd = ['/bin/rm', '-rf', mountPoint]

        for cmd in [umountCmd, rmdirCmd]:
            rc, out = machine.runCmd(cmd)
            if not rc:
                util.logger.debug(out)
                util.logger.debug(
                    "Command:\n%s\n failed to run on host: %s",
                    ' '.join(cmd), host,
                )

    return rc == positive
