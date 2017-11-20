#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures for DNS tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    hosts as ll_hosts,
)
import config as dns_conf
import helper
import rhevmtests.helpers as global_helper
from rhevmtests.networking import config as conf


@pytest.fixture(scope="module", autouse=True)
def get_hosts_params(request):
    """
    Get host network info and store them in dns_conf.HOSTS_NET_INFO
    """

    def fin():
        """
        Restore host IP boot protocol to DHCP
        """
        sn_dict = {
            "update": {
                "1": {
                    "datacenter": conf.DC_0,
                    "network": conf.MGMT_BRIDGE,
                    "ip": {
                        "1": {
                            "boot_protocol": "dhcp",
                        }
                    }
                }
            }
        }

        assert hl_host_network.setup_networks(
            host_name=dns_conf.WORKING_HOST, **sn_dict
        )
    request.addfinalizer(fin)

    spm = ll_hosts.get_spm_host(hosts=conf.HOSTS)
    hosts = filter(lambda x: x != spm, conf.HOSTS)
    dns_conf.WORKING_HOST = hosts[0]

    for host in conf.HOSTS:
        dns_conf.HOSTS_NET_INFO[host] = {}
        host_resource = global_helper.get_host_resource_by_name(host_name=host)
        net_info = host_resource.network.get_info()
        if net_info.get("bridge") == conf.MGMT_BRIDGE:
            dns_conf.HOSTS_NET_INFO[host]["net_info"] = net_info

        dnss = helper.get_host_dns_servers(host=host)
        dns_conf.HOSTS_NET_INFO[host]["dns"] = dnss
        dns_conf.HOSTS_NET_INFO[host]["ip"] = dnss

    host_ip = dns_conf.HOSTS_NET_INFO.get(
        dns_conf.WORKING_HOST
    ).get("net_info").get("ip")

    host_prefix = dns_conf.HOSTS_NET_INFO.get(
        dns_conf.WORKING_HOST
    ).get("net_info").get("prefix")

    host_gateway = dns_conf.HOSTS_NET_INFO.get(
        dns_conf.WORKING_HOST
    ).get("net_info").get("gateway")

    sn_dict = {
        "update": {
            "1": {
                "datacenter": conf.DC_0,
                "network": conf.MGMT_BRIDGE,
                "ip": {
                    "1": {
                        "address": host_ip,
                        "netmask": host_prefix,
                        "gateway": host_gateway,
                        "boot_protocol": "static",
                    }
                }
            }
        }
    }

    assert hl_host_network.setup_networks(
        host_name=dns_conf.WORKING_HOST, **sn_dict
    )


@pytest.fixture(scope="class")
def restore_host_dns_servers(request):
    """
    Restore host DNS servers
    """
    results = list()
    network = conf.MGMT_BRIDGE
    dc = conf.DC_0
    sn_dict = {
        "update": {
            "1": {
                "datacenter": dc,
                "network": network,
                "dns": list()
            }
        }
    }

    def fin3():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove DNS checkbox from the hosts NIC
        """
        results.append(
            (
               hl_host_network.setup_networks(
                            host_name=dns_conf.WORKING_HOST, **sn_dict
                        ), "fin2: hl_host_network.setup_networks"
                )
            )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove DNS checkbox from the network
        """
        results.append(
            (
                ll_networks.update_network(
                    positive=True, network=network, dns=list(), data_center=dc
                ), "fin1: ll_networks.update_network (remove DNS checkbox)"
            )
        )
    request.addfinalizer(fin1)
