#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for misc
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def remove_all_networks(request):
    """
    Fixture for case01:
    """
    misc = NetworkFixtures()

    def fin():
        """
        Finalizer for remove all networks from the DC.
        """
        testflow.teardown("Remove all networks from datacenter %s", misc.dc_0)
        assert hl_networks.remove_all_networks(datacenter=misc.dc_0)
    request.addfinalizer(fin)
