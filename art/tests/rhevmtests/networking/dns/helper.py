#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper for DNS tests
"""

import shlex

import config as dns_conf
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from rhevmtests.networking import helper as network_helper
from rhevmtests import helpers
from art.core_api import apis_utils, apis_exceptions


def get_host_dns_servers(host):
    """
    Get host DNS servers (/etc/reslove.conf)

    Arg:
        host (str): Host name

    Returns:
        list: Host DNS servers
    """
    host_resource = helpers.get_host_resource_by_name(host_name=host)
    rc, out, _ = host_resource.executor().run_cmd(
        shlex.split(
            "cat {resolve_conf}".format(resolve_conf=dns_conf.RESOLVE_CONF)
        )
    )
    if rc:
        return list()

    return [i.rsplit()[-1] for i in out.splitlines() if "nameserver" in i]


def refresh_caps_if_network_unsynced(host, network, last_event):
    """
    Refresh host caps if network is unsynced

    Args:
        host (str): Host name
        network (str): Network name
        last_event (str): Event ID to check from

    Returns:
        bool: True if network sync, False otherwise
    """
    sampler = apis_utils.TimeoutingSampler(
        30, 1, network_helper.networks_sync_status, host, [network]
    )

    try:
        for s in sampler:
            if s:
                return True

            if not ll_hosts.refresh_host_capabilities(
                host=host, start_event_id=last_event
            ):
                return False
    except apis_exceptions.APITimeout:
        return False
