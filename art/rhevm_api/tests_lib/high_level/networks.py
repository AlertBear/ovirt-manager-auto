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

import os
import logging
import re

from art.rhevm_api.tests_lib.low_level.networks import addNetwork,\
    getClusterNetwork, DC_API, removeNetwork, addNetwork,\
    addNetworkToCluster
from art.rhevm_api.tests_lib.low_level.hosts import sendSNRequest,\
    commitNetConfig, genSNNic, genSNBond
from art.core_api.apis_exceptions import EntityNotFound
from utilities.utils import readConfFile
from art.core_api import is_action
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger(__package__ + __name__)
CONNECTIVITY_TIMEOUT = 60


@is_action()
def addMultipleVlanedNetworks(networks, data_center, **kwargs):
    '''
    Adding multiple networks with vlan according to the given prefix and range
    Author: atal
    Parameters:
        * networks - a list of vlaned networks with their vlan suffix
        * date_center - the DataCenter name
        * kwargs - all arguments related to basic addNetwork
    return True with new nics name list or False with empty list
    '''

    for network in networks:
        vlan = re.search(r'(\d+)', network)
        if not addNetwork('True', name=network, data_center=data_center,
                          vlan_id=vlan.group(0), **kwargs):
            return False
    return True


# FIXME: need to check if this function is being used else just remove.
@is_action()
def getNetworkConfig(positive, cluster, network, datacenter=None, tag=None):
    '''
     Validate Datacenter/Cluster network configurations/existence.
     This function tests the network configured parameters. we look for
     networks link under cluster even though we check the DC network
     configurations only because cluster networks related
     to main networks href.
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

        # return False means that given datacenter
        #doesn't contain the given network
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
@is_action()
def validateNetwork(positive, cluster, network, tag, val):
    status, output = getNetworkConfig(positive, cluster, network, tag=tag)
    if not status:
        return False
    if str(output['value']).lower() != str(val).lower():
        return False
    return True


@is_action()
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


def createAndAttachNetworkSN(data_center, cluster, host, auto_nics=[],
                             network_dict={}):
    '''
        Function that creates and attach the network to the:
        a) DC, b) Cluster, c) Host with SetupNetworks
        Author: gcheresh
        Parameters:
        * data_center - DC name
        * cluster - Cluster name
        * host - remote machine ip address or fqdn
        * auto_nics - a list of nics
        * network_dict - dictionary of dictionaries for the following
          net parameters:
            * logical network name as the key for the following:
                * nic - interface to create the network on
                * usages - VM/non-VM or display network
                * vlan_id - list of values, each value for specific network
                * mtu - list of values, each value for specific network
                * required - required/non-required network
                * bond - bond name to create
                * slaves - interfaces that the bond will be composed from
                * mode - the mode of the bond
        Return: True value if succeeded in creating and adding network list
                to DC/Cluster and Host
    '''

    net_obj = []
    for key in network_dict.keys():
        logger.info("Adding network to DC")
        bond = network_dict[key].get('bond')
        if not addNetwork(True, name=key, data_center=data_center,
                          usages=network_dict[key].get('usages', 'vm'),
                          vlan_id=network_dict[key].get('vlan_id'),
                          mtu=network_dict[key].get('mtu')):
            logger.error("Cannot add network to DC")
            return False

        logger.info("Adding network to Cluster")
        if not addNetworkToCluster(True, network=key, cluster=cluster,
                                   required=network_dict[key].
                                   get('required')):
            logger.error("Cannot add network to Cluster")
            return False

        if not bond:
            logger.info("Generating network object for SetupNetwork ")
            rc, out = genSNNic(nic=network_dict[key]['nic'],
                               network=key,
                               vlan=network_dict[key].get('vlan_id', 0))
            if not rc:
                logger.error("Cannot generate network object")
                return False
            net_obj.append(out['host_nic'])
        if bond:
            logger.info("Generating network object for bond ")
            rc, out = genSNBond(name=network_dict[key]['bond'],
                                network=key,
                                slaves=network_dict[key].get('slaves'),
                                mode=network_dict[key].get('mode'))
            if not rc:
                logger.error("Cannot generate network object ")
                return False
            net_obj.append(out['host_nic'])
    try:
        sendSNRequest(True, host=host, nics=net_obj,
                      auto_nics=auto_nics, check_connectivity='true',
                      connectivity_timeout=60, force='false')
    except Exception as ex:
        logger.error("SendSNRequest failed %s", ex)
        return False
    return True


def removeNetFromSetup(host, auto_nics=['eth0'], network=[]):
    '''
        Function that removes networks from the host, Cluster and DC:
        Author: gcheresh
        Parameters:
        * host - remote machine ip address or fqdn
        * auto_nics - a list of nics
        * network - list of networks to remove
        Return: True value if succeeded in deleting network
                from Host, Cluster DC
    '''
    try:
        sendSNRequest(True, host=host,
                      auto_nics=auto_nics,
                      check_connectivity='true',
                      connectivity_timeout=CONNECTIVITY_TIMEOUT,
                      force='false')
        commitNetConfig(True, host=host)
        for index in range(len(network)):
            removeNetwork(True, network=network[index])
    except Exception as ex:
        logger.error("Remove Network from setup failed %s", ex, exc_info=True)
        return False
    return True
