#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Check persistence networks after host reboot
"""
import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import config as host_network_api_conf
import rhevmtests.networking.host_network_qos.helper as qos_helper
import rhevmtests.networking.multi_host.helper as multi_host_helper
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import reboot_host
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)
from rhevmtests.networking.fixtures import (
    NetworkFixtures, setup_networks_fixture
)


@pytest.fixture(scope="module", autouse=True)
def sn_prepare_setup(request):
    """
    Prepare setup for setup networks tests
    """
    network_api = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        assert hl_networks.remove_net_from_setup(
            host=conf.HOSTS[2], all_net=True,
            data_center=conf.DC_0
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=host_network_api_conf.PERSIST_NETS_DICT,
        dc=network_api.dc_0, cluster=network_api.cluster_0
    )


@attr(tier=3)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    reboot_host.__name__
)
class TestPersistenceSetupNetworks01(NetworkTest):
    """
    Check the VLAN, MTU and QoS are persistence on host NIC
    Check the VLAN, MTU and QoS are persistence on host BOND
    """
    # test_01_persistence_network_on_host_nic params
    nic_net = host_network_api_conf.PERSIST_NETS[1][0]
    nic_vlan = (
        host_network_api_conf.PERSIST_NETS_DICT.get(nic_net).get("vlan_id")
    )

    # test_02_persistence_network_on_host_bond params
    bond_net = host_network_api_conf.PERSIST_NETS[1][1]
    bond_vlan = (
        host_network_api_conf.PERSIST_NETS_DICT.get(bond_net).get("vlan_id")
    )
    bond = "bond10"

    # test_01 and test_02 params
    mtu_9000 = conf.MTU[0]
    qos_dict = {
        "rt": host_network_api_conf.QOS_VAL * 1000000,
        "ul": host_network_api_conf.QOS_VAL * 1000000,
        "ls": host_network_api_conf.QOS_VAL
    }

    # setup_networks_fixture params
    persist = True
    hosts_nets_nic_dict = {
        2: {
            nic_net: {
                "nic": 1,
                "network": nic_net,
                "qos": host_network_api_conf.QOS
            },
            bond_net: {
                "nic": bond,
                "slaves": [2, 3],
                "network": bond_net,
                "qos": host_network_api_conf.QOS
            }
        }
    }

    @pytest.mark.parametrize(
        ("network", "nic", "vlan"),
        [
            polarion("RHEVM3-19133")([nic_net, 1, nic_vlan]),
            polarion("RHEVM3-19134")([bond_net, bond, bond_vlan])
        ],
        ids=[
            "Check_persistence_network_on_host_NIC",
            "Check_persistence_network_on_host_BOND"
        ]
    )
    def test_host_persistence_networks(self, network, nic, vlan):
        """
        Check the VLAN, MTU and QoS are persistence on NIC
        Check the VLAN, MTU and QoS are persistence on BOND
        """
        host = conf.HOSTS[2]
        vds = conf.VDS_HOSTS[2]
        host_nic = vds.nics[nic] if isinstance(nic, int) else nic
        testflow.step(
            "Check that MTU on host NIC %s is %s", host_nic, self.mtu_9000
        )
        assert multi_host_helper.check_mtu(
            net=network, mtu=self.mtu_9000, nic=host_nic, host=host,
            vds_host=vds
        )
        testflow.step(
            "Check that VLAN on host NIC %s is %s", host_nic, vlan
        )
        assert multi_host_helper.check_vlan(
            net=network, vlan=vlan, nic=host_nic, host=host, vds_host=vds
        )
        testflow.step(
            "Check that QOS on host NIC %s is %s", host_nic, self.qos_dict
        )
        assert qos_helper.cmp_qos_with_vdscaps(
            host_resource=vds, net=network, qos_dict=self.qos_dict
        )
