#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper for DNS tests
"""

import shlex

import config as dns_conf
from rhevmtests import helpers


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
        ), tcp_timeout=300, io_timeout=300
    )
    if rc:
        return list()

    return [i.rsplit()[-1] for i in out.splitlines() if "nameserver" in i]
