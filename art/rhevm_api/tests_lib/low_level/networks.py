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

from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api import is_action
from utilities.machine import Machine, LINUX
import logging

import re

NET_API = get_api("network", "networks")
CL_API = get_api("cluster", "clusters")
DC_API = get_api("data_center", "datacenters")
VNIC_PROFILE_API = get_api('vnic_profile', 'vnicprofiles')
MGMT_NETWORK = "rhevm"

logger = logging.getLogger('networks')


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

    ip = {}
    for k in ['address', 'netmask', 'gateway']:
        if k in kwargs:
            ip[k] = kwargs.get(k)
    ip and net.set_ip(data_st.IP(**ip))

    if 'vlan_id' in kwargs:
        net.set_vlan(data_st.VLAN(id=kwargs.get('vlan_id')))

    if 'usages' in kwargs:
        usages = kwargs.get('usages')
        if usages:
            net.set_usages(data_st.Usages(usage=usages.split(',')))
        else:
            net.set_usages(data_st.Usages())

    if 'mtu' in kwargs:
        net.set_mtu(kwargs.get('mtu'))

    return net


@is_action()
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
       * usages - a string contain list of comma-separated usages 'VM,DIPLAY'.
       * mtu - and integer to overrule mtu on the related host nic..
    Return: status (True if network was added properly, False otherwise)
    '''

    net_obj = _prepareNetworkObject(**kwargs)
    res, status = NET_API.create(net_obj, positive)

    return status


@is_action()
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
       * stp - new network support stp (if relevant). (true/false string)
       * vlan_id - new network vlan id (if relevant)
       * usages - a string contain list of comma-separated usages 'VM,DIPLAY'.
                    should contain all usages every update.
                    a missing usage will be deleted!
       * mtu - and integer to overrule mtu on the related host nic..
    Return: status (True if network was updated properly, False otherwise)
    '''

    net = findNetwork(network, kwargs.get('data_center'))
    net_update = _prepareNetworkObject(**kwargs)
    res, status = NET_API.update(net, net_update, positive)

    return status


@is_action()
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


def findNetwork(network, data_center=None, cluster=None):
    '''
    Description: Find desired network using cluster or data center as an option
                 to narrow down the search when multiple networks with the same
                 name exist (needed due to BZ#741111). The network is retrieved
                 at the data center level unless only the network name is
                 passed, in which case a search is done among all the networks
                 in the environment.
    **Author**: atal, tgeft
    **Parameters**:
        *  *name* - Name of the network to find.
        *  *cluster* - Name of the cluster in which the network is located.
        *  *data_center* - Name of the data center in which the network is
                           located.
    **Return**: Returns the desired network object in case of success,
                otherwise raises EntityNotFound
    '''
    if data_center:
        dc_obj = DC_API.find(data_center)
        nets = NET_API.get(absLink=False)
        for net in nets:
            if net.get_data_center().get_id() == dc_obj.get_id() and \
                    net.get_name().lower() == network.lower():
                return net
        raise EntityNotFound('%s network does not exists!' % network)
    elif cluster:
        return findNetworkByCluster(network, cluster)
    else:
        return NET_API.find(network)


