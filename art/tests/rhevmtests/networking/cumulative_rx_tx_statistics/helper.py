#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics helper file
"""

import logging
import operator

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import config as rx_tx_conf

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Helper")


def compare_nic_stats(
    nic, vm=None, host=None, total_rx=None, total_tx=None, oper=">="
):
    """
    Compare NIC statistics for VM or Host

    Args:
        nic (str): NIC name
        vm (str): VM name
        host (str): Host name
        total_rx (int): Total RX stats to check against
        total_tx (int): Total TX stats to check against
        oper (str): The operator to compare with

    Raises:
        AssertionError: if comparing NIC statistics failed
    """
    # logger.info("Get %s statistics on %s", nic, vm)
    nic_stat = hl_networks.get_nic_statistics(
        nic=nic, vm=vm, host=host, keys=rx_tx_conf.STAT_KEYS
    )
    comp_oper = operator.ge if oper == ">=" else operator.gt
    logger.info("--------------------------------------------------")
    logger.info("%s, %s", nic_stat["data.total.rx"], total_rx)
    logger.info("%s, %s", nic_stat["data.total.tx"], total_tx)
    logger.info("--------------------------------------------------")
    if not (
        comp_oper(nic_stat["data.total.rx"], total_rx) and
        comp_oper(nic_stat["data.total.tx"], total_tx)
    ):

        logger.error("Comparing NIC statistics failed")
        return False
    return True
