#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network custom properties
"""
import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as custom_prop_conf
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


@pytest.fixture(scope="module")
def prepare_setup(request, network_cleanup_fixture):
    """
    Create networks on engine
    """
    custom_properties = NetworkFixtures()

    def fin2():
        """
        Remove ve dummies interfaces from host
        """
        custom_properties.remove_dummies(
            host_resource=custom_properties.vds_0_host
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove networks from engine
        """
        custom_properties.remove_networks_from_setup(
            hosts=custom_properties.host_0_name
        )
    request.addfinalizer(fin1)

    custom_properties.prepare_dummies(
        host_resource=custom_properties.vds_0_host, num_dummy=conf.NUM_DUMMYS
    )

    custom_properties.prepare_networks_on_setup(
        networks_dict=custom_prop_conf.NETS_DICT, dc=custom_properties.dc_0,
        cluster=custom_properties.cluster_0
    )


@pytest.fixture(scope="class")
def teardown_all_cases(request, prepare_setup):
    """
    Teardown for all cases
    """
    custom_properties = NetworkFixtures()

    def fin():
        """
        Clean host interfaces
        """
        hl_host_network.clean_host_interfaces(
            host_name=custom_properties.host_0_name
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def attach_networks_to_host(request, teardown_all_cases):
    """
    Attach networks to host NICs
    """
    custom_properties = NetworkFixtures()
    net_nic_list = request.node.cls.net_nic_list
    ethtool_properties = request.node.cls.ethtool_properties
    bridge_opts_properties = request.node.cls.bridge_opts_properties
    ethtool_checksums = request.node.cls.ethtool_checksums
    clear_custom_properties = request.node.cls.clear_custom_properties
    slaves = request.node.cls.slaves
    slaves_created = False
    ethtool_opts = "ethtool_opts"
    bridge_opts = "bridge_opts"
    properties = dict()
    sn_dict = {
        "add": {}
    }
    sn_dict_clear = {
        "update": {}
    }
    for network, nic in net_nic_list:
        if isinstance(nic, int):
            host_nic = custom_properties.host_0_nics[nic]
            slaves = None
        else:
            host_nic = nic
            if not slaves_created:
                slaves = (
                    custom_properties.host_0_nics[-2:] if not slaves else
                    custom_properties.host_0_nics[2:4]
                )
                slaves_created = True
            else:
                slaves = None

        if clear_custom_properties:
            properties = {
                ethtool_opts: None,
                bridge_opts: None
            }

            def fin():
                """
                Clear host NIC custom properties
                """
                sn_dict_clear["update"][network] = {
                    "network": network,
                    "nic": host_nic,
                    "slaves": slaves,
                    "properties": properties
                }
                hl_host_network.setup_networks(
                    host_name=custom_properties.host_0_name, **sn_dict_clear
                )
            request.addfinalizer(fin)

        if ethtool_properties:
            nic = host_nic if not slaves else "*"
            state = ethtool_properties.get(ethtool_opts)
            for checksum in ethtool_checksums:
                properties[ethtool_opts] = checksum.format(
                    nic=nic, state=state
                )

        if bridge_opts_properties:
            properties[bridge_opts] = bridge_opts_properties.get(
                bridge_opts
            )

        sn_dict["add"][network] = {
            "network": network,
            "nic": host_nic,
            "slaves": slaves,
            "properties": properties
        }
        properties = dict()

    assert hl_host_network.setup_networks(
        host_name=custom_properties.host_0_name, **sn_dict
    )
