#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures for acquire connections created by NetworkManager
"""

import re
import shlex
from art.unittest_lib import testflow
import pytest

import helper as nm_helper
from rhevmtests.networking import fixtures


@pytest.fixture()
def nmcli_create_networks(request):
    """
    Create networks on host via nmcli (NetworkManager)
    """
    nm_networks = fixtures.NetworkFixtures()
    nic_type = request.getfixturevalue("type_")
    network = request.getfixturevalue("connection")
    vlan_id = request.getfixturevalue("vlan_id")
    host_nics = (
        [nm_networks.host_0_nics[1]] if
        nic_type == "nic" else
        nm_networks.host_0_nics[1:3]
    )

    def fin():
        """
        Clean all NetworkManager networks from the host
        """
        all_connections = "nmcli connection show"
        delete_cmd = "nmcli connection delete {uuid}"
        rc, out, _ = nm_networks.vds_0_host.run_command(
            command=shlex.split(all_connections)
        )
        assert not rc
        for match in re.findall(r'\w+-\w+-\w+-\w+-\w+', out):
            testflow.teardown(
                "Remove connection %s from NetworkManager", match
            )
            nm_networks.vds_0_host.run_command(
                command=shlex.split(delete_cmd.format(uuid=match))
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
