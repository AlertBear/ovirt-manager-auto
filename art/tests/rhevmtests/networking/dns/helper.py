#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper for DNS tests
"""

import shlex

import rhevmtests.networking.config as conf


def get_host_dns_servers():
    """
    Get host DNS servers (/etc/reslove.conf)

    Returns:
        list: Host DNS servers
    """
    rc, out, _ = conf.VDS_2_HOST.executor().run_cmd(
        shlex.split("cat /etc/resolv.conf")
    )
    if rc:
        return list()

    return [i.rsplit()[-1] for i in out.splitlines() if "nameserver" in i]
