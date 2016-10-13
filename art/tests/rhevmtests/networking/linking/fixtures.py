#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Network Linking test cases
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def add_vnics_to_vms(request):
    """
    Add vNIC(s) with properties to a VM(s)
    """
    NetworkFixtures()
    vnic_props_list = request.node.cls.add_vnics_vms_params

    def fin():
        """
        Remove vNIC(s) from a VM(s)
        """
        for props in vnic_props_list:
            vm = props.get("vm")
            nic = props.get("name")
            testflow.teardown("Removing vNIC: %s from VM: %s", nic, vm)
            assert ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin)

    for props in vnic_props_list:
        testflow.setup(
            "Adding vNIC: %s to VM: %s", props.get("name"), props.get("vm")
        )
        assert ll_vms.addNic(positive=True, **props)


@pytest.fixture(scope="class")
def add_vnic_profile(request):
    """
    Add vNIC profile with properties
    """
    linking = NetworkFixtures()
    vnic_params = request.node.cls.add_vnic_profile_params
    name = vnic_params.get("name")
    cl = vnic_params.get("cluster", linking.cluster_0)
    net = vnic_params.get("network")
    pm = vnic_params.get("port_mirror", True)

    def fin():
        """
        Remove vNIC profile
        """
        testflow.teardown("Removing vNIC profile: %s", name)
        assert ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=name, network=net
        )
    request.addfinalizer(fin)

    testflow.setup("Adding vNIC profile: %s", name)
    assert ll_networks.add_vnic_profile(
        positive=True, name=name, cluster=cl, network=net, port_mirroring=pm
    )
