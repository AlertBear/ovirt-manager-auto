#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Check persistence networks after host reboot
"""
import pytest

import config as host_network_api_conf
import rhevmtests.networking.host_network_qos.helper as qos_helper
import rhevmtests.networking.multi_host.helper as multi_host_helper
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier3,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import reboot_host
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    reboot_host.__name__
)
class TestPersistenceSetupNetworks01(NetworkTest):
    """
    Check the VLAN, MTU and QoS are persistence on host NIC
    Check the VLAN, MTU and QoS are persistence on host BOND
    """
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": host_network_api_conf.PERSIST_NETS_CASE_1
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # test_01_persistence_network_on_host_nic params
    nic_net = host_network_api_conf.PERSIST_NETS[1][0]
    nic_vlan = (
        host_network_api_conf.PERSIST_NETS_CASE_1.get(nic_net).get("vlan_id")
    )
    test01_params = [nic_net, 1, nic_vlan]

    # test_02_persistence_network_on_host_bond params
    bond_net = host_network_api_conf.PERSIST_NETS[1][1]
    bond_vlan = (
        host_network_api_conf.PERSIST_NETS_CASE_1.get(bond_net).get("vlan_id")
    )
    bond = "bond10"

    # test_01 and test_02 params
    mtu_9000 = conf.MTU[0]
    qos_dict = {
        "rt": host_network_api_conf.QOS_VAL * 1000000,
        "ul": host_network_api_conf.QOS_VAL * 1000000,
        "ls": host_network_api_conf.QOS_VAL
    }

    test02_params = [bond_net, bond, bond_vlan]

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

    @tier3
    @pytest.mark.parametrize(
        ("network", "nic", "vlan"),
        [
            pytest.param(*test01_params, marks=(polarion("RHEVM3-19133"))),
            pytest.param(*test02_params, marks=(polarion("RHEVM3-19134"))),
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
