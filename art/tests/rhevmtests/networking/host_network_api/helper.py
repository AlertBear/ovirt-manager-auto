#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for Host Network API
"""

import logging

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.utils.test_utils as test_utils
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("Host_Network_API_Helper")


def get_networks_sync_status_and_unsync_reason(net_sync_reason):
    """
    Check if networks attachment is unsync and check the unsync reason

    Args:
        net_sync_reason (dict): List of tuple of (network_name, unsync_reason)

    Returns:
        bool: True if network attachment is unsync and if unsync reason
            is correct, else False.
    """
    networks = [i for i in net_sync_reason]
    if network_helper.networks_sync_status(
        host=conf.HOST_0_NAME, networks=networks
    ):
        logger.error("%s are synced but shouldn't", networks)
        return False

    for net, val in net_sync_reason.iteritems():
        reas = val.keys()[0]
        dict_to_compare = net_sync_reason[net][reas]
        logger.info("Check if %s unsync reason is %s", net, reas)
        unsync_reason = hl_host_network.get_networks_unsync_reason(
            conf.HOST_0_NAME, [net]
        )
        if not unsync_reason[net][reas] == dict_to_compare:
            logger.error(
                "Expected reasons are %s, got %s instead",
                dict_to_compare, unsync_reason[net][reas]
            )
            return False
    return True


def manage_ip_and_refresh_capabilities(
    interface, ip=None, netmask="24", set_ip=True
):
    """
    Set temporary IP on interface and refresh capabilities

    Args:
        interface (str): Interface name.
        ip (str): IP to set.
        netmask (str): Netmask for the IP.
        set_ip (bool): True to set IP on interface.

    Raises:
        AssertionError: If failed to set temporary IP on interface and
            refresh capabilities.
    """
    old_ip = None
    int_ip = conf.VDS_0_HOST.network.find_ip_by_int(interface)
    host_ips = conf.VDS_0_HOST.network.find_ips()
    if int_ip:
        old_ip = [i for i in host_ips[1] if int_ip in i][0]

    if old_ip:
        remove_ip_from_interface(ip=old_ip, interface=interface)

    if set_ip:
        ip = int_ip if not ip else ip
        set_ip_on_interface(ip=ip, netmask=netmask, interface=interface)

    last_event = ll_events.get_max_event_id(query="")
    logger.info("Refresh capabilities for %s", conf.HOST_0_NAME)
    ll_hosts.refresh_host_capabilities(
        host=conf.HOST_0_NAME, start_event_id=last_event
    )


def remove_ip_from_interface(ip, interface):
    """
    Remove IP from interface using ip address.

    Args:
        ip (str): IP to remove.
        interface (str): Interface where the IP is.

     Raises:
        AssertionError: If failed to remove IP from interface.
    """
    cmd = ["ip", "addr", "del", "%s" % ip, "dev", interface]
    assert not conf.VDS_0_HOST.run_command(cmd)[0]


def set_ip_on_interface(ip, netmask, interface):
    """
    Set IP on interface using ip address

    Args:
        ip (str): IP to set.
        netmask (str): Netmask for the IP.
        interface (str): Interface to set the IP on.

     Raises:
        AssertionError: If failed to set IP on interface.
    """
    assert test_utils.configure_temp_static_ip(
        vds_resource=conf.VDS_0_HOST, ip=ip, nic=interface, netmask=netmask
    )