def findNetworkByCluster(network, cluster):
    '''
    Description:Design to compare cluster DC with network DC in order to
                workaround BZ#741111
    **Author**: atal
    **Parameters**:
        *  *network* - network name
        *  *cluster* - cluster name
    **return**: network object in case of success, raise EntityNotFound in case
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


def _prepareClusterNetworkObj(**kwargs):
    '''
    preparing cluster network object
    Author: edolinin, atal
    return: logical network data structure object for cluster
    '''
    net = kwargs.get('net', data_st.Network())

    if kwargs.get('usages', None) is not None:
        net.set_usages(data_st.Usages(usage=kwargs.get('usages').split(',')))

    if 'required' in kwargs:
        net.set_required(kwargs.get('required'))

    if 'display' in kwargs:
        net.set_display(kwargs.get('display'))

    return net


def getClusterNetwork(cluster, network):
    '''
    Find a network by cluster (along with the network properties that are
    specific to the cluster).
    **Parameters**:
        *  *cluster* - Name of the cluster in which the network is located.
        *  *network* - Name of the network.
    **Return**: Returns the network object if it's found or raises
                EntityNotFound exception if it's not.
    '''
    clusterObj = CL_API.find(cluster)
    return CL_API.getElemFromElemColl(clusterObj,
                                      network,
                                      'networks',
                                      'network')


def getClusterNetworks(cluster):
    '''
    Get href of the cluster's networks.
    **Parameters**:
        *  *cluster* - Name of the cluster.
    **Return**: Returns the href that links to the cluster's networks.
    '''
    clusterObj = CL_API.find(cluster)
    return CL_API.getElemFromLink(clusterObj,
                                  link_name='networks',
                                  attr='network',
                                  get_href=True)


@is_action()
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
    kwargs.update(net=findNetwork(network, cluster=cluster))
    net = _prepareClusterNetworkObj(**kwargs)
    cluster_nets = getClusterNetworks(cluster)
    res, status = NET_API.create(net,
                                 positive,
                                 collection=cluster_nets)

    return status


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


# FIXME: change to use conf file for vlan networks name
@is_action()
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
        if not addNetwork(positive,
                          name=net_name,
                          data_center=data_center,
                          vlan_id=vlan):
            return False, {'nets': None}
    return True, {'nets': nics}


@is_action()
def isNetworkRequired(network, cluster):
    '''
    Description: Check if Network is required
    Author: atal
    Parameters:
        * network - logical network name
        * cluster = cluster name
    return: True if network is required, False otherwise.
    '''
    net_obj = getClusterNetwork(cluster, network)

    return net_obj.get_required()


@is_action()
def isVMNetwork(network, cluster):
    '''
    Description: Check if Network is VM network
    Author: atal
    Parameters:
        * network - logical network name
        * cluster = cluster name
    return: True if network is VM network, False otherwise.
    '''
    net_obj = getClusterNetwork(cluster, network)
    usages = net_obj.get_usages()
    return 'vm' in usages.usage


def checkIPRule(host, user, password, subnet):
    '''
    Check occurence of specific ip in 'ip rule' command output
    Author: gcheresh
    Parameters:
        *  *host* - remote machine ip address or fqdn
        *  *user* - root user on the machine
        *  *password* - password for the root user
        *  *subnet* - subnet to search for
    return True/False
    '''
    machine = Machine(host, user, password).util(LINUX)
    cmd = ["ip", "rule"]
    rc, out = machine.runCmd(cmd)
    logger.info("The output of ip rule command is:\n %s", out)
    if not rc:
        logger.error("Failed to run ip rule command")
        return False
    return len(re.findall(subnet.replace('.', '[.]'), out)) == 2


def updateVnicProfile(name, network, cluster=None, data_center=None,
                      new_name=None, port_mirroring=None, description=None):
    '''
    Description: Update VNIC profile with provided parameters in kwargs
    **Author**: gcheresh
    **Parameters**:
        *  *name* - name of VNIC profile to update
        *  *network* - network name used by profile to be updated
        *  *cluster* - name of cluster in which the network is located
        *  *data_center* - name of the data center in which the network
                           is located
        *  *new_name* - new name for the VNIC profile
        *  *port_mirroring* - Enable/Disable port mirroring for profile
        *  *description* - New description of vnic profile
    **Return**: True, if adding vnic profile was success, otherwise False
    '''

    vnic_profile_obj = getVnicProfileObj(name=name, network=network,
                                         cluster=cluster,
                                         data_center=data_center)
    new_vnic_profile_obj = vnic_profile_obj

    logger.info("Updating VNIC profile with new parameters")

    if new_name:
        new_vnic_profile_obj.set_name(new_name)

    if port_mirroring is not None:
        new_vnic_profile_obj.set_port_mirroring(port_mirroring)

    if description:
        new_vnic_profile_obj.set_description(description)

    if not VNIC_PROFILE_API.update(vnic_profile_obj, new_vnic_profile_obj,
                                   True):
        logger.error("Updating %s profile failed", name)
        return False

    return True


def getNetworkVnicProfiles(network, cluster=None, data_center=None):
    '''
    Returns all the VNIC profiles that belong to a certain network
    **Author**: tgeft
    **Parameters**:
        *  *network* - Name of the network.
        *  *cluster* - Name of the cluster in which the network is located.
        *  *data_center* - Name of the data center in which the network is
                           located.
    **Return**: Returns a list of VNIC profile objects that belong to the
                provided network.
    '''
    netObj = findNetwork(network, data_center, cluster)
    return NET_API.getElemFromLink(netObj, link_name='vnicprofiles',
                                   attr='vnic_profile', get_href=False)


def getVnicProfileObj(name, network, cluster=None, data_center=None):
    '''
    Finds the VNIC profile object.
    **Author**: tgeft
    **Parameters**:
        *  *name* - Name of the VNIC profile to find.
        *  *network* - Name of the network used by the VNIC profile.
        *  *cluster* - Name of the cluster in which the network is located.
        *  *data_center* - Name of the data center in which the network
                           is located.
    **Return**: Returns the VNIC profile object if it's found or raises
                EntityNotFound exception if it's not.
    '''
    matching_profiles = filter(lambda profile: profile.get_name() == name,
                               getNetworkVnicProfiles(network, cluster,
                                                      data_center))
    if matching_profiles:
        return matching_profiles[0]
    else:
        raise EntityNotFound('VNIC profile %s was not found among the profiles'
                             ' of network %s' % (name, network))


# noinspection PyUnusedLocal
@is_action()
def addVnicProfile(positive, name, cluster=None, data_center=None,
                   network=MGMT_NETWORK, port_mirroring=False,
                   custom_properties=None,
                   description=""):
    '''
    Description: Add new vnic profile to network in cluster with cluster_name
    **Author**: alukiano
    **Parameters**:
        *  *positive* - Expected result
        *  *name* - name of vnic profile
        *  *network* - Network name to be used by profile
        *  *cluster* - name of cluster in which the network is located
        *  *data_center* - name of the data center in which the network
                           is located
        *  *port_mirroring* - Enable port mirroring for profile
        *  *custom_properties* - Custom properties for the profile
        *  *description* - Description of vnic profile
    **Return**: True, if adding vnic profile was success, otherwise False
    '''
    vnic_profile_obj = data_st.VnicProfile()
    network_obj = findNetwork(network, data_center, cluster)
    logger.info("\n"
                "Creating vnic profile:\n"
                "                      name: %s\n"
                "                      Network: %s\n"
                "                      Port mirroring: %s\n"
                "                      Custom properties: %s\n"
                "                      Description: %s",
                name, network, port_mirroring, custom_properties, description)
    vnic_profile_obj.set_name(name)
    vnic_profile_obj.set_network(network_obj)

    if port_mirroring:
        vnic_profile_obj.set_port_mirroring(port_mirroring)

    if description:
        vnic_profile_obj.set_description(description)

    if custom_properties:
        from art.rhevm_api.tests_lib.low_level.vms import \
            createCustomPropertiesFromArg
        vnic_profile_obj.set_custom_properties(
            createCustomPropertiesFromArg(custom_properties))

    if not VNIC_PROFILE_API.create(vnic_profile_obj, positive)[1]:
        logger.error("Creating %s profile failed", name)
        return False

    return True


@is_action()
def removeVnicProfile(positive, vnic_profile_name, network, cluster=None,
                      data_center=None):
    '''
    Description: Remove vnic profiles with given names
    **Author**: alukiano
    **Parameters**:
        *  *positive* - Expected result
        *  *vnic_profile_name* -Vnic profile name
        *  *network* - Network name used by profile
        *  *cluster* - name of the cluster the network reside on (None for all
                       clusters)
        *  *data_center* - Name of the data center in which the network
                           is located (None for all data centers)
    **Return**: True if action succeeded, otherwise False
    '''
    profileObj = getVnicProfileObj(vnic_profile_name, network, cluster,
                                   data_center)
    logger.info("Trying to remove vnic profile %s", vnic_profile_name)

    if not VNIC_PROFILE_API.delete(profileObj, positive):
        logger.error("Expected result was %s, got the opposite", positive)
        return False

    return True
