#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for required network job
"""

import logging
import config as conf
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

logger = logging.getLogger("Required_Network_Helper")


def deactivate_hosts(host=None):
    """
    Set first host as SPM
    Deactivating all other hosts in setup

    Args:
        host (str): Host name
    """
    host = host if host else conf.HOST_0_NAME
    if not ll_hosts.checkHostSpmStatus(
        positive=True, hostName=host
    ):
        if not ll_hosts.select_host_as_spm(
            positive=True, host=host, datacenter=conf.DC_0
        ):
            raise conf.NET_EXCEPTION()

    hosts = filter(lambda x: host != x, conf.HOSTS)
    for host in hosts:
        if not ll_hosts.deactivateHost(positive=True, host=host):
            raise conf.NET_EXCEPTION()


def activate_hosts():
    """
    Activating all hosts in setup besides the first host
    """
    for host in conf.HOSTS[1:]:
        ll_hosts.activateHost(positive=True, host=host)


def set_nics_and_wait_for_host_status(nics, nic_status, host_status="up"):
    """
    Set host NICs state and check for host status

    Args:
        nics (list): host NICs list
        nic_status (str): NIC status to set the NICs
        host_status (str): Host status to wait for

    Raises:
        NetworkException: If operation failed
    """
    func = getattr(conf.VDS_0_HOST.network, "if_%s" % nic_status)
    for nic in nics:
        logger.info("Set %s %s", nic, nic_status)
        if not func(nic=nic):
            raise conf.NET_EXCEPTION(
                "Failed to set %s %s" % (nic, nic_status)
            )

    if not ll_hosts.waitForHostsStates(
        positive=True, names=conf.HOST_0_NAME, timeout=300, states=host_status
    ):
        raise conf.NET_EXCEPTION()
