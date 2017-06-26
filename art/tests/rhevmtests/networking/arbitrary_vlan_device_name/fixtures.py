#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for arbitrary_vlan_device_name
"""
import shlex

import pytest

import helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def create_vlans_on_host(request):
    """
    Add VLANs and bridge names on host.
    """
    param_list = request.node.cls.param_list
    vlan_name_list = request.node.cls.vlan_names
    vds_host = conf.VDS_0_HOST
    host_name = conf.HOST_0_NAME

    def fin():
        """
        Remove VLANs from host
        """
        ip_link_out = vds_host.run_command(shlex.split("ip link"))[1]
        vlans_to_remove = [v for v in vlan_name_list if v in ip_link_out]
        testflow.teardown(
            "Remove VLANs %s from host %s", vlans_to_remove, host_name
        )
        assert helper.remove_vlans_and_refresh_capabilities(
            host_obj=vds_host, vlans_names=vlans_to_remove
        )

    request.addfinalizer(fin)

    for nic, vlan_ids, vlan_names in param_list:
        testflow.setup("Create VLANs %s on host %s", vlan_names, vds_host)
        assert helper.add_vlans_to_host(
            host_obj=vds_host, nic=nic, vlan_id=vlan_ids, vlan_names=vlan_names
        )
    assert helper.refresh_host_capabilities(host=host_name)
