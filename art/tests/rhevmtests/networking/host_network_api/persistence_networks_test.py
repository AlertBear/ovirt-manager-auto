#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Check persistence networks after host reboot
"""
import pytest

import config as host_network_api_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.host_network_qos.helper as qos_helper
import rhevmtests.networking.multi_host.helper as multi_host_helper
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import reboot_host
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces, NetworkFixtures
)  # flake8: noqa


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
        testflow.teardown("Remove all networks from engine")
        assert network_helper.remove_networks_from_setup(
            hosts=network_api.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup("Add networks to engine")
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
    __test__ = True
    bond = "bond10"
    nic_net = host_network_api_conf.PERSIST_NETS[1][0]
    bond_net = host_network_api_conf.PERSIST_NETS[1][1]
    nic_vlan = host_network_api_conf.VLAN_IDS[57]
    bond_vlan = host_network_api_conf.VLAN_IDS[58]
    mtu_9000 = conf.MTU[0]
    qos_dict = {
        "rt": host_network_api_conf.QOS_VAL * 1000000,
        "ul": host_network_api_conf.QOS_VAL * 1000000,
        "ls": host_network_api_conf.QOS_VAL
    }
    persist = True
    hosts_nets_nic_dict = {
        0: {
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

    def test_01_persistence_network_on_host_nic(self):
        """
        Check the VLAN, MTU and QoS are persistence on host NIC
        """
        host_nic = conf.HOST_0_NICS[1]
        testflow.step(
            "Check that MTU on host NIC %s is %s", host_nic, self.mtu_9000
        )
        multi_host_helper.check_mtu(
            net=self.nic_net, mtu=self.mtu_9000, nic=host_nic,
            host=conf.HOST_0_NAME, vds_host=conf.VDS_0_HOST
        )
        testflow.step(
            "Check that VLAN on host NIC %s is %s", host_nic, self.nic_vlan
        )
        multi_host_helper.check_vlan(
            net=self.nic_net, vlan=self.nic_vlan, nic=host_nic,
            host=conf.HOST_0_NAME, vds_host=conf.VDS_0_HOST
        )
        testflow.step(
            "Check that QOS on host NIC %s is %s", host_nic, self.qos_dict
        )
        assert qos_helper.cmp_qos_with_vdscaps(
            host_resource=conf.VDS_0_HOST, net=self.nic_net,
            qos_dict=self.qos_dict
        )

    def test_02_persistence_network_on_host_bond(self):
        """
        Check the VLAN, MTU and QoS are persistence on host BOND
        """
        testflow.step(
            "Check that MTU on host NIC %s is %s", self.bond, self.mtu_9000
        )
        multi_host_helper.check_mtu(
            net=self.bond_net, mtu=self.mtu_9000, nic=self.bond,
            host=conf.HOST_0_NAME, vds_host=conf.VDS_0_HOST
        )
        testflow.step(
            "Check that VLAN on host NIC %s is %s", self.bond, self.bond_vlan
        )
        multi_host_helper.check_vlan(
            net=self.bond_net, vlan=self.bond_vlan, nic=self.bond,
            host=conf.HOST_0_NAME, vds_host=conf.VDS_0_HOST
        )
        testflow.step(
            "Check that QOS on host NIC %s is %s", self.bond, self.qos_dict
        )
        assert qos_helper.cmp_qos_with_vdscaps(
            host_resource=conf.VDS_0_HOST, net=self.nic_net,
            qos_dict=self.qos_dict
        )
