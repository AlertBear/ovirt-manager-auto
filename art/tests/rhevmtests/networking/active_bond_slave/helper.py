#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for active_bond_slave job
"""
import logging
import shlex

from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    hosts as ll_hosts
)
import rhevmtests.networking.config as conf

logger = logging.getLogger("networking.misc.helper")


def compare_active_slave_from_host_to_engine(bond):
    """
    Check if active slave that reported via engine match to the active slave
        on the host.

    Args:
        bond (str): Bond name.

    Returns:
        bool: True if the same active slave name exist on host file and on
            engine otherwise False.
    """
    logger.info("Check if active slave report on the host")
    cmd = "cat /sys/class/net/%s/bonding/active_slave" % bond
    rc, out, _ = conf.VDS_0_HOST.run_command(shlex.split(cmd))
    if rc or not out:
        logger.error("Active slave name isn't exist on the host")
        return False

    host_active_slave = out.strip()
    host_obj = ll_hosts.get_host_object(host_name=conf.HOST_0_NAME)
    logger.info("Check if active slave report on the engine")
    engine_active_slave = ll_networks.get_bond_active_slave_object(
        host=host_obj, bond=bond
    )
    if engine_active_slave is None:
        logger.error("Active slave name isn't exist on the engine")
        return False

    return host_active_slave == engine_active_slave.name
