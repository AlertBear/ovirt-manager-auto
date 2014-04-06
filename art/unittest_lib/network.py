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


def find_ip(vm, host_list, nic):
    """
    Description: Find source and destination IP for hosts
    **Parameters**:
        *  *vm* - VM name
        *  *host_list* - List off the hosts
        *  *nic* - Nic to get IP on the hosts
    Return: Source and destination IPs
    """
    orig_host = get_host(vm)
    dst_host = host_list[(host_list.index(orig_host) + 1) % len(host_list)]
    return getIpOnHostNic(orig_host, nic), getIpOnHostNic(dst_host, nic)


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
