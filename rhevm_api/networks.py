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

from utils.data_structures import Network, IP
from utils.test_utils import get_api
from utils.apis_exceptions import EntityNotFound

ELEMENT = 'network'
COLLECTION = 'networks'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
clUtil = get_api('cluster', 'clusters')


def addNetwork(positive, **kwargs):
    '''
    Description: add network to a data center
    Author: edolinin
    Parameters:
       * name - name of a new network
       * data_center - data center name where a new network should be added
       * address - network ip address
       * netmask - network ip netmask
       * gateway - network ip gateway
       * stp - support stp true/false (note: true/false as a strings) 
       * vlan_id - network vlan id
       * display - set as display or not (true/false)
    Return: status (True if network was added properly, False otherwise)
    '''

    netDC = dcUtil.find(kwargs.pop('data_center'))
    
    address = None
    netmask = None
    gateway = None

    if 'address' in kwargs:
        address = kwargs.pop('address')

    if 'netmask' in kwargs:
        netmask = kwargs.pop('netmask')

    if 'gateway' in kwargs:
        gateway = kwargs.pop('gateway')
  
    ip = None
    if address or netmask or gateway:
        ip = IP(address=address, netmask=netmask, gateway=gateway)

    Vlan = None
    if 'vlan_id' in kwargs:
        Vlan = Vlan(id=kwargs.pop('vlan_id'))
       
    net = Network(data_center = netDC, ip=ip, vlan=Vlan, **kwargs)
    net, status = util.create(net, positive)

    return status


def findNetwork(network, data_center=None):
    found_net = False
    # FIXME: data_center is needed in some cases untill BZ#741111 will be solved
    if data_center:
        dc_obj = dcUtil.find(data_center)
        # NOTE: data_center isn't mandatory in order not to break
        # other related functions
        nets = util.get(absLink=False)
        for net in nets:
            if net.get_data_center().get_id() == dc_obj.get_id() and \
            net.get_name().lower() == network.lower():
                found_net = True
                break
    else:
        return True

    return found_net


def updateNetwork(positive, network, **kwargs):
    '''
    Description: update existing network
    Author: edolinin
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
       * display - new network display value (if relevant)
    Return: status (True if network was updated properly, False otherwise)
    '''
    if not findNetwork(network, kwargs.get('data_center')):
        # found_net is a flag that suppose to be true if founded network
        # else exist the function with EntityNotFound
        raise EntityNotFound

    net = util.find(network)
    netUpd = Network()
    
    if 'name' in kwargs:
        netUpd.set_name(kwargs.get('name'))

    if 'description' in kwargs:
        netUpd.set_description(kwargs.get('description'))

    if 'stp' in kwargs:
        netUpd.set_stp(kwargs.get('stp'))

    if 'display' in kwargs:
        netUpd.set_display(kwargs.get('display'))

    if 'data_center' in kwargs:
        netUpd.set_data_center(dcUtil.find(data_center))

    address = kwargs.get('address')
    netmask = kwargs.get('netmask')
    gateway = kwargs.get('gateway')

    if address or netmask or gateway:
        ip = IP(address=address, netmask=netmask, gateway=gateway)
        netUpd.set_ip(ip)
     
    vlan = kwargs.get('vlan_id')
    if vlan:
        netUpd.set_vlan(id=vlan_id)
       
    netUpd, status = util.update(net, netUpd, positive)
    
    return status


def removeNetwork(positive, network, data_center=None,):
    '''
    Description: remove existing network
    Author: edolinin
    Parameters:
       * network - name of a network that should be removed
       * data_center - In case more then one network with the same name exists.
    Return: status (True if network was removed properly, False otherwise)
    '''
    if not findNetwork(network, data_center):
        # found_net is a flag that suppose to be true if founded network
        # else exist the function with EntityNotFound
        raise EntityNotFound

    net = util.find(network)

    return util.delete(net, positive)


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


def addNetworkToCluster(positive, network, cluster):
    '''
    Description: attach network to cluster
    Author: edolinin, atal
    Parameters:
       * network - name of a network that should be attached
       * cluster - name of a cluster to attach to
    Return: status (True if network was attached properly, False otherwise)
    '''
    # FIXME: this function is a workaround for BZ#741111
    network_objs = util.get(absLink=False)
    cluster_obj = clUtil.find(cluster)
    cluster_cd_id = cluster_obj.get_data_center().get_id()
    clNetworks = util.getElemFromLink(cluster_obj, 'networks',
                                attr='network', get_href=True)
   
    if network_objs is None:
        raise EntityNotFound('Found Empty networks element')

    for network_obj in network_objs:
        if cluster_cd_id == network_obj.get_data_center().get_id() and \
        network == network_obj.get_name():
            net, status = util.create(network_obj, positive, collection=clNetworks)
            return status
    return False


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


def removeNetworkFromCluster(positive, network, cluster):
    '''
    Description: detach network from cluster
    Author: edolinin, atal
    Parameters:
       * network - name of a network that should be detached
       * cluster - name of a cluster to detach from
    Return: status (True if network was detached properly, False otherwise)
    '''
    cluster_obj = clUtil.find(cluster)
    net_obj = util.getElemFromElemColl(cluster_obj, 'networks', 'network', network)
    if net_obj:
        return util.delete(net_obj, positive)
    else:
        util.logger.error("Network {0} is not found at cluster {1}".format(network,
        cluster))
        return False


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
        clusterObj = util.find(cluster)
        netObj = util.getElemFromElemColl(clusterObj, 'networks', 'network', network)
    except EntityNotFound:
        return False, {'value': None}

    # validate cluster network related to the given datacenter
    if datacenter:
        try:
            dcObj = dcUtil.find(datacenter)
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


def validateNetwork(positive, cluster, network, tag, val):
    status, output = getNetworkConfig(positive, cluster, network, tag=tag)
    if not status:
        return False
    if str(output['value']).lower() != str(val).lower():
        return False
    return True


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
        if not addNetwork(positive, prefix + str(vlan), data_center, vlan_id=vlan):
            return False, {'nets': None}
    return True, {'nets': nics}
