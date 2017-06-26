#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures for acquire connections created by NetworkManager
"""

import pytest

import helper as nm_helper
from rhevmtests.networking import config as conf, helper
from art.unittest_lib import testflow


@pytest.fixture()
def nmcli_create_networks(request):
    """
    Create networks on host via nmcli (NetworkManager)
    """
    nic_type = request.getfixturevalue("type_")
    network = request.getfixturevalue("connection")
    vlan_id = request.getfixturevalue("vlan_id")
    host_nics = (
        [conf.HOST_0_NICS[1]] if nic_type == "nic" else conf.HOST_0_NICS[1:3]
    )

    def fin():
        """
        Clean all NetworkManager networks from the host
        """
        assert helper.network_manager_remove_all_connections(
            host=conf.VDS_0_HOST
        )
    request.addfinalizer(fin)

    testflow.setup("Remove existing NetworkManager connections")
    nm_helper.remove_nm_controlled(nics=host_nics)
    testflow.setup("Reload NetworkManager")
    nm_helper.reload_nm()

    if nic_type == "bond":
        testflow.setup("Create BOND via NetworkManager")
        nm_helper.create_bond_connection(nics=host_nics, vlan_id=vlan_id)
    else:
        testflow.setup("Create connection via NetworkManager")
        nm_helper.create_eth_connection(
            nic_type=nic_type, nics=host_nics, vlan_id=vlan_id,
            connection=network
        )
