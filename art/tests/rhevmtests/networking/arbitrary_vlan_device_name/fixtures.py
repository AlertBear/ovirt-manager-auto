#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for arbitrary_vlan_device_name
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def create_networks_on_engine(request):
    """
    Create networks on engine
    """
    arbitrary_vlan_device_name = NetworkFixtures()

    def fin():
        """
        Remove the VLAN from the setup
        """
        arbitrary_vlan_device_name.remove_networks_from_setup(
            hosts=arbitrary_vlan_device_name.host_0_name
        )
    request.addfinalizer(fin)

    arbitrary_vlan_device_name.prepare_networks_on_setup(
        networks_dict=conf.ARBITRARY_NET_DICT,
        dc=arbitrary_vlan_device_name.dc_0,
        cluster=arbitrary_vlan_device_name.cluster_0
    )


@pytest.fixture(scope="module")
def set_virsh_credentails_on_vds_host_0(request):
    """
    Set virsh credentails on vds host-0
    """
    arbitrary_vlan_device_name = NetworkFixtures()

    assert net_helper.set_virsh_sasl_password(
        vds_resource=arbitrary_vlan_device_name.vds_0_host
    )


@pytest.fixture(scope="class")
def create_vlans_and_bridges_on_host(
        request, set_virsh_credentails_on_vds_host_0
):
    """
    Fixtures for add VLANs and bridge names on host.
    """
    arbitrary_vlan_device_name = NetworkFixtures()
    vlan_ids = request.node.cls.vlan_ids
    vlan_names = request.node.cls.vlan_names
    nic = request.node.cls.nic
    bridge_names = request.node.cls.bridge_names

    def fin():
        """
        Finalizer for remove all networks from host
        """
        helper.job_tear_down()
    request.addfinalizer(fin)

    assert helper.add_vlans_to_host(
        host_obj=arbitrary_vlan_device_name.vds_0_host, nic=nic,
        vlan_id=vlan_ids, vlan_name=vlan_names
    )

    assert helper.add_bridge_on_host_and_virsh(
        host_obj=arbitrary_vlan_device_name.vds_0_host, bridge=bridge_names,
        network=vlan_names
    )


@pytest.fixture(scope="class")
def attach_network_to_host(request):
    """
    Fixture for create bond or attach network to host NICs
    """
    arbitrary_vlan_device_name = NetworkFixtures()
    nic = request.node.cls.nic
    network = request.node.cls.network
    sn_dict = {
        "add": {
            "1": {}
        }
    }
    if isinstance(nic, int):
        nic = arbitrary_vlan_device_name.host_0_nics[nic]
        sn_dict["add"]["1"]["network"] = network
    else:
        sn_dict["add"]["1"]["slaves"] = conf.HOST_0_NICS[2:4]

    sn_dict["add"]["1"]["nic"] = nic

    assert hl_host_network.setup_networks(
        host_name=arbitrary_vlan_device_name.host_0_name, **sn_dict
    )
