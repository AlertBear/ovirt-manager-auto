#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for arbitrary_vlan_device_name
"""
import shlex

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import config as vlan_name_conf
import helper
import rhevmtests.networking.helper as net_helper
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def create_networks_on_engine(request):
    """
    Create networks on engine
    """
    arbitrary_vlan_device_name = NetworkFixtures()

    def fin():
        """
        Remove the VLAN from the setup
        """
        assert hl_networks.remove_net_from_setup(
            host=[arbitrary_vlan_device_name.host_0_name], all_net=True,
            data_center=arbitrary_vlan_device_name.dc_0
        )
    request.addfinalizer(fin)

    net_helper.prepare_networks_on_setup(
        networks_dict=vlan_name_conf.ARBITRARY_NET_DICT,
        dc=arbitrary_vlan_device_name.dc_0,
        cluster=arbitrary_vlan_device_name.cluster_0
    )


@pytest.fixture(scope="class")
def create_vlans_on_host(request):
    """
    Add VLANs and bridge names on host.
    """
    arbitrary_vlan_device_name = NetworkFixtures()
    param_list = request.node.cls.param_list
    vlan_name_list = request.node.cls.vlan_names
    vds_host = arbitrary_vlan_device_name.vds_0_host
    host_name = arbitrary_vlan_device_name.host_0_name

    def fin():
        """
        Remove VLANs from host
        """
        ip_link_out = vds_host.run_command(shlex.split("ip link"))[1]
        vlans_to_remove = [v for v in vlan_name_list if v in ip_link_out]
        testflow.teardown(
            "Remove VLANs %s from host %s", vlans_to_remove, host_name
        )
        assert helper.remove_vlans_and_refresh_capabilities(
            host_obj=vds_host, vlans_names=vlans_to_remove
        )

    request.addfinalizer(fin)

    for nic, vlan_ids, vlan_names in param_list:
        testflow.setup("Create VLANs %s on host %s", vlan_names, vds_host)
        assert helper.add_vlans_to_host(
            host_obj=vds_host, nic=nic, vlan_id=vlan_ids, vlan_names=vlan_names
        )
    assert helper.refresh_host_capabilities(host=host_name)
