#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Helper for hot plug cpu module
"""
from rhevmtests.virt import config
from art.test_handler import exceptions

logger = config.logging.getLogger("virt.hot_plug.hot_plug_cpu.helper")

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
    :return: list with cpu_socket and cpu_core
    :rtype: list
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
