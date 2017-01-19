#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Bad Bond feature
"""

import pytest

import helper
import rhevmtests.networking.config as conf
from art.core_api import apis_utils
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture()
def get_linux_ad_partner_mac_value(request):
    """
    Get Linux ad_partner_mac MAC value of bond until get succeed, or timeout
        exceeded
    """
    NetworkFixtures()

    bond_name = request.getfixturevalue("bond_name")
    host_index = request.getfixturevalue("host_index")

    sample = apis_utils.TimeoutingSampler(
        timeout=30, sleep=1, func=helper.get_bond_ad_partner_mac_in_linux,
        host_name=conf.HOSTS[host_index], bond_name=bond_name
    )
    assert sample.waitForFuncStatus(result=True)
