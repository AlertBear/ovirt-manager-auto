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
import random
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level.hosts import get_linux_machine_obj
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
LOAD_SCRIPT_NAME = "load_host.sh"
LOAD_SCRIPT_DIR = "/tmp"

logger = logging.getLogger(__name__)


def get_pinned_cpu(host, host_user, host_pwd, vm, vcpu):
    """
    Get the pCPU which vCPU is running on

    :param host: ip of host
    :param host_user: user for connection to host
    :param host_pwd: password for connection to host
    :param vm: name of the vm
    :param vcpu: number of virtual CPU

    :returns: number of pCPU on success, False on failure
    """
    host_machine = get_linux_machine_obj(host, host_user, host_pwd)
    rc, output = host_machine.runCmd(['virsh', '-r', 'list', '|grep', vm])
    if not rc or not output:
        HOST_API.logger.error("Can't read 'virsh -r list' on %s", host)
        return False
    vm_id = output.split()[0]
    HOST_API.logger.info("VM pid is %s", vm_id)
    rc, output = host_machine.runCmd(['virsh', '-r', 'vcpuinfo', vm_id])
    if not rc or not output:
        HOST_API.logger.error("Can't read 'virsh -r vcpuinfo {0}'"
                              " on {1}".format(vm_id, host))
        return False
    regex = r'VCPU:\s+' + vcpu + r'\s+CPU:\s+(\d)'
    res = re.search(regex, output).group(1)
    HOST_API.logger.info("vCPU {0} of VM {1} is pinned to physical "
                         "CPU {2}.".format(vcpu, vm, res))
    return res


def get_pinned_cpu_affinity(host, host_user, host_pwd, vm, vcpu):
    """
    Gets the vCPU pinning affinity

    :param host: ip of host
    :param host_user: user for connection to host
    :param host_pwd: password for connection to host
    :param vm: name of the vm
    :param vcpu: number of virtual CPU
    :returns: String containing the affinity on success,
                    False on failure
    """
    host_machine = get_linux_machine_obj(host, host_user, host_pwd)
    rc, output = host_machine.runCmd(['virsh', '-r', 'list', '|grep', vm])
    if not rc or not output:
        HOST_API.logger.error("Can't read 'virsh -r list' on %s", host)
        return False
    vm_id = output.split()[0]
    rc, output = host_machine.runCmd(['virsh', '-r', 'vcpuinfo', vm_id])
    if not rc or not output:
        HOST_API.logger.error("Can't read 'virsh -r vcpuinfo {0} on"
                              " {1}".format(vm_id, host))
        return False
    regex = r'VCPU:\s+' + vcpu + r'[\w\W]+?CPU Affinity:\s+([-y]+)'
    res = re.search(regex, output).group(1)
    HOST_API.logger.info("CPU affinity of vCPU {0} of VM {1} is "
                         "{2}.".format(vcpu, vm, res))
    return res


def check_random_pinning(host, host_user, host_pwd, vm):
    """
    Pins a VM with a single core CPU to a random core on host, checking
    if pinning works as expected

    :param host: ip of host
    :param host_user: user for connection to host
    :param host_pwd: password for connection to host
    :param vm: name of the vm
    :returns: True on success, False on failure
    """
    host_obj = HOST_API.find(host)
    total_cores = int(
        host_obj.cpu.topology.sockets) * int(host_obj.cpu.topology.cores)
    expected_pin = str(random.randint(0, total_cores - 1))
    expected_affinity = '-' * int(expected_pin) + 'y' + '-' * (
        total_cores - int(expected_pin) - 1)
    if not vms.updateVm(
            positive=True, vm=vm, vcpu_pinning={'0': expected_pin},
            placement_affinity=ENUMS['vm_affinity_pinned'],
            placement_host=host):
        VM_API.logger.error("Could not update VM.")
        return False
    if not vms.startVm(positive=True, vm=vm):
        VM_API.logger.error("Could not start VM.")
        return False
    actual_pin = get_pinned_cpu(host, host_user, host_pwd, vm, '0')
    actual_affinity = get_pinned_cpu_affinity(
        host, host_user, host_pwd, vm, '0')[:total_cores]
    if not vms.stopVm(positive=True, vm=vm):
        VM_API.logger.error("Could not stop VM.")
        return False
    if (not actual_pin) or (not actual_affinity):
        HOST_API.logger.error("Could not retrieve VM pinning information.")
        return False
    VM_API.logger.info(
        "vCPU #0 is expected to be pinned to vCPU #{0}, and is actually pinned"
        " to vCPU #{1}.".format(expected_pin, actual_pin))
    VM_API.logger.info(
        "vCPU #0 is expected to have pinning affinity of {0}, and actually has"
        " {1}.".format(expected_affinity, actual_affinity))
    if (actual_pin != expected_pin) or (actual_affinity != expected_affinity):
        return False
    return True


