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

from core_api.apis_utils import data_st
from rhevm_api.utils.test_utils import get_api
from core_api.apis_exceptions import EntityNotFound

ELEMENT = 'network'
COLLECTION = 'networks'
NET_API = get_api(ELEMENT, COLLECTION)
DC_API = get_api('data_center', 'datacenters')
CL_API = get_api('cluster', 'clusters')

logger = logging.getLogger(__package__ + __name__)


def _prepareNetworkObject(**kwargs):
    '''
    preparing logical network object
    Author: edolinin, atal
    return: logical network data structure object
    '''
    net = data_st.Network()

    if 'name' in kwargs:
        net.set_name(kwargs.get('name'))

    if 'description' in kwargs:
        net.set_description(kwargs.get('description'))

    if 'stp' in kwargs:
        net.set_stp(kwargs.get('stp'))

    if 'data_center' in kwargs:
        dc = kwargs.get('data_center')
        net.set_data_center(DC_API.find(dc))

    address = kwargs.get('address')
    netmask = kwargs.get('netmask')
    gateway = kwargs.get('gateway')
    if (address or netmask or gateway) is not None:
        ip = {}
        if address is not None:
            ip['address'] = address
        if netmask is not None:
            ip['netmask'] = netmask
        if gateway is not None:
            ip['gateway'] = gateway
        net.set_ip(data_st.IP(**ip))

    if 'vlan_id' in kwargs:
        net.set_vlan(data_st.VLAN(id=kwargs.get('vlan_id')))

    if 'usages' in kwargs:
        net.set_usages(data_st.Usages(usage=kwargs.get('usages').split(',')))

    if 'mtu' in kwargs:
        net.set_mtu(kwargs.get('mtu'))

    return net


def addNetwork(positive, **kwargs):
    '''
    Description: add network to a data center
    Author: edolinin
    Parameters:
       * name - name of a new network
       * description - new network description (if relevant)
       * data_center - data center name where a new network should be added
       * address - network ip address
       * netmask - network ip netmask
       * gateway - network ip gateway
       * stp - support stp true/false (note: true/false as a strings)
       * vlan_id - network vlan id
       * usages - a string contain list of usages separated by commas 'VM,DIPLAY'.
       * mtu - and integer to overrule mtu on the related host nic..
    Return: status (True if network was added properly, False otherwise)
    '''

    net_obj = _prepareNetworkObject(**kwargs)
    res, status = NET_API.create(net_obj, positive)

    return status


def updateNetwork(positive, network, **kwargs):
    '''
    Description: update existing network
    Author: edolinin, atal
    Parameters:
       * network - name of a network that should be updated
       * name - new network name (if relevant)
       * data_center - In case more then one network with the same name exists.
       * address - network ip address
       * netmask - network ip netmask
       * gateway - network ip gateway
       * description - new network description (if relevant)
       * stp - new network support stp (if relevant). (note: true/false as a strings)
       * vlan_id - new network vlan id (if relevant)
       * usages - a string contain list of usages separated by commas 'VM,DIPLAY'.
                    should contain all usages every update.
                    a missing usage will be deleted!
       * mtu - and integer to overrule mtu on the related host nic..
    Return: status (True if network was updated properly, False otherwise)
    '''

    net = findNetwork(network, kwargs.get('data_center'))
    net_update = _prepareNetworkObject(**kwargs)
    res, status = NET_API.update(net, net_update, positive)

    return status


def removeNetwork(positive, network, data_center=None):
    '''
    Description: remove existing network
    Author: edolinin, atal
    Parameters:
       * network - name of a network that should be removed
       * data_center - In case more then one network with the same name exists.
    Return: status (True if network was removed properly, False otherwise)
    '''

    net = findNetwork(network, data_center)
    return NET_API.delete(net, positive)


def findNetwork(network, data_center=None):
    '''
    Description: Find desired network among other networks with same name
    findNetwork is needed due to BZ#741111.
    Author: atal
    Parameters:
        * network - network name
        * data_center - DC which given network is a member of.
        note: DC isn't mandatory in order not to break API
    return: network object in case of succeed, raise EntityNotFound in case
    of Failure
    '''

    if data_center is not None:
        dc_obj = DC_API.find(data_center)
        nets = NET_API.get(absLink=False)
        for net in nets:
            if net.get_data_center().get_id() == dc_obj.get_id() and \
            net.get_name().lower() == network.lower():
                return net
        raise EntityNotFound('%s network does not exists!' % network)
    else:
        return NET_API.find(network)


def removeMultiNetworks(positive, networks):
    '''
    Remove Multiple networks from cluster
    Author: atal
    Parameters:
        * networks- a list of networks
    return True/False
    '''
    for net in networks:
        if not removeNetwork(positive, net):
            return False
    return True


def _prepareClusterNetworkObj(**kwargs):
    '''
    preparing cluster network object
    Author: edolinin, atal
    return: logical network data structure object for cluster
    '''
    net = kwargs.get('net', data_st.Network())

    if 'usages' in kwargs:
        net.set_usages(data_st.Usages(usage=kwargs.get('usages').split(',')))

    if 'required' in kwargs:
        net.set_required(kwargs.get('required'))

    if 'display' in kwargs:
        net.set_display(kwargs.get('display'))

    return net


def getClusterNetwork(cluster, network):

    clusterObj = CL_API.find(cluster)
    return CL_API.getElemFromElemColl(clusterObj, network, 'networks', 'network')


def getClusterNetworks(cluster):

    clusterObj = CL_API.find(cluster)
    return CL_API.getElemFromLink(clusterObj, link_name='networks', attr='network', get_href=True)


