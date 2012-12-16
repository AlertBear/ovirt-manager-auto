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
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

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
    rc, output = host_machine.runCmd(['virsh', '-r', 'list','|grep', vm])
    if not rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r list' on %s", host)
         return False
    vm_id = output.split()[0]
    HOST_API.logger.info("VM pid is %s",vm_id)
    rc, output = host_machine.runCmd(['virsh','-r','vcpuinfo', vm_id])
    if not rc or not output:
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
    rc, output = host_machine.runCmd(['virsh','-r','list', '|grep', vm])
    if not rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r list' on %s", host)
         return False
    vm_id = output.split()[0]
    rc, output  = host_machine.runCmd(['virsh','-r','vcpuinfo', vm_id])
    if not rc or not output:
         HOST_API.logger.error("Can't read 'virsh -r vcpuinfo {0} on"
                               " {1}".format(vm_id,host))
         return False
    regex=r'VCPU:\s+' + vcpu + r'[\w\W]+?CPU Affinity:\s+([-y]+)'
    res = re.search(regex, output).group(1)
    HOST_API.logger.info("CPU affinity of vCPU {0} of VM {1} is "
                         "{2}.".format(vcpu, vm, res))
    return res

@is_action()
def checkRandomPinning(positive, host, host_user, host_pwd, vm):
    '''
    Pins a VM with a single core CPU to a random core on host, checking
    if pinning works as expected.
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
        * vm - name of the vm
    Return value: True on success, False on failure
    '''
    host_obj = HOST_API.find(host)
    total_cores = int(host_obj.cpu.topology.sockets) * int(host_obj.cpu.topology.cores)
    expected_pin = str(random.randint(0, total_cores - 1))
    expected_affinity = '-' * int(expected_pin) + 'y' + '-' * (total_cores - int(expected_pin) - 1)
    if not updateVm(positive=True, vm=vm, vcpu_pinning={'0':expected_pin},
                    placement_affinity=ENUMS['vm_affinity_pinned'], placement_host=host):
        VM_API.logger.error("Could not update VM.")
        return not positive
    if not startVm(positive=True, vm=vm):
        VM_API.logger.error("Could not start VM.")
        return not positive
    actual_pin = getPinnedCPU(positive, host, host_user, host_pwd, vm, '0')
    actual_affinity = getPinnedCPUAffinity(positive, host, host_user, host_pwd, vm, '0')[:total_cores]
    if not stopVm(positive=True, vm=vm):
        VM_API.logger.error("Could not stop VM.")
        return not positive
    if (not actual_pin) or (not actual_affinity):
        HOST_API.logger.error("Could not retrieve VM pinning information.")
        return not positive
    VM_API.logger.info("vCPU #0 is expected to be pinned to vCPU #{0}, and is actually pinned to "
                       "vCPU #{1}.".format(expected_pin, actual_pin))
    VM_API.logger.info("vCPU #0 is expected to have pinning affinity of {0}, and actually has "
                       "{1}.".format(expected_affinity, actual_affinity))
    if (actual_pin != expected_pin) or (actual_affinity != expected_affinity):
        return not positive
    return positive

@is_action()
def testPinningLoad(positive, host, host_user, host_pwd, vm):
    '''
    Pins all vCPU's of a VM to a single pCPU on host, checking
    if pinning holds.
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
        * vm - name of the vm
    Return value: True on success, False on failure
    '''
    vm_obj = VM_API.find(vm)
    vm_total_cores = int(vm_obj.cpu.topology.sockets) * int(vm_obj.cpu.topology.cores)
    actual_pin = 0
    pinning = dict()
    for i in range(vm_total_cores):
        pinning[str(i)] = '0'
    if not updateVm(positive=True, vm=vm, vcpu_pinning=pinning,
                    placement_affinity=ENUMS['vm_affinity_pinned'], placement_host=host):
        VM_API.logger.error("Could not update VM.")
        return not positive
    if not startVm(positive=True, vm=vm):
        VM_API.logger.error("Could not start VM.")
        return not positive
    for i in range(vm_total_cores):
        actual_pin = getPinnedCPU(positive, host, host_user, host_pwd, vm, str(i))
        if (not actual_pin):
            HOST_API.logger.error("Could not retrieve VM pinning information.")
            return not positive
        if actual_pin != '0':
            VM_API.logger.error("vCPU #{0} is not running on pCPU #0.".format(i))
            return not positive
    if not stopVm(positive=True, vm=vm):
        VM_API.logger.error("Could not stop VM.")
        return not positive
    return positive
