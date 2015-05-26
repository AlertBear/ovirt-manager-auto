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


def get_list_of_online_cpus_on_resource(resource):
    """
    Return number of online cpus on resource

    :param resource: resource
    :type resource: instance of VDS
    :returns: list of online cpu's on host
    :rtype: list
    """
    online_cpus_l = []
    command = ['lscpu']
    rc, out, err = resource.executor().run_cmd(command)
    if rc:
        logger.error(
            "Failed to run command %s on resource %s; out: %s; err: %s",
            command, resource, out, err
        )
        return online_cpus_l
    online_cpus = re.search(r'On-line CPU\(s\) list:\s+(\S+)', out).group(1)
    online_cpus = online_cpus.split(',')
    for cpus in online_cpus:
        if '-' in cpus:
            t_cpus = cpus.split('-')
            online_cpus_l.extend(xrange(int(t_cpus[0]), int(t_cpus[1]) + 1))
        else:
            online_cpus_l.append(int(cpus))
    return online_cpus_l


def start_cpu_loading_on_resources(
    resources,
    load,
    name_of_script=LOAD_SCRIPT_NAME,
    dir_of_script=LOAD_SCRIPT_DIR
):
    """
    Load resources CPU to specific value

    :param resources: list of resources
    :type resources: list
    :param load: CPU load to create
    :type load: int
    :param name_of_script: name of loading script(by default load_host.sh)
    :type name_of_script: str
    :param dir_of_script: directory where to put script(by default /tmp)
    :type dir_of_script: str
    :returns: True, if method succeeded, else False
    :rtype: bool
    """
    for resource in resources:
        logger.info("Get number of online CPU's from resource %s", resource)
        num_of_cpus = len(get_list_of_online_cpus_on_resource(resource))
        if not num_of_cpus:
            logger.error(
                "Failed to get number of online CPU's from resource %s",
                resource
            )
            return False
        logger.info(
            "Number of online CPU's on resource %s: %d", resource, num_of_cpus
        )
        num_of_cpus /= 100 / load
        logger.info(
            "Create CPU load script on resource %s", resource
        )
        script_body = (
            "#!/bin/bash\n"
            "for i in `seq 1 %d`;\n"
            "do while :\n"
            " do :\n"
            " done &\n"
            " done" %
            num_of_cpus
        )
        script_path = resource.create_script(
            script_body, name_of_script, dir_of_script
        )
        if not script_path:
            logger.error(
                "Failed to create CPU load script on resource %s", resource
            )
            return False
        cmd = [
            "sh", script_path, "&>", "/tmp/OUT1", "&", "echo", "$!"
        ]
        logger.info(
            "Run CPU load script '%s' on resource %s", script_path, resource
        )
        logger.info(
            "Running command %s on resource %s", " ".join(cmd), resource
        )
        rc, out, err = resource.executor().run_cmd(cmd)
        if rc:
            logger.error(
                "Running command %s on resource %s failed; err: %s; out: %s",
                " ".join(cmd), resource, err, out
            )
            return False
        if out:
            logger.info("Output of command %s: %s", " ".join(cmd), out)
    return True


def stop_cpu_loading_on_resources(
        resources,
        name_of_script=LOAD_SCRIPT_NAME,
        dir_of_script=LOAD_SCRIPT_DIR
):
    """
    Stop CPU loading on resources

    :param resources: list of resources
    :type resources: list
    :param name_of_script: name of loading script(by default load_host.sh)
    :type name_of_script: str
    :param dir_of_script: directory where to put script(by default /tmp)
    :type dir_of_script: str
    """
    cmd = [
        "kill", "$(pidof", "sh", "%s)" % os.path.join(
            dir_of_script, name_of_script
        )
    ]
    for resource in resources:
        logger.info("Stop CPU loading on resource %s", resource)
        logger.info(
            "Running command %s on resource %s", " ".join(cmd), resource
        )
        rc, out, err = resource.executor().run_cmd(cmd)
        if rc:
            logger.error(
                "Running command %s on host %s failed; err: %s; out: %s",
                " ".join(cmd), resource, err, out
            )