def findNetworkByCluster(network, cluster):
    '''
    Design to compare cluster DC with network DC in order to
    workaround BZ#741111
    Author: atal
    Parameters:
        * network - network name
        * cluster - cluster name
    return: network object in case of success, raise EntityNotFound in case
    of Failure
    '''
    nets = NET_API.get(absLink=False)
    cluster_obj = CL_API.find(cluster)
    cluster_dc_id = cluster_obj.get_data_center().get_id()

    for net in nets:
        if cluster_dc_id == net.get_data_center().get_id() and \
        network == net.get_name():
            return net
    raise EntityNotFound('%s network does not exists!' % network)


def addNetworkToCluster(positive, network, cluster, **kwargs):
    '''
    Description: attach network to cluster
    Author: atal
    Parameters:
       * network - name of a network that should be attached
       * cluster - name of a cluster to attach to
       * required - boolean, decide if network should be required by cluster..
       * usages - a string contain list of usages separated by comma
       'VM,DIPLAY'. should contain all usages every update.
       a missing usage will be deleted!
       * display - deprecated. boolean, a spice display network.
    Return: status (True if network was attached properly, False otherwise)
    '''

    kwargs.update(net=findNetworkByCluster(network, cluster))
    net = _prepareClusterNetworkObj(**kwargs)
    cluster_nets = getClusterNetworks(cluster)
    res, status = NET_API.create(net, positive,
                                     collection=cluster_nets)

    return status


def updateClusterNetwork(positive, cluster, network, **kwargs):
    '''
    Description: update network to cluster
    Author: atal
    Parameters:
       * network - name of a network that should be attached
       * cluster - name of a cluster to attach to
       * required - boolean, decide if network should be required by cluster..
       * usages - a string contain list of usages separated by
       commas 'VM,DIPLAY'. should contain all usages every update.
       a missing usage will be deleted!
       * display - deprecated. boolean, a spice display network.
    Return: status (True if network was attached properly, False otherwise)
    '''

    net = getClusterNetwork(cluster, network)
    net_update = _prepareClusterNetworkObj(**kwargs)
    res, status = NET_API.update(net, net_update, positive)

    return status


def removeNetworkFromCluster(positive, network, cluster):
    '''
    Description: detach network from cluster
    Author: edolinin, atal
    Parameters:
       * network - name of a network that should be detached
       * cluster - name of a cluster to detach from
    Return: status (True if network was detached properly, False otherwise)
    '''

    net_obj = getClusterNetwork(cluster, network)

    return NET_API.delete(net_obj, positive)


def addMultiNetworksToCluster(positive, networks, cluster):
    '''
    Adding multiple networks to cluster
    Author: atal
    Parameters:
        * networks - list of networks name
        * cluster - cluster name
    return True/False
    '''
    for net in networks:
        if not addNetworkToCluster(positive, net, cluster):
            return False
    return True


def removeMultiNetworksFromCluster(positive, networks, cluster):
    '''
    Remove multiple networks to cluster
    Author: atal
    Parameters:
        * networks - list of networks name
        * cluster - cluster name
    return True/False
    '''
    for net in networks:
        if not removeNetworkFromCluster(positive, net, cluster):
            return False
    return True


# FIXME: need to check if this function is being used else just remove.
def getNetworkConfig(positive, cluster, network, datacenter=None, tag=None):
    '''
     Validate Datacenter/Cluster network configurations/existence.
     This function tests the network configured parameters. we look for
     networks link under cluster even though we check the DC network
     configurations only because cluster networks related to main networks href.
     Author: atal
     Parameters:
        * cluster - cluster name
        * network - network name
        * datacenter - data center name. in order to check if the given
                       network exists in the DC.
        * tag - the tag we are looking to validate
     return: True and value of the given filed, otherwise False and None
    '''
    try:
        netObj = getClusterNetwork(cluster, network)
    except EntityNotFound:
        return False, {'value': None}

    # validate cluster network related to the given datacenter
    if datacenter:
        try:
            dcObj = DC_API.find(datacenter)
        except EntityNotFound:
            return False, {'value': None}

        # return False means that given datacenter doesn't contain the given network
        if dcObj.get_id() != netObj.get_data_center().get_id():
            return False, {'value': None}

    if tag:
        if hasattr(netObj, tag):
            attrValue = None
            if tag == 'status':
                attrValue = getattr(netObj.get_status(), 'state')
            else:
                attrValue = getattr(netObj, tag)
            return True, {'value': attrValue}

    # in canse we only like to check if the network exists or not.
    if netObj:
        return True, {'value': netObj.get_name()}

    return False, tag


# FIXME: method is using only for checking status. need to change to a more
# simple method
def validateNetwork(positive, cluster, network, tag, val):
    status, output = getNetworkConfig(positive, cluster, network, tag=tag)
    if not status:
        return False
    if str(output['value']).lower() != str(val).lower():
        return False
    return True


# FIXME: change to use conf file for vlan networks name
def addNetworksVlans(positive, prefix, vlans, data_center):
    '''
    Adding multiple networks with vlan according to the given prefix and range
    Author: atal
    Parameters:
        * prefix - the prefix for the network name
        * vlans - a list vlan ids
        * date_center - the DataCenter name
    return True with new nics name list or False with empty list
    '''
    nics = []
    for vlan in vlans.split(','):
        nics.append(prefix + str(vlan))
        net_name = prefix + str(vlan)
        if not addNetwork(positive, name=net_name, data_center=data_center, vlan_id=vlan):
            return False, {'nets': None}
    return True, {'nets': nics}
