#! /usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import shlex

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config
import rhevmtests.helpers as helpers
from art.rhevm_api.resources import Host, User
from art.rhevm_api.tests_lib.low_level.hooks import (
    check_for_file_existence_and_content
)
from art.unittest_lib.common import testflow

logger = logging.getLogger(__name__)


def check_existence_of_payload(
    vm_name, payload_type, payload_device, payload_filename,
    payload_content
):
    """
    Mount payload and check if payload content exist

    Args:
        vm_name(str): vm_name
        payload_type(str): payload type
        payload_device(str): payload device (cd / floppy)
        payload_filename(str): file name
        payload_content(str): file content

    Returns:
        bool: True if payload found, False otherwise
    """

    payload_dir = os.path.join(config.TMP_DIR, payload_type)
    vm_ip = hl_vms.get_vm_ip(vm_name=vm_name)
    executor = helpers.get_vm_resource(vm=vm_name)
    testflow.step(
        "Create new directory %s on vm %s and modprobe device",
        payload_dir, vm_name
    )
    cmd = 'mkdir %s && modprobe %s' % (payload_dir, payload_type)
    rc, out, err = executor.run_command(shlex.split(cmd))
    if rc:
        logger.error(
            "Failed to run command %s on vm %s: %s" %
            (cmd, vm_name, out)
        )
        return False

    testflow.setup(
        "Mount device %s to directory %s", payload_device, payload_dir
    )
    cmd = 'mount %s %s' % (payload_device, payload_dir)
    rc, out, err = executor.run_command(shlex.split(cmd))
    if rc:
        logger.error(
            "Failed to run command %s on vm %s: %s" %
            (cmd, vm_name, out)
        )
        return False

    testflow.step("Check if file content exist on vm %s", vm_name)
    filename = os.path.join(payload_dir, payload_filename)

    vm_host = Host(ip=vm_ip)
    vm_host.users.append(
        User(
            name=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW
        )
    )
    return check_for_file_existence_and_content(
        positive=True,
        host=vm_host,
        filename=filename,
        content=payload_content
    )
