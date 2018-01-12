#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for required network job
"""

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.config as conf
from art.rhevm_api.utils import test_utils


def deactivate_hosts(host=None):
    """
    Set first host as SPM
    Deactivating all other hosts in setup

    Args:
        host (str): Host name.

    Returns:
        bool: True if deactivate hosts succeeded, False if failed to deactivate
            hosts.
    """
    host = host if host else conf.HOST_0_NAME
    test_utils.wait_for_tasks(engine=conf.ENGINE, datacenter=conf.DC_0)
    if not ll_hosts.check_host_spm_status(positive=True, host=host):
        if not ll_hosts.select_host_as_spm(
            positive=True, host=host, data_center=conf.DC_0
        ):
            return False

    hosts = filter(lambda x: host != x, conf.HOSTS)
    for host in hosts:
        if not ll_hosts.deactivate_host(positive=True, host=host):
            return False

    return True


def set_nics_and_wait_for_host_status(nics, nic_status, host_status="up"):
    """
    Set host NICs state and check for host status

    Args:
        nics (list): host NICs list
        nic_status (str): NIC status to set the NICs
        host_status (str): Host status to wait for

    Returns:
        bool: True If operation was succeed, False otherwise
    """
    func = getattr(conf.VDS_0_HOST.network, "if_%s" % nic_status)
    for nic in nics:
        if not func(nic=nic):
            return False

    return ll_hosts.wait_for_hosts_states(
        positive=True, names=conf.HOST_0_NAME, timeout=300, states=host_status,
        sleep_=1
    )
