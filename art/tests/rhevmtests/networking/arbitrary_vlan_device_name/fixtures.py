#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for arbitrary_vlan_device_name
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.config as conf
import helper
import rhevmtests.networking.helper as net_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class ArbitraryVlanDeviceName(NetworkFixtures):
    """
    arbitrary_vlan_device_name class for fixtures
    """
    def __init__(self):
        super(ArbitraryVlanDeviceName, self).__init__()
        self.vlan_name_1 = conf.VLAN_NAMES[0]
        self.vlan_id_1 = conf.VLAN_IDS[0]
        self.bridge_name_1 = conf.BRIDGE_NAMES[0]
        self.bond = conf.BOND[0]
        self.vlan_names = conf.VLAN_NAMES
        self.vlan_ids = conf.VLAN_IDS
        self.bridge_names = conf.BRIDGE_NAMES
        self.vlan_network_1 = conf.VLAN_NETWORKS[0]
        self.network_name_1 = conf.NETWORKS[0]
        self.real_vln_id = conf.VLAN_ID[0]

    def create_vlans_on_host(self, nic=1, vlan_id=None, vlan_name=None):
        """
        Add VLANs on host
        """
        vlan_id = [self.vlan_id_1] if not vlan_id else vlan_id
        vlan_name = [self.vlan_name_1] if not vlan_name else vlan_name
        return helper.add_vlans_to_host(
            host_obj=conf.VDS_0_HOST, nic=nic, vlan_id=vlan_id,
            vlan_name=vlan_name
        )

    def create_bridges_on_host_and_virsh(self, bridge=None, network=None):
        """
        Add bridge_names on host
        """
        bridge = [self.bridge_name_1] if not bridge else bridge
        network = [self.vlan_name_1] if not network else network
        return helper.add_bridge_on_host_and_virsh(
            host_obj=conf.VDS_0_HOST, bridge=bridge, network=network
        )


@pytest.fixture(scope="module")
def avdn_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    avdn = ArbitraryVlanDeviceName()
    assert net_helper.set_virsh_sasl_password(vds_resource=avdn.vds_0_host)


@pytest.fixture(scope="class")
def all_cases_teardown(request):
    """
    Teardown for all cases
    """
    def fin():
        """
        Finalizer for remove all networks from host
        """
        helper.job_tear_down()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case_01_fixture(request, all_cases_teardown, avdn_prepare_setup):
    """
    Create VLAN entity with name on the host
    """
    avdn = ArbitraryVlanDeviceName()
    assert avdn.create_vlans_on_host()
    assert avdn.create_bridges_on_host_and_virsh()


@pytest.fixture(scope="class")
def case_02_fixture(request, all_cases_teardown, avdn_prepare_setup):
    """
    Create empty BOND via SetupNetworks
    Create VLAN entity with name on the host
    """
    avdn = ArbitraryVlanDeviceName()
    network_host_api_dict = {
        "add": {
            "1": {
                "nic": avdn.bond,
                "slaves": conf.HOST_0_NICS[2:4]
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=conf.HOST_0_NAME, **network_host_api_dict
    )
    assert avdn.create_vlans_on_host(nic=avdn.bond)
    assert avdn.create_bridges_on_host_and_virsh()


@pytest.fixture(scope="class")
def case_03_fixture(request, all_cases_teardown, avdn_prepare_setup):
    """
    Create VLAN entity with name on the host
    """
    avdn = ArbitraryVlanDeviceName()
    assert avdn.create_vlans_on_host(
        vlan_id=avdn.vlan_ids, vlan_name=avdn.vlan_names
    )
    assert avdn.create_bridges_on_host_and_virsh(
        bridge=avdn.bridge_names, network=avdn.vlan_names
    )


@pytest.fixture(scope="class")
def case_04_fixture(request, all_cases_teardown, avdn_prepare_setup):
    """
    Create empty BOND
    Create VLAN entity with name on the host
    """
    avdn = ArbitraryVlanDeviceName()
    local_dict = {
        "add": {
            "1": {
                "nic": avdn.bond,
                "slaves": conf.HOST_0_NICS[2:4]
            },
        }
    }
    assert hl_host_network.setup_networks(
        host_name=conf.HOST_0_NAME, **local_dict
    )
    assert avdn.create_vlans_on_host(
        vlan_id=avdn.vlan_ids, vlan_name=avdn.vlan_names
    )
    assert avdn.create_bridges_on_host_and_virsh(
        bridge=avdn.bridge_names, network=avdn.vlan_names
    )


@pytest.fixture(scope="class")
def case_05_fixture(request, all_cases_teardown, avdn_prepare_setup):
    """
    Create VLAN on NIC via SetupNetworks
    Create VLAN entity with name on the host
    """
    avdn = ArbitraryVlanDeviceName()

    def fin():
        """
        Remove the VLAN from the setup
        """
        hl_networks.remove_all_networks(
            datacenter=avdn.dc_0, cluster=avdn.cluster_0
        )
    request.addfinalizer(fin)

    local_dict = {
        avdn.vlan_network_1: {
            "vlan_id": avdn.real_vln_id,
            "required": "false",
        },
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=avdn.dc_0, cluster=avdn.cluster_0, network_dict=local_dict
    )

    sn_dict = {
        "add": {
            "1": {
                "network": avdn.vlan_network_1,
                "nic": conf.HOST_0_NICS[1]
            }
        }
    }

    assert hl_host_network.setup_networks(
        host_name=conf.HOST_0_NAME, **sn_dict
    )
    assert avdn.create_vlans_on_host()
    assert avdn.create_bridges_on_host_and_virsh()


@pytest.fixture(scope="class")
def case_06_fixture(request, all_cases_teardown, avdn_prepare_setup):
    """
    Create Non-VM network on NIC via SetupNetworks
    Create VLAN entity with name on the host
    """
    avdn = ArbitraryVlanDeviceName()

    def fin():
        """
        Remove the network from the setup
        """
        hl_networks.remove_all_networks(
            datacenter=avdn.dc_0, cluster=avdn.cluster_0
        )
    request.addfinalizer(fin)

    local_dict = {
        avdn.network_name_1: {
            "vlan_id": avdn.real_vln_id,
            "required": "false",
            "usages": ""
        },
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=avdn.dc_0, cluster=avdn.cluster_0, network_dict=local_dict,
    )
    sn_dict = {
        "add": {
            "1": {
                "network": avdn.network_name_1,
                "nic": conf.HOST_0_NICS[1]
            }
        }
    }

    assert hl_host_network.setup_networks(
        host_name=conf.HOST_0_NAME, **sn_dict
    )
    assert avdn.create_vlans_on_host()
    assert avdn.create_bridges_on_host_and_virsh()
