#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for topologies test
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture()
def update_vnic_network(request):
    """
    Update vNIC network on VM
    """
    net = request.getfixturevalue("network")
    if not net:
        return

    vm = conf.VM_0
    nic = conf.VM_NIC_0
    mgmt = conf.MGMT_BRIDGE

    def fin():
        """
        Update vNIC to management network
        """
        testflow.teardown("Update vNIC %s on VM %s to %s", nic, vm, mgmt)
        assert ll_vms.updateNic(
            positive=True, vm=vm, nic=nic, vnic_profile=mgmt, network=mgmt
        )
    request.addfinalizer(fin)

    testflow.setup("Update vNIC %s on VM %s to %s", nic, vm, net)
    assert ll_vms.updateNic(
        positive=True, vm=vm, nic=nic, vnic_profile=net, network=net
    )
