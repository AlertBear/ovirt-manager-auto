# -*- coding: utf-8 -*-

"""
Fixtures for acquire connections created by NetworkManager
"""

import pytest

from art.rhevm_api.tests_lib.low_level import (
    events as ll_events,
    hosts as ll_hosts
)
from rhevmtests import fixtures_helper
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
from rhevmtests.networking import (
    config as network_config,
    helper as network_helper
)


@pytest.fixture()
def nmcli_create_networks(request):
    """
    Create networks on host via nmcli (NetworkManager)
    """
    nic_type = fixtures_helper.get_fixture_val(
        request=request, attr_name="type_"
    )
    vlan_id = fixtures_helper.get_fixture_val(
        request=request, attr_name="vlan_id"
    )
    host_resource = network_config.VDS_0_HOST
    host_nics = (
        [network_config.HOST_0_NICS[1]] if nic_type == "nic" else
        network_config.HOST_0_NICS[1:3]
    )

    def fin():
        """
        Clean all NetworkManager networks from the host
        """
        network_helper.network_manager_remove_all_connections(
            host=network_config.VDS_0_HOST
        )
    request.addfinalizer(fin)

    if nic_type == "bond":
        assert hl_networks.create_bond(
            bond="bond1", host_resource=host_resource, host_nics=host_nics,
            via="nm"
        )
    else:
        assert hl_networks.create_interface(
            host_resource=host_resource, interface=host_nics, vlan_id=vlan_id,
            via="nm"
        )

    last_event = ll_events.get_max_event_id()
    assert last_event
    assert ll_hosts.refresh_host_capabilities(
        host=network_config.HOST_0_NAME, start_event_id=last_event
    )
