#!/usr/bin/env python

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
from art.rhevm_api.tests_lib.high_level.networks import getIpOnHostNic
from art.rhevm_api.tests_lib.low_level.hosts import get_host_name_from_engine
from art.rhevm_api.tests_lib.low_level.vms import getVmHost
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger(__name__)
DEFAULT_HOST_NICS_NUM = 4
DEFAULT_MTU = "1500"


def skipBOND(case_list, host_nics):
    """
    Description: Check if host can run BOND test (host have 4 interfaces)
    if not skip the test (only for unittest)
    **Author**: myakove
    **Parameters**:
       * *case_list* - list of class names from unittest test.
       * *host_nics* - List of interfaces on the host (use config.HOST_NICS)
    """
    if len(host_nics) < DEFAULT_HOST_NICS_NUM:
        for case in case_list:
            case.__test__ = False
            logger.info("%s is skipped, host cannot run BOND test case" % case)


def find_ip(vm, host_list, nic_index, vlan=None, bond=None):
    """
    Find source and destination IP for hosts
    :param vm:  VM name
    :param host_list:  List off the hosts (resource.VDS objects)
    :param nic_index:  Nic to get IP on the hosts
    :return: Source and destination IPs
    """
    src_host, dst_host, dst_name_engine = None, None, None
    orig_host = get_host(vm)
    for host in host_list:
        host_name_engine = get_host_name_from_engine(host.ip)
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
        getIpOnHostNic(orig_host, src_int),
        getIpOnHostNic(dst_name_engine, dst_int)
    )


def get_host(vm):
    """
    Description: Find the host that the VM is running on
        **Parameters**:
            *  *vm* - VM name
        Return: Host that VM is running on
    """
    rc, out = getVmHost(vm)
    if not rc:
        raise NetworkException("Cannot get host that VM resides on")
    return out['vmHoster']


def vlan_int_name(interface, vlan):
    """
        Description: Build the name for tagged interface or bond
            **Parameters**:
                *  *interface* - interface name
                *  *vlan* - vlan id
            Return: interface.vlan name format
        """
    return ".".join([interface, vlan])
