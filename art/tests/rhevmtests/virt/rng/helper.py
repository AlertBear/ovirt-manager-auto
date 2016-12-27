#! /usr/bin/python
# -*- coding: utf-8 -*-

import shlex
import rhevmtests.helpers as helpers


def check_if_device_exists(vm_name, device_name):
    """
    Check if device exists

    Args:
        vm_name(str): Vm name
        device_name(str): Rng device name

    Returns:
        bool: True if device exists, False otherwise
    """
    host_resource = helpers.get_host_resource_of_running_vm(vm_name)
    cmd = "virsh -r dumpxml %s | grep %s" % (vm_name, device_name)
    rc, out, _ = host_resource.run_command(shlex.split(cmd))
    assert not rc, "Failed to run virsh command"
    return True if out else False
