#! /usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2013 Red Hat, Inc.
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
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger(__name__)
DEFAULT_HOST_NICS_NUM = 4
NUM_OF_NETWORKS = 5
DEFAULT_MTU = "1500"
PREFIX = "net"


def find_ip(vm, host_list, nic_index, vlan=None, bond=None):
    """
    Find source and destination IP for hosts

    :param vm:  VM name
    :type vm: str
    :param host_list:  List of the hosts (resource.VDS objects)
    :type host_list: list
    :param nic_index:  Nic to get IP on the hosts
    :type nic_index: int
    :param vlan: VLAN name
    :type vlan: str
    :param bond: BOND name
    :type bond: str
    :return: Source and destination IPs
    :rtype: tuple
    """
    src_host, dst_host, dst_name_engine = None, None, None
    orig_host = get_host(vm)
    for host in host_list:
        host_name_engine = ll_hosts.get_host_name_from_engine(host.ip)
        if host_name_engine == orig_host:
            src_host = host
        else:
            dst_host = host
            dst_name_engine = host_name_engine
    if vlan:
        if not bond:
            src_int = ".".join([src_host.nics[nic_index], vlan])
            dst_int = ".".join([dst_host.nics[nic_index], vlan])
        else:
            src_int = dst_int = ".".join([bond, vlan])

    elif bond:
        src_int = dst_int = bond
    else:
        src_int = src_host.nics[nic_index]
        dst_int = dst_host.nics[nic_index]
    return (
        hl_networks.getIpOnHostNic(orig_host, src_int),
        hl_networks.getIpOnHostNic(dst_name_engine, dst_int)
    )


def get_host(vm):
    """
    Find the host that the VM is running on

    :param vm: VM name
    :type vm: str
    :return: Host that VM is running on
    :rtype: str
    """
    rc, out = ll_vms.getVmHost(vm)
    if not rc:
        raise exceptions.NetworkException("Cannot get host that VM resides on")
    return out['vmHoster']


def vlan_int_name(interface, vlan):
    """
    Build the name for tagged interface or bond

    :param interface: interface name
    :type interface: str
    :param vlan: vlan id
    :type vlan: str
    :return: interface.vlan name format
    :rtype: str
    """
    return ".".join([interface, vlan])


def check_dummy_on_host_interfaces(host_name, dummy_name):
    """
    Check if dummy interface is on host via engine

    :param host_name: Host name
    :type host_name: str
    :param dummy_name: Dummy name
    :type dummy_name: str
    :return: True if dummy interface is on host False otherwise
    :rtype: bool
    """
    host_nics = ll_hosts.getHostNicsList(host_name)
    for nic in host_nics:
        if dummy_name == nic.name:
            return True
    return False


def get_clusters_managements_networks_ids(cluster=None):
    """
    Get clusters managements networks IDs for all clusters in the engine if
    not cluster else get only for the given cluster

    :param cluster: Cluster name
    :type cluster: list
    :return: managements networks ids
    :rtype: list
    """
    clusters = (
        ll_clusters.CLUSTER_API.get(absLink=False) if not cluster else cluster
    )
    return [
        ll_networks.get_management_network(cluster_name=cl.name).id
        for cl in clusters
        ]
