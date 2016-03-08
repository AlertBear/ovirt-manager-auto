#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for Host Network API
"""

import logging
import config as conf
from art.unittest_lib import attr
import art.unittest_lib as unit_lib
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Helper")


def attach_network_attachment(nic=None, positive=True, **network_dict):
    """
    Attach network attachment to host NIC via NIC or host href

    :param network_dict: Network dict
    :type network_dict: dict
    :param nic: NIC name
    :type nic: str
    :param positive: Expected status
    :type positive: bool
    :raise: NetworkException
    """
    res = hl_host_network.add_network_to_host(
        host_name=conf.HOST_0_NAME, nic_name=nic, **network_dict
    )
    if res != positive:
        raise conf.NET_EXCEPTION()


def networks_unsync_reasons(net_sync_reason):
    """
    Check the reason for unsync networks is correct

    :param net_sync_reason: List of tuples of (network_name, unsync_reason)
    :type net_sync_reason: dict
    :return: True if unsync reason is correct
    :rtype: bool
    """
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


def get_networks_sync_status_and_unsync_reason(net_sync_reason):
    """
    Check if networks attachment is unsync and check the unsync reason

    :param net_sync_reason: List of tuple of (network_name, unsync_reason)
    :type net_sync_reason: dict
    :raise: conf.NET_EXCEPTION
    """
    networks = [i for i in net_sync_reason]
    if network_helper.networks_sync_status(
        host=conf.HOST_0_NAME, networks=networks
    ):
        raise conf.NET_EXCEPTION("%s are synced but shouldn't" % networks)

    if not networks_unsync_reasons(net_sync_reason):
        raise conf.NET_EXCEPTION("%s unsync reason is incorrect" % networks)


@attr(tier=2)
class TestHostNetworkApiTestCaseBase(unit_lib.NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    @classmethod
    def teardown_class(cls):
        """
        Remove all networks from the host NICs.
        """
        network_helper.remove_networks_from_host()


def manage_ip_and_refresh_capabilities(
    interface, ip=None, netmask="24", set_ip=True
):
    """
    Set temporary IP on interface and refresh capabilities

    :param interface: Interface name
    :type interface: str
    :param ip: IP to set
    :type ip: str
    :param netmask: Netmask for the IP
    :type netmask: str
    :param set_ip: True to set IP on interface
    :type set_ip: bool
    :raise: NET_EXCEPTION
    """
    old_ip = None
    int_ip = conf.VDS_0_HOST.network.find_ip_by_int(interface)
    host_ips = conf.VDS_0_HOST.network.find_ips()
    if int_ip:
        old_ip = [i for i in host_ips[1] if int_ip in i][0]

    if old_ip:
        remove_interface_ip(ip=old_ip, interface=interface)

    if set_ip:
        ip = int_ip if not ip else ip
        set_interface_ip(ip=ip, netmask=netmask, interface=interface)
    host_obj = ll_hosts.HOST_API.find(conf.HOST_0_NAME)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)


def remove_interface_ip(ip, interface):
    """
    Remove IP from interface using ip addr

    :param ip: IP to remove
    :type ip: str
    :param interface: Interface where the IP is
    :type interface: str
    :raise: NET_EXCEPTION
    """
    cmd = ["ip", "addr", "del", "%s" % ip, "dev", interface]
    rc, _, _ = conf.VDS_0_HOST.run_command(cmd)
    if rc:
        raise conf.NET_EXCEPTION()


def set_interface_ip(ip, netmask, interface):
    """
    Set IP on interface using ip addr

    :param ip: IP to set
    :type ip: str
    :param netmask: Netmask for the IP
    :type netmask: str
    :param interface: Interface to set the IP on
    :type interface: str
    :raise: NET_EXCEPTION
    """
    if not test_utils.configure_temp_static_ip(
        vds_resource=conf.VDS_0_HOST, ip=ip, nic=interface, netmask=netmask
    ):
        raise conf.NET_EXCEPTION()
