#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for required network
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import config as required_conf
import helper
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class RequiredNetwork(NetworkFixtures):
    """
    Fixtures for labels
    """
    pass


@pytest.fixture(scope="module")
def requird_network_prepare_setup(request, network_cleanup_fixture):
    """
    prepare setup
    """
    required_network = RequiredNetwork()

    def fin2():
        """
        Finalizer for remove networks
        """
        required_network.remove_networks_from_setup(
            hosts=required_network.host_0_name
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for activate all hosts
        """
        helper.activate_hosts()
    request.addfinalizer(fin1)

    required_network.prepare_networks_on_setup(
        networks_dict=required_conf.NETS_DICT, dc=required_network.dc_0,
        cluster=required_network.cluster_0
    )

    assert helper.deactivate_hosts()


@pytest.fixture(scope="class")
def all_classes_teardown(request, requird_network_prepare_setup):
    """
    Teardown fixture for all cases
    """
    net = request.node.cls.net
    required_network = RequiredNetwork()

    def fin3():
        """
        Activate host if not up
        """
        hl_hosts.activate_host_if_not_up(host=required_network.host_0_name)
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove network from setup
        """
        if net:
            hl_networks.remove_net_from_setup(
                host=required_network.host_0_name,
                data_center=required_network.dc_0, network=[net]
            )
    request.addfinalizer(fin2)

    def fin1():
        """
        Set host NICs up if needed
        """
        for nic in required_network.host_0_nics[1:]:
            if "dummy" in nic:
                continue

            if not ll_hosts.check_host_nic_status(
                host_resource=conf.VDS_0_HOST, nic=nic,
                status=required_conf.NIC_STATE_UP
            ):
                assert conf.VDS_0_HOST.network.if_up(nic=nic)
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def case_02_fixture(request, all_classes_teardown):
    """
    Fixture for case02:
    Attach required non-VM network to host
    """
    required_network = RequiredNetwork()
    net = request.node.cls.net

    local_dict = {
        net: {
            "nic": 1,
        }
    }

    assert hl_networks.createAndAttachNetworkSN(
        host=required_network.vds_0_host, network_dict=local_dict,
        auto_nics=[0]
    )


@pytest.fixture(scope="class")
def case_03_fixture(request, all_classes_teardown):
    """
    Attach required network over BOND.
    """
    required_network = RequiredNetwork()
    net = request.node.cls.net
    bond = request.node.cls.bond
    vlan = request.node.cls.vlan

    local_dict = {
        None: {
            "nic": bond,
            "slaves": [2, 3]
        },
        net: {
            "nic": bond,
            "vlan_id": vlan
        }
    }

    assert hl_networks.createAndAttachNetworkSN(
        host=required_network.vds_0_host, network_dict=local_dict,
        auto_nics=[0]
    )
