#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for arbitrary_vlan_device_name
"""

import pytest

import config as vlan_name_conf
import helper
import rhevmtests.helpers as global_helper
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
        testflow.teardown("Remove networks from setup")
        assert net_helper.remove_networks_from_setup(
            hosts=arbitrary_vlan_device_name.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Create networks %s on setup", vlan_name_conf.ARBITRARY_NET_DICT
    )
    net_helper.prepare_networks_on_setup(
        networks_dict=vlan_name_conf.ARBITRARY_NET_DICT,
        dc=arbitrary_vlan_device_name.dc_0,
        cluster=arbitrary_vlan_device_name.cluster_0
    )


@pytest.fixture(scope="module")
def set_virsh_credentials(request):
    """
    Set virsh credentials on vds host-0
    """
    arbitrary_vlan_device_name = NetworkFixtures()

    assert net_helper.set_virsh_sasl_password(
        vds_resource=arbitrary_vlan_device_name.vds_0_host
    )


@pytest.fixture(scope="class")
def create_vlans_and_bridges_on_host(request, set_virsh_credentials):
    """
    Add VLANs and bridge names on host.
    """
    arbitrary_vlan_device_name = NetworkFixtures()
    param_list = request.node.cls.param_list
    vlan_name_list = request.node.cls.vlan_names
    bridge_name_list = request.node.cls.bridge_names
    vds_host = arbitrary_vlan_device_name.vds_0_host
    host_name = arbitrary_vlan_device_name.host_0_name
    result = list()

    def fin4():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)
    request.addfinalizer(fin4)

    def fin3():
        """
        Delete bridge
        """
        for bridge in bridge_name_list:
            if vds_host.network.get_bridge(bridge):
                try:
                    testflow.teardown(
                        "Delete BRIDGE: %s from host %s", bridge, host_name
                    )
                    vds_host.network.delete_bridge(bridge=bridge)
                except Exception:
                    result.append(
                        (False, "fin3: vds_host.network.delete_bridge")
                    )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove bridges from host
        """
        for br in bridge_name_list:
            if net_helper.virsh_is_network_exists(
                vds_resource=vds_host, network=br
            ):
                result.append(
                    (
                        net_helper.virsh_delete_network(
                            vds_resource=vds_host, network=br
                        ), "fin2: net_helper.virsh_delete_network"
                    )
                )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove VLANs from host
        """
        vlans_to_remove = [
            v for v in vlan_name_list if
            helper.is_interface_on_host(host_obj=vds_host, interface=v)
            ]
        testflow.teardown(
            "Remove VLANs %s from host %s", vlans_to_remove, host_name
        )
        result.append(
            (
                helper.remove_vlan_and_refresh_capabilities(
                    host_obj=vds_host, vlan_name=vlans_to_remove
                ), "fin1: helper.remove_vlan_and_refresh_capabilities"
            )
        )
    request.addfinalizer(fin1)

    for nic, vlan_ids, vlan_names, bridge_names in param_list:
        testflow.setup("Create VLANs %s on host %s", vlan_names, vds_host)
        assert helper.add_vlans_to_host(
            host_obj=vds_host, nic=nic, vlan_id=vlan_ids, vlan_name=vlan_names
        )
        testflow.setup("Create bridges %s on host %s", bridge_names, vds_host)
        assert helper.add_bridge_on_host_and_virsh(
            host_obj=vds_host, bridge=bridge_names, network=vlan_names
        )
