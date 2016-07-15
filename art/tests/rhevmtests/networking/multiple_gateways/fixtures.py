#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for multiple gateways
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as multiple_gw_conf
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def multiple_gw_prepare_setup(request):
    """
    Create dummies on host
    Create networks on engine
    """
    multiple_gw = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        multiple_gw.remove_networks_from_setup(hosts=multiple_gw.host_0_name)
    request.addfinalizer(fin)

    multiple_gw.prepare_networks_on_setup(
        networks_dict=multiple_gw_conf.NETS_DICT, dc=multiple_gw.dc_0,
        cluster=multiple_gw.cluster_0
    )


@pytest.fixture(scope="class")
def teardown_all_cases(request, multiple_gw_prepare_setup):
    """
    Teardown for all cases
    """
    multiple_gw = NetworkFixtures()

    def fin():
        """
        Clean hosts interfaces
        """
        hl_host_network.clean_host_interfaces(
            host_name=multiple_gw.host_0_name
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def attach_networks_to_host(request, teardown_all_cases):
    """
    Attach networks to host NICs
    """
    multiple_gw = NetworkFixtures()
    net = request.node.cls.net
    ip = request.node.cls.ip
    nic = request.node.cls.nic
    slaves = request.node.cls.slaves
    if slaves:
        slaves = [multiple_gw.host_0_nics[i] for i in slaves]

    netmask = conf.NETMASK
    gateway = conf.MG_GATEWAY
    host_nic = multiple_gw.host_0_nics[nic] if isinstance(nic, int) else nic

    sn_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": host_nic,
                "slaves": slaves,
                "ip": {
                    "1": {
                        "address": ip,
                        "netmask": netmask,
                        "gateway": gateway,
                        "boot_protocol": "static"
                    }
                }
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=multiple_gw.host_0_name, **sn_dict
    )
