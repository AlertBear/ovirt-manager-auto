#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Bad Bond feature
"""

import pytest

from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts, events
import helper
import rhevmtests.networking.config as conf
from art.core_api import apis_utils


@pytest.fixture()
def get_linux_ad_partner_mac_value(request):
    """
    Get Linux ad_partner_mac MAC value of bond until get succeed, or timeout
        exceeded
    """

    bond_name = request.getfixturevalue("bond_name")
    host_index = request.getfixturevalue("host_index")

    sample = apis_utils.TimeoutingSampler(
        timeout=30, sleep=1, func=helper.get_bond_ad_partner_mac_in_linux,
        host_name=conf.HOSTS[host_index], bond_name=bond_name
    )
    assert sample.waitForFuncStatus(result=True)


@pytest.fixture()
def refresh_hosts_capabilities(request):
    """
    Refresh host(s) VDS capabilities
    """

    hosts_indexes = getattr(request.cls, "hosts_to_refresh", list())

    for host_idx in hosts_indexes:
        last_event = events.get_max_event_id()

        assert ll_hosts.refresh_host_capabilities(
            host=conf.HOSTS[host_idx], start_event_id=last_event
        )
