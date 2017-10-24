#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Helper for hot plug cpu module
"""
import shlex

import art.test_handler.exceptions as errors
from rhevmtests.compute.virt import config

logger = config.logging.getLogger("linux_boot_parameters")


def get_vm_root_device(vm_resource):
    """
    Get the root device on the resource using `df` command

    Args:
        vm_resource (resource): Resource of the VM

    Returns:
        str: The root device on the VM
    """
    command = "df -h / | awk 'NR==2{print \$1}'"
    logger.info(
        "Run %s on %s in order get the root device", command, vm_resource
    )
    rc, root_device, _ = vm_resource.run_command(shlex.split(command))
    if rc:
        raise errors.VMException("Failed to run command %s" % command)
    logger.info("The root device is %s", root_device.strip())
    return root_device.strip()
