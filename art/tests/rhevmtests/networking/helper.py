#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for networking jobs
"""

import logging
from random import randint
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.low_level.vms as ll_vms


def create_random_ips(num_of_ips=2, mask=16):
    """
    Create random IPs (only support masks 8/16/24)
    :param num_of_ips: Number of IPs to create
    :type num_of_ips: int
    :param mask: IP subnet to create the IPs for
    :type mask: int
    :return: IPs
    :rtype: list
    """
    ips = []
    ip_mask = mask // 8
    base_ip = ".".join("5" * ip_mask)
    for i in xrange(num_of_ips):
        rand_num = [randint(1, 250) for i in xrange(4 - ip_mask)]
        rand_oct = ".".join(str(i) for i in rand_num)
        ips.append(".".join([base_ip, rand_oct]))
    return ips


def run_vm_once_specific_host(vm, host, wait_for_ip=False):
    """
    Run VM once on specific host

    :param vm: VM name
    :type vm: str
    :param host: Host name
    :type host: str
    :return: True if action succeeded, False otherwise
    :rtype: bool
    """
    logging.info("Run VM once on host %s", host)
    if not ll_vms.runVmOnce(positive=True, vm=vm, host=host):
        logging.error("Couldn't run VM on host %s", host)
        return False
    if wait_for_ip:
        logging.info("Wait to get IP address")
        if not ll_vms.waitForIP(vm)[0]:
            logging.error("VM didn't get IP address")
            return False
    logging.info("Check that VM was started on host %s", host)
    vm_host = ll_vms.getVmHost(vm)[1]["vmHoster"]
    if not host == vm_host:
        logging.error(
            "VM should start on %s instead of %s", host, vm_host)
        return False
    return True


def seal_vm(vm, root_password):
    """
    Start VM, seal VM and stop VM

    :param vm: VM name
    :type vm: str
    :param root_password: VM root password
    :type root_password: str
    :return: True/False
    :rtype: bool
    """
    logging.info("Start VM: %s", vm)
    if not ll_vms.startVm(positive=True, vm=vm):
        logging.error("Failed to start %s.", vm)
        return False

    logging.info("Waiting for IP from %s", vm)
    rc, out = ll_vms.waitForIP(vm=vm, timeout=180, sleep=10)
    if not rc:
        logging.error("Failed to get %s IP", vm)
        return False

    ip = out["ip"]
    logging.info("Running setPersistentNetwork on %s", vm)
    if not test_utils.setPersistentNetwork(host=ip, password=root_password):
        logging.error("Failed to seal %s", vm)
        return False

    logging.info("Stopping %s", vm)
    if not ll_vms.stopVm(positive=True, vm=vm):
        logging.error("Failed to stop %s", vm)
        return False
    return True

if __name__ == "__main__":
    pass
