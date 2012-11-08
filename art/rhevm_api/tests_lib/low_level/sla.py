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
import re
import random
import os
from utilities import machine
from utilities.utils import readConfFile
from art.core_api import is_action
from vms import updateVm, startVm, stopVm, createVm, removeVm
from art.rhevm_api.utils.test_utils import get_api

ELEMENTS = os.path.join(os.path.dirname(__file__), '../../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
HOST_API = get_api('host', 'hosts')

logger = logging.getLogger(__package__ + __name__)


@is_action()
def getPinnedCPU(positive, host, host_user, host_pwd, vm, vcpu):
    '''
    Gets the pCPU which vCPU is running on.
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
        * vm - name of the vm
        * vcpu - number of virtual CPU
    Return value: number of pCPU on success, False on failure
    '''
    output = None
    host_machine = machine.Machine(host, host_user, host_pwd).util('linux')
    rc, output, err = host_machine.runCmd(['virsh', '-r', 'list','|grep', vm])
    if rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r list' on %s", host)
         return False
    vm_id = output.split()[0]
    HOST_API.logger.info("VM pid is %s",vm_id)
    rc, output, err = host_machine.runCmd(['virsh','-r','vcpuinfo', vm_id])
    if rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r vcpuinfo {0}'"
                               " on {1}".format(vm_id, host))
         return False
    regex=r'VCPU:\s+' + vcpu + r'\s+CPU:\s+(\d)'
    res = re.search(regex, output).group(1)
    HOST_API.logger.info("vCPU {0} of VM {1} is pinned to physical "
                         "CPU {2}.".format(vcpu, vm, res))
    return res

@is_action()
def getPinnedCPUAffinity(positive, host, host_user, host_pwd, vm, vcpu):
    '''
    Gets the vCPU pinning affinity.
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
        * vm - name of the vm
        * vcpu - number of virtual CPU
    Return value: String containing the affinity on success,
                    False on failure
    '''
    output = None
    host_machine = machine.Machine(host, host_user, host_pwd).util('linux')
    rc, output, err = host_machine.runCmd(['virsh','-r','list', '|grep', vm])
    if rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r list' on %s", host)
         return False
    vm_id = output.split()[0]
    rc, output, err  = host_machine.runCmd(['virsh','-r','vcpuinfo', vm_id])
    if rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r vcpuinfo {0} on"
                               " {1}".format(vm_id,host))
         return False
    regex=r'VCPU:\s+' + vcpu + r'[\w\W]+?CPU Affinity:\s+([-y]+)'
    res = re.search(regex, output).group(1)
    HOST_API.logger.info("CPU affinity of vCPU {0} of VM {1} is "
                         "{2}.".format(vcpu, vm, res))
    return res