def test_pinning_load(host, host_user, host_pwd, vm):
    """
    Pins all vCPU's of a VM to a single pCPU on host, checking
    if pinning holds

    :param host: ip of host
    :param host_user: user for connection to host
    :param host_pwd: password for connection to host
    :param vm: name of the vm
    :returns: True on success, False on failure
    """
    vm_obj = VM_API.find(vm)
    vm_total_cores = int(
        vm_obj.cpu.topology.sockets) * int(vm_obj.cpu.topology.cores)
    pinning = dict()
    for i in range(vm_total_cores):
        pinning[str(i)] = '0'
    if not vms.updateVm(
            positive=True, vm=vm, vcpu_pinning=pinning,
            placement_affinity=ENUMS['vm_affinity_pinned'],
            placement_host=host
    ):
        VM_API.logger.error("Could not update VM.")
        return False
    if not vms.startVm(positive=True, vm=vm):
        VM_API.logger.error("Could not start VM.")
        return False
    for i in range(vm_total_cores):
        actual_pin = get_pinned_cpu(host, host_user, host_pwd, vm, str(i))
        if not actual_pin:
            HOST_API.logger.error("Could not retrieve VM pinning information.")
            return False
        if actual_pin != '0':
            VM_API.logger.error(
                "vCPU #{0} is not running on pCPU #0.".format(i))
            return False
    if not vms.stopVm(positive=True, vm=vm):
        VM_API.logger.error("Could not stop VM.")
        return False
    return True


def get_num_of_cpus(host, host_user, host_passwd):
    """
    Return number of physical cpus on host

    :param host: name of host
    :param host_user: user for connection to host
    :param host_passwd: password for connection to host

    :returns: number of physical cpu's
    """
    host_machine = get_linux_machine_obj(host, host_user, host_passwd)
    logger.debug("Run lscpu command on host %s", host)
    rc, output = host_machine.runCmd(['lscpu'])
    num_of_cpus = re.findall(r'CPU\(s\):\s*\d+', output)
    num_of_cpus = num_of_cpus[0].split(':')[1].strip()
    return int(num_of_cpus)


def cpu_load_script(num_of_cpus, script_name, target,
                    host, host_user, host_passwd):
    """
    Create bash script for loading cpu's on host

    :param num_of_cpus: number of cpu's to load
    :param script_name: name of script to create
    :param target: directory on host to copy script
    :param host: name of host
    :param host_user: user for connection to host
    :param host_passwd: password for connection to host

    :returns: True, if script was created, else False
    """
    host_machine = get_linux_machine_obj(host, host_user, host_passwd)
    with open(script_name, 'w+') as fd:
        fd.write("#!/bin/bash\n"
                 "for i in `seq 1 %d`;\n"
                 "do while :\n do :\n done &\n done" % num_of_cpus)
    try:
        host_machine.copyTo(script_name, target, 300)
    except IOError as error:
        logger.error("Copy data to %s : %s" % (host, error))
    except Exception as error:
        logger.error("%s\nConnecting or copying data to %s", host, error)
    cmd = ["chmod", "755", os.path.join(target, script_name)]
    rc, out = host_machine.runCmd(cmd)
    if rc == -1:
        logger.error("Running command %s on host %s failed",
                     " ".join(cmd), host)
        return False
    if out:
        logger.info("Output of command %s: %s", " ".join(cmd), out)
    return True


def load_cpu(host, host_user, host_passwd, load,
             name_of_script=LOAD_SCRIPT_NAME,
             dir_of_script=LOAD_SCRIPT_DIR):
    """
    Load cpu on given host

    :param host: name of host
    :param host_user: user for connection to host
    :param host_passwd: password for connection to host
    :param load: number of CPU's to load
    :param name_of_script: name of loading script(by default load_host.sh)
    :param dir_of_script: directory where to put script(by default /tmp)
    :returns: True, if method was succeeded, else False
    """
    if not cpu_load_script(load, name_of_script, dir_of_script,
                           host, host_user, host_passwd):
        logger.info("Creating loading script failed")
        return False
    host_machine = get_linux_machine_obj(host, host_user, host_passwd)
    cmd = ["sh", os.path.join(dir_of_script, name_of_script)]
    rc, out = host_machine.runCmd(cmd)
    if rc == -1:
        logger.error("Running command %s on host %s failed",
                     " ".join(cmd), host)
        return False
    if out:
        logger.info("Output of command %s: %s", " ".join(cmd), out)
    return True


def stop_loading_cpu(host, host_user, host_passwd,
                     name_of_script=LOAD_SCRIPT_NAME,
                     dir_of_script=LOAD_SCRIPT_DIR):
    """
    Stop loading cpu on host

    :param host: name of host
    :param host_user: user for connection to host
    :param host_passwd: password for connection to host
    :param name_of_script: name of loading script(by default load_host.sh)
    :param dir_of_script: directory where to put script(by default /tmp)
    :returns: True, if method was succeeded, else False
    """
    host_machine = get_linux_machine_obj(host, host_user, host_passwd)
    cmd = ["kill", "$(pidof", "sh",
           os.path.join(dir_of_script, name_of_script) + ")"]
    logger.info("Running command %s on host %s", " ".join(cmd), host)
    rc, out = host_machine.runCmd(cmd)
    if rc == -1:
        logger.error("Running command %s on host %s failed",
                     " ".join(cmd), host)
        return False
    if out:
        logger.info("Output of command %s: %s", " ".join(cmd), out)
    return True
