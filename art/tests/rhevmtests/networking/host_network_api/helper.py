#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for Host Network API
"""

import shlex
import logging

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as net_api_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.unittest_lib import testflow

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
    host = conf.HOST_0_NAME
    networks = [i for i in net_sync_reason]
    if network_helper.networks_sync_status(host=host, networks=networks):
        logger.error("%s are synced but shouldn't", networks)
        return False

    for net, val in net_sync_reason.iteritems():
        reas = val.keys()[0]
        dict_to_compare = net_sync_reason.get(net).get(reas)
        logger.info("Check if %s unsync reason is %s", net, reas)
        unsync_reason = hl_host_network.get_networks_unsync_reason(
            host_name=host, networks=[net]
        )
        if not unsync_reason.get(net).get(reas) == dict_to_compare:
            logger.error(
                "Expected reasons are %s, got %s instead",
                dict_to_compare, unsync_reason.get(net).get(reas)
            )
            return False
    return True


def manage_host_ip(interface, ip=None, netmask="24"):
    """
    Set temporary IP on interface and refresh capabilities

    Args:
        interface (str): Interface name.
        ip (str): IP to set.
        netmask (str): Netmask for the IP.

    Raises:
        AssertionError: If failed to set temporary IP on interface
    """
    int_ip = conf.VDS_0_HOST.network.find_ip_by_int(interface)
    host_ips = conf.VDS_0_HOST.network.find_ips()
    if int_ip:
        old_ip = [i for i in host_ips[1] if int_ip == i.split("/")[0]][0]
        del_ip_cmd = "ip addr del %s dev %s" % (old_ip, interface)
        assert not conf.VDS_0_HOST.run_command(shlex.split(del_ip_cmd))[0]

    if ip or netmask != "24":
        ip = int_ip if not ip else ip
        assert network_helper.configure_temp_static_ip(
            vds_resource=conf.VDS_0_HOST, ip=ip, nic=interface, netmask=netmask
        )


def attach_networks_for_parametrize(
    network, nic, via, log_, ip=None, properties=None, positive=True,
    update=False, remove=False
):
    """
    Attach network to host via HostNic, Host and SetupNetwork API

    Args:
        network (str): network name
        nic (str): NIC name
        via (str): The API to use
        log_ (str): Testflow to use
        ip (dict): IP to set
        properties (dict): Network custom properties to set
        positive (bool): Test type (negative/positive)
        update (bool): True to update existing network
        remove (bool): Trie to remove network

    Raises:
        AssertionError: if the test fail
    """
    host_0 = conf.HOST_0_NAME
    testflow.step(log_)

    # Host NIC and Host
    if via == "host_nic" or via == "host":
        use_nic = nic if via == "host_nic" else None
        if remove:
            res = hl_host_network.remove_networks_from_host(
                host_name=host_0, networks=[network], nic=use_nic
            )
        else:
            sn_dict = {
                "network": network,
                "nic": nic if via == "host" else None,
                "ip": ip,
                "properties": properties
            }
            if update:
                res = hl_host_network.update_network_on_host(
                    host_name=host_0, nic_name=use_nic, **sn_dict
                )
            else:
                res = hl_host_network.add_network_to_host(
                    host_name=host_0, nic_name=use_nic, **sn_dict
                )
        assert res is positive

    # SetupNetworks
    if via == "sn":
        network_dict = {
            "network": network,
            "nic": nic,
            "ip": ip,
            "properties": properties
        }
        if update:
            sn_dict = {
                "update": {
                    "1": network_dict
                }
            }
        elif remove:
            sn_dict = {
                "remove": {
                    "networks": [network]
                }
            }
        else:
            sn_dict = {
                "add": {
                    "1": network_dict
                }
            }

        res = hl_host_network.setup_networks(host_name=host_0, **sn_dict)
        assert res is positive


def get_dict(network, type_, ex=None, act=None):
    """
    Get param from network dict

    Args:
        network (str): network name
        type_ (str): The param type to get
        ex (str): Expected to set
        act (str): Actual to set

    Returns:
        dict: param dict for check sync function
    """
    share = net_api_conf.AVERAGE_SHARE_STR
    limit = net_api_conf.AVERAGE_LIMIT_STR
    real = net_api_conf.AVERAGE_REAL_STR

    params_dict = {
        network: {
            type_: {}
        }
    }
    dict_c_1_1 = net_api_conf.SYNC_DICT_1_CASE_1
    dict_c_1_2 = net_api_conf.SYNC_DICT_2_CASE_1

    dict_c_3_1 = net_api_conf.SYNC_DICT_1_CASE_3
    dict_c_3_2 = net_api_conf.SYNC_DICT_2_CASE_3

    if type_ == net_api_conf.VLAN_STR:
        act = dict_c_1_1.get(network).get("vlan_id", None)
        ex = dict_c_1_2.get(network).get("vlan_id", None)
        params_dict[network][type_]["actual"] = act
        params_dict[network][type_]["expected"] = ex

    if type_ == net_api_conf.MTU_STR:
        act = dict_c_1_1.get(network).get("mtu", 1500)
        ex = dict_c_1_2.get(network).get("mtu", 1500)
        params_dict[network][type_]["actual"] = str(act)
        params_dict[network][type_]["expected"] = str(ex)

    if type_ == net_api_conf.BRIDGE_STR:
        act = str(bool(dict_c_1_1.get(network).get("usages", True))).lower()
        ex = str(bool(dict_c_1_2.get(network).get("usages", True))).lower()
        params_dict[network][type_]["actual"] = act
        params_dict[network][type_]["expected"] = ex

    if type_ in [
            net_api_conf.IPADDR_STR, net_api_conf.NETMASK_STR,
            net_api_conf.BOOTPROTO_STR
    ]:
        params_dict[network][type_]["actual"] = act
        params_dict[network][type_]["expected"] = ex

    if type_ in [share, limit, real]:
        get_type = None
        if type_ == share:
            get_type = "outbound_average_linkshare"

        if type_ == limit:
            get_type = "outbound_average_upperlimit"

        if type_ == real:
            get_type = "outbound_average_realtime"

        act = dict_c_3_1.get(network).get("qos", {}).get(get_type)
        ex = dict_c_3_2.get(network).get("qos", {}).get(get_type)
        params_dict[network][type_]["actual"] = str(act) if act else None
        params_dict[network][type_]["expected"] = str(ex) if ex else None

    return params_dict


def get_ip_dict(ip, proto):
    """
    Get IP dict updated

    Args:
        ip (str): IP to add to the dict
        proto (str): Boot protocol to add to the dict

    Returns:
        dict: IP dict for setupNetworks
    """
    ipv6_dict = net_api_conf.IPV6_IP_DICT.copy()
    if ip:
        ipv6_dict["address"] = ip
    else:
        ipv6_dict["address"] = None
        ipv6_dict["netmask"] = None

        if proto == "autoconf":
            ipv6_dict["boot_protocol"] = "autoconf"

        if proto == "dhcp":
            ipv6_dict["boot_protocol"] = "dhcp"

    return ipv6_dict
