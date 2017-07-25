#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Helper for hot plug cpu module
"""
from art.unittest_lib.common import testflow
from rhevmtests.virt import config
from art.test_handler import exceptions
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from rhevmtests import helpers

logger = config.logging.getLogger("virt.hot_plug_unplug.cpu.helper")

NPROC_COMMAND = 'nproc'
MAX_NUM_CORES_PER_SOCKET = 16


def get_number_of_cores(resource):
    """
    Get the number of cores on the resource using `nproc` command
    :param resource: the resource of the VM/host
    :type: resource: VM/Host resource
    :return: the number of cores on the host
    :rtype: int
    """

    logger.info(
        "Run %s on %s in order to get the number of cores",
        NPROC_COMMAND, resource
    )
    rc, out, _ = resource.run_command([NPROC_COMMAND])
    if rc:
        return 0
    logger.info("Number of cores on:%s is:%s", resource, out)
    return int(out)


def calculate_the_cpu_topology(cpu_number):
    """
    Calculate the cpu topology (cores and sockets) with some limitations:
    - Maximum number of cores per socket is 16
    - A prime number of CPU can't be set

    :param cpu_number: the total number of CPU
    :type cpu_number: int
    :return: tuple with cpu_socket and cpu_core
    :rtype: tuple
    """
    cpu_socket = cpu_number
    cpu_core = 1
    if cpu_number > MAX_NUM_CORES_PER_SOCKET:
        for number in range(2, cpu_number):
            if cpu_number % number == 0:
                cpu_core = number
                cpu_socket = cpu_number / number
                if cpu_socket <= MAX_NUM_CORES_PER_SOCKET:
                    break
            else:
                raise exceptions.TestException(
                    "Can't set cpu_topology with %d, because it's a prime"
                    " number that is larger then %s"
                    % cpu_number, MAX_NUM_CORES_PER_SOCKET
                )
    logger.info("cpu socket:%d, cpu_core:%d", cpu_socket, cpu_core)
    return cpu_socket, cpu_core


def migrate_vm_and_check_cpu(number_of_cpus, vm_name=config.CPU_HOTPLUG_VM):
    """
    Migration VM and check CPU number on VM

    Args:
        vm_name: VM name
        number_of_cpus (int): Expected number of CPUs
    """
    testflow.step("migrating vm: %s", vm_name)
    assert ll_vms.migrateVm(True, vm_name)
    vm_resource = helpers.get_host_resource(
        hl_vms.get_vm_ip(vm_name), config.VMS_LINUX_PW
    )
    testflow.step(
        "Verifying that after migration vm: %s has %d cpus" %
        (vm_name, number_of_cpus)
    )
    assert get_number_of_cores(vm_resource) == number_of_cpus, (
        "The Cores number should be % and not: %s",
        number_of_cpus, ll_vms.get_vm_cores(vm_name)
    )


def hot_plug_unplug_cpu(
    number_of_cpus,
    action,
    vm_name=config.CPU_HOTPLUG_VM
):
    """
    Update VM CPU according to action (hot plug / hot unplug)
    And verify CPU amount on VM

    Args:
        number_of_cpus (int): Expected number of CPUs
        action (str): Hot plug / hot unplug action to update VM
        vm_name (str): VM name, default "cpu_hotplug_vm"
    """
    testflow.step(
        "%s case:\nUpdating number of cpu sockets on vm: %s to "
        "%d" % (action, vm_name, number_of_cpus)
    )
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        cpu_socket=number_of_cpus
    )
    vm_resource = helpers.get_host_resource(
        hl_vms.get_vm_ip(vm_name), config.VMS_LINUX_PW
    )
    working_cores = get_number_of_cores(vm_resource)
    testflow.step(
        "Verifying that after %s vm: %s has %d cpus" %
        (action, vm_name, number_of_cpus)
    )
    assert working_cores == number_of_cpus, (
        "The number of working cores: %s isn't correct" % working_cores
    )
