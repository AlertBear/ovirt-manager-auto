#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Host Network API
Test via host NIC href
Test via host href
Test via SetupNetworks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import config as net_api_conf
import helper as host_net_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.network_custom_properties.config as cust_prop_conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import create_networks, remove_network
from rhevmtests.networking.fixtures import (
    setup_networks_fixture,
    clean_host_interfaces  # flake8: noqa
)


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApi01(NetworkTest):
    """
    All tests are done via Host,HostNic and SetupNetworks API

    1) Attach network to host NIC.
    2) Attach VLAN network to host NIC.
    3) Attach Non-VM network to host NIC.
    4) Attach Non-VM VLAN network to host NIC.
    """

    # General
    vm_type = "VM network"
    vlan_type = "VLAN network"
    non_vm_type = "Non-VM network"
    non_vm_vlan_type = "Non-VM VLAN network"

    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_01_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # HostNic
    net_1 = net_api_conf.NETS[1][0]
    net_2 = net_api_conf.NETS[1][1]
    net_3 = net_api_conf.NETS[1][2]
    net_4 = net_api_conf.NETS[1][3]
    # Host
    net_5 = net_api_conf.NETS[1][4]
    net_6 = net_api_conf.NETS[1][5]
    net_7 = net_api_conf.NETS[1][6]
    net_8 = net_api_conf.NETS[1][7]
    # SetupNetworks
    net_9 = net_api_conf.NETS[1][8]
    net_10 = net_api_conf.NETS[1][9]
    net_11 = net_api_conf.NETS[1][10]
    net_12 = net_api_conf.NETS[1][11]

    # clean_host_interfaces fixture
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @pytest.mark.parametrize(
        ("network", "nic", "type_", "via"),
        [
            polarion("RHEVM3-9601")([net_1, 1, vm_type, "host_nic"]),
            polarion("RHEVM3-9619")([net_2, 2, vlan_type, "host_nic"]),
            polarion("RHEVM3-9618")([net_3, 3, non_vm_type, "host_nic"]),
            polarion("RHEVM3-9620")([net_4, 4, non_vm_vlan_type, "host_nic"]),
            polarion("RHEVM3-10456")([net_5, 5, vm_type, "host"]),
            polarion("RHEVM3-10458")([net_6, 6, vlan_type, "host"]),
            polarion("RHEVM3-10457")([net_7, 7, non_vm_type, "host"]),
            polarion("RHEVM3-10459")([net_8, 8, non_vm_vlan_type, "host"]),
            polarion("RHEVM3-10470")([net_9, 9, vm_type, "sn"]),
            polarion("RHEVM3-10472")([net_10, 10, vlan_type, "sn"]),
            polarion("RHEVM3-10471")([net_11, 11, non_vm_type, "sn"]),
            polarion("RHEVM3-10473")([net_12, 12, non_vm_vlan_type, "sn"]),
        ]
    )
    def test_attach_network_to_nic(self, network, nic, type_, via):
        """
        Attach network to NIC via Host/HostNic and SetupNetworks API
        """
        host_nic = conf.HOST_0_NICS[nic]
        log_ = (
            "Attach network %s (%s) to host NIC %s via %s" %
            (network, type_, host_nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=host_nic, via=via, log_=log_
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApi02(NetworkTest):
    """
    All tests are done via Host,HostNic and SetupNetworks API

    1) Attach network with IP (netmask) to host NIC.
    2) Attach network with IP (prefix) to host NIC.
    3) Attach VLAN network with IP (netmask) to host NIC
    4) Attach VLAN network with IP (prefix) to host NIC
    5) Attach Non-VM network with IP (netmask) to host NIC.
    6) Attach Non-VM network with IP (prefix) to host NIC.
    7) Attach Non-VM VLAN network with IP (netmask) to host NIC.
    8) Attach Non-VM VLAN network with IP (prefix) to host NIC.
    """

    # General
    vm_type = "VM network"
    vlan_type = "VLAN network"
    non_vm_type = "Non-VM network"
    non_vm_vlan_type = "Non-VM VLAN network"

    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_02_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # HostNic
    net_1 = net_api_conf.NETS[2][0]
    ip_mask_net_1 = net_api_conf.IPS.pop(0)
    net_2 = net_api_conf.NETS[2][1]
    ip_prefix_net_2 = net_api_conf.IPS.pop(0)
    net_3 = net_api_conf.NETS[2][2]
    ip_mask_net_3 = net_api_conf.IPS.pop(0)
    net_4 = net_api_conf.NETS[2][3]
    ip_prefix_net_4 = net_api_conf.IPS.pop(0)
    net_5 = net_api_conf.NETS[2][4]
    ip_mask_net_5 = net_api_conf.IPS.pop(0)
    net_6 = net_api_conf.NETS[2][5]
    ip_prefix_net_6 = net_api_conf.IPS.pop(0)
    net_7 = net_api_conf.NETS[2][6]
    ip_mask_net_7 = net_api_conf.IPS.pop(0)
    net_8 = net_api_conf.NETS[2][7]
    ip_prefix_net_8 = net_api_conf.IPS.pop(0)
    # parametrize (Network, NIC, IP, network type, Use API via)
    nic_mask_vm = [net_1, 1, ip_mask_net_1, vm_type, "host_nic"]
    nic_pre_vm = [net_2, 2, ip_prefix_net_2, vm_type, "host_nic"]
    nic_mask_vlan = [net_3, 3, ip_mask_net_3, vlan_type, "host_nic"]
    nic_pre_vlan = [net_4, 4, ip_prefix_net_4, vlan_type, "host_nic"]
    nic_mask_non_vm = [net_5, 5, ip_mask_net_5, non_vm_type, "host_nic"]
    nic_pre_non_vm = [net_6, 6, ip_prefix_net_6, non_vm_type, "host_nic"]
    nic_mask_non_vm_vlan = [
        net_7, 7, ip_mask_net_7, non_vm_vlan_type, "host_nic"
    ]
    nic_pre_non_vm_vlan = [
        net_8, 8, ip_prefix_net_8, non_vm_vlan_type, "host_nic"
    ]
    # Host
    net_9 = net_api_conf.NETS[2][8]
    ip_mask_net_9 = net_api_conf.IPS.pop(0)
    net_10 = net_api_conf.NETS[2][9]
    ip_prefix_net_10 = net_api_conf.IPS.pop(0)
    net_11 = net_api_conf.NETS[2][10]
    ip_mask_net_11 = net_api_conf.IPS.pop(0)
    net_12 = net_api_conf.NETS[2][11]
    ip_prefix_net_12 = net_api_conf.IPS.pop(0)
    net_13 = net_api_conf.NETS[2][12]
    ip_mask_net_13 = net_api_conf.IPS.pop(0)
    net_14 = net_api_conf.NETS[2][13]
    ip_prefix_net_14 = net_api_conf.IPS.pop(0)
    net_15 = net_api_conf.NETS[2][14]
    ip_mask_net_15 = net_api_conf.IPS.pop(0)
    net_16 = net_api_conf.NETS[2][15]
    ip_prefix_net_16 = net_api_conf.IPS.pop(0)
    # parametrize (Network, NIC, IP, network type, Use API via)
    host_mask_vm = [net_9, 9, ip_mask_net_9, vm_type, "host"]
    host_pre_vm = [net_10, 10, ip_prefix_net_10, vm_type, "host"]
    host_mask_vlan = [net_11, 11, ip_mask_net_11, vlan_type, "host"]
    host_pre_vlan = [net_12, 12, ip_prefix_net_12, vlan_type, "host"]
    host_mask_non_vm = [net_13, 13, ip_mask_net_13, non_vm_type, "host"]
    host_pre_non_vm = [net_14, 14, ip_prefix_net_14, non_vm_type, "host"]
    host_mask_non_vm_vlan = [
        net_15, 15, ip_mask_net_15, non_vm_vlan_type, "host"
    ]
    host_pre_non_vm_vlan = [
        net_16, 16, ip_prefix_net_16, non_vm_vlan_type, "host"
    ]
    # SetupNetwork
    net_17 = net_api_conf.NETS[2][16]
    ip_mask_net_17 = net_api_conf.IPS.pop(0)
    net_18 = net_api_conf.NETS[2][17]
    ip_prefix_net_18 = net_api_conf.IPS.pop(0)
    net_19 = net_api_conf.NETS[2][18]
    ip_mask_net_19 = net_api_conf.IPS.pop(0)
    net_20 = net_api_conf.NETS[2][19]
    ip_prefix_net_20 = net_api_conf.IPS.pop(0)
    net_21 = net_api_conf.NETS[2][20]
    ip_mask_net_21 = net_api_conf.IPS.pop(0)
    net_22 = net_api_conf.NETS[2][21]
    ip_prefix_net_22 = net_api_conf.IPS.pop(0)
    net_23 = net_api_conf.NETS[2][22]
    ip_mask_net_23 = net_api_conf.IPS.pop(0)
    net_24 = net_api_conf.NETS[2][23]
    ip_prefix_net_24 = net_api_conf.IPS.pop(0)
    # parametrize (Network, NIC, IP, network type, Use API via)
    sn_mask_vm = [net_17, 17, ip_mask_net_17, vm_type, "sn"]
    sn_pre_vm = [net_18, 18, ip_prefix_net_18, vm_type, "sn"]
    sn_mask_vlan = [net_19, 19, ip_mask_net_19, vlan_type, "sn"]
    sn_pre_vlan = [net_20, 20, ip_prefix_net_20, vlan_type, "sn"]
    sn_mask_non_vm = [net_21, 21, ip_mask_net_21, non_vm_type, "sn"]
    sn_pre_non_vm = [net_22, 22, ip_prefix_net_22, non_vm_type, "sn"]
    sn_mask_non_vm_vlan = [
        net_23, 23, ip_mask_net_23, non_vm_vlan_type, "sn"
    ]
    sn_pre_non_vm_vlan = [
        net_24, 24, ip_prefix_net_24, non_vm_vlan_type, "sn"
    ]
    network_netmask = [
        net_1, net_3, net_5, net_7, net_9, net_11, net_13, net_15,
        net_17, net_19, net_21, net_23
    ]
    network_prefix = [
        net_2, net_4, net_6, net_8, net_10, net_12, net_14, net_16,
        net_18, net_20, net_22, net_24
    ]

    # clean_host_interfaces fixture
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @pytest.mark.parametrize(
        ("network", "nic", "ip", "type_", "via"),
        [
            polarion("RHEVM3-10446")(nic_mask_vm),
            polarion("RHEVM3-19101")(nic_pre_vm),
            polarion("RHEVM3-10447")(nic_mask_vlan),
            polarion("RHEVM3-19102")(nic_pre_vlan),
            polarion("RHEVM3-10448")(nic_mask_non_vm),
            polarion("RHEVM3-19103")(nic_pre_non_vm),
            polarion("RHEVM3-10449")(nic_mask_non_vm_vlan),
            polarion("RHEVM3-19104")(nic_pre_non_vm_vlan),

            polarion("RHEVM3-10460")(host_mask_vm),
            polarion("RHEVM3-19106")(host_pre_vm),
            polarion("RHEVM3-10461")(host_mask_vlan),
            polarion("RHEVM3-19107")(host_pre_vlan),
            polarion("RHEVM3-10462")(host_mask_non_vm),
            polarion("RHEVM3-19108")(host_pre_non_vm),
            polarion("RHEVM3-10463")(host_mask_non_vm_vlan),
            polarion("RHEVM3-19109")(host_pre_non_vm_vlan),

            polarion("RHEVM3-10474")(sn_mask_vm),
            polarion("RHEVM3-19111")(sn_pre_vm),
            polarion("RHEVM3-10475")(sn_mask_vlan),
            polarion("RHEVM3-19112")(sn_pre_vlan),
            polarion("RHEVM3-10476")(sn_mask_non_vm),
            polarion("RHEVM3-19113")(sn_pre_non_vm),
            polarion("RHEVM3-10477")(sn_mask_non_vm_vlan),
            polarion("RHEVM3-19114")(sn_pre_non_vm_vlan),
        ]
    )
    def test_attach_network_with_ip_to_nic(
        self, network, nic, ip, type_, via
    ):
        """
        Attach network with IP to NIC via Host/HostNic and SetupNetworks API
        """
        to_log = ""
        ip_to_add = None
        host_nic = conf.HOST_0_NICS[nic]
        if network in self.network_netmask:
            net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip
            ip_to_add = net_api_conf.BASIC_IP_DICT_NETMASK
            to_log = "(netmask)"

        if network in self.network_prefix:
            net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = ip
            ip_to_add = net_api_conf.BASIC_IP_DICT_PREFIX
            to_log = "(prefix)"

        log_ = (
            "Attach network %s (%s) with IP %s %s to host NIC %s via %s" %
            (network, type_, ip, to_log, host_nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=host_nic, ip=ip_to_add, log_=log_, via=via
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks.__name__,
    setup_networks_fixture.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApi03(NetworkTest):
    """
    All tests are done via Host,HostNic and SetupNetworks API

    1) Attach network with custom properties to NIC
    """
    # General
    bond_1 = "bond01"

    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_03_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # HostNic
    net_1 = net_api_conf.NETS[3][0]
    # Host
    net_2 = net_api_conf.NETS[3][1]
    # SetupNetworks
    net_3 = net_api_conf.NETS[3][2]

    # setup_networks_fixture fixture
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
               "nic": bond_1,
               "slaves": [-1, -2]
            }
        }
    }

    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            polarion("RHEVM3-10450")([net_1, 1, "host_nic"]),
            polarion("RHEVM3-10464")([net_2, 2, "host"]),
            polarion("RHEVM3-11880")([net_3, bond_1, "sn"]),
        ]
    )
    def test_network_custom_properties_on_nic(self, network, nic, via):
        """
        Attach network with custom properties to host NIC
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        properties_dict = {
            "bridge_opts": cust_prop_conf.PRIORITY,
            "ethtool_opts": cust_prop_conf.TX_CHECKSUM.format(
                nic=host_nic, state="off"
            )
        }
        log_ = (
            "Attach network %s with custom properties %s to NIC %s via %s" %
            (network, properties_dict, host_nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=host_nic, via=via, log_=log_
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_networks.__name__,
    setup_networks_fixture.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApi04(NetworkTest):
    """
    All tests are done via Host,HostNic and SetupNetworks API

    1) Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    2) Remove network from host NIC
    """
    # General
    net_4 = net_api_conf.NETS[4][3]

    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_04_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # setup_networks_fixture fixture
    net_1 = net_api_conf.NETS[4][0]
    net_2 = net_api_conf.NETS[4][1]
    net_3 = net_api_conf.NETS[4][2]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 2,
                "network": net_2
            },
            net_3: {
                "nic": 3,
                "network": net_3
            }
        }
    }

    @pytest.mark.parametrize(
        ("nic", "via"),
        [
            polarion("RHEVM3-10451")([1, "host_nic"]),
            polarion("RHEVM3-10465")([2, "host"]),
            polarion("RHEVM3-10513")([3, "sn"]),
        ]
    )
    def test_01_mtu_negative(self, nic, via):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        host_nic = conf.HOST_0_NICS[nic]
        log_ = (
            "Negative: Attach network %s to host NIC %s via %s when MTU is "
            "not the same as existing network on the NIC" % (
                self.net_4, host_nic, via
            )
        )
        host_net_helper.attach_networks_for_parametrize(
            network=self.net_4, nic=host_nic, via=via, log_=log_,
            positive=False
        )

    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            polarion("RHEVM3-10452")([net_1, 1, "host_nic"]),
            polarion("RHEVM3-10466")([net_2, 2, "host"]),
            polarion("RHEVM3-10514")([net_3, 3, "sn"]),
        ]
    )
    def test_02_remove_network_from_host(self, network, nic, via):
        """
        Remove network from host NIC
        """
        host_nic = conf.HOST_0_NICS[nic]
        log_ = (
            "Remove network %s from host NIC %s via %s" %
            (network, host_nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=host_nic, via=via, log_=log_, remove=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks.__name__,
    setup_networks_fixture.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApi05(NetworkTest):
    """
    All tests are done via Host,HostNic and SetupNetworks API

    1) Update the network to have IP (netmask).
    2) Update the network to have IP (prefix).
    3) Attach network to BOND.
    4) Delete 2 networks from the BOND.
    5) Attach network with custom properties to BOND.
    """

    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_05_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # test_attach_network_on_bond_nic params
    # HostNic
    net_5 = net_api_conf.NETS[5][4]
    # Host
    net_6 = net_api_conf.NETS[5][5]
    # SetupNetworks
    net_7 = net_api_conf.NETS[5][6]

    # test_update_network_with_ip_nic params
    # HostNic
    host_nic_ip_mask = net_api_conf.IPS.pop(0)
    host_nic_ip_pre = net_api_conf.IPS.pop(0)
    # Host
    host_ip_mask = net_api_conf.IPS.pop(0)
    host_ip_pre = net_api_conf.IPS.pop(0)
    # SetupNetworks
    sn_ip_mask = net_api_conf.IPS.pop(0)
    sn_ip_pre = net_api_conf.IPS.pop(0)
    netmask_ips = [host_nic_ip_mask, host_ip_mask, sn_ip_mask]
    prefix_ips = [host_nic_ip_pre, host_ip_pre, sn_ip_pre]

    # setup_networks_fixture fixture
    net_1 = net_api_conf.NETS[5][0]
    net_2 = net_api_conf.NETS[5][1]
    net_3 = net_api_conf.NETS[5][2]
    net_4 = net_api_conf.NETS[5][3]

    bond_1 = "bond51"
    bond_2 = "bond52"
    bond_3 = "bond53"
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            },
            net_2: {
                "nic": bond_2,
                "slaves": [-3, -4],
                "network": net_2
            },
            net_3: {
                "nic": bond_2,
                "network": net_3
            },
            net_4: {
                "nic": bond_2,
                "network": net_4
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [-5, -6]
            },
        }
    }

    net_list_to_remove = [net_2, net_3]

    @pytest.mark.parametrize(
        ("ip", "via"),
        [
            polarion("RHEVM3-10453")([host_nic_ip_mask, "host_nic"]),
            polarion("RHEVM3-19116")([host_nic_ip_pre, "host_nic"]),
            polarion("RHEVM3-10467")([host_ip_pre, "host"]),
            polarion("RHEVM3-19115")([host_ip_pre, "host"]),
            polarion("RHEVM3-10515")([sn_ip_pre, "sn"]),
            polarion("RHEVM3-19110")([sn_ip_pre, "sn"]),
        ]
    )
    def test_update_network_with_ip_nic(self, ip, via):
        """
        Update the network to have IP
        """
        to_log = ""
        ip_to_add = None
        host_nic = conf.HOST_0_NICS[1]
        if ip in self.netmask_ips:
            net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip
            ip_to_add = net_api_conf.BASIC_IP_DICT_NETMASK
            to_log = "(netmask)"

        if ip in self.prefix_ips:
            net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = ip
            ip_to_add = net_api_conf.BASIC_IP_DICT_PREFIX
            to_log = "(prefix)"

        log_ = (
            "Update network %s with IP %s %s to host NIC %s via %s" %
            (self.net_1, ip, to_log, host_nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=self.net_1, nic=host_nic, via=via, log_=log_,
            ip=ip_to_add, update=True
        )

    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            polarion("RHEVM3-10454")([net_5, bond_1, "host_nic"]),
            polarion("RHEVM3-10468")([net_6, bond_1, "host"]),
            polarion("RHEVM3-10516")([net_7, bond_1, "sn"]),
        ]
    )
    def test_attach_network_on_bond_nic(self, network, nic, via):
        """
        Attach network on BOND
        """
        log_ = (
            "Attach network %s to host NIC %s via %s" % (network, nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=nic, via=via, log_=log_
        )

    @pytest.mark.parametrize(
        ("network", "via"),
        [
            polarion("RHEVM3-10455")([net_2, "host_nic"]),
            polarion("RHEVM3-10469")([net_3, "host"]),
            polarion("RHEVM3-10517")([net_4, "sn"]),
        ]
    )
    def test_remove_networks_from_bond(self, network, via):
        """
        Remove 2 networks (VLAN and Non-VM) from host NIC
        """
        log_ = (
            "Remove network %s from the BOND %s via %s" %
            (network, self.bond_2, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=self.bond_2, via=via, log_=log_, remove=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks.__name__,
    setup_networks_fixture.__name__,
    remove_network.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApiHost06(NetworkTest):
    """
    All tests are done via Host and SetupNetworks API

    1) Remove the un-managed network from NIC
    2) Remove the un-managed network from BOND
    """

    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_06_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # test_remove_un_managed_network params
    net_1 = net_api_conf.NETS[6][0]
    net_2 = net_api_conf.NETS[6][1]
    net_3 = net_api_conf.NETS[6][2]
    net_4 = net_api_conf.NETS[6][3]
    bond_1 = "bond041"
    bond_2 = "bond042"

    # remove_network params
    nets_to_remove = [net_1, net_2, net_3, net_4]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2],
                "network": net_2
            },
            net_3: {
                "nic": 2,
                "network": net_3
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-3, -4],
                "network": net_4
            },
        }
    }

    @pytest.mark.parametrize(
        ("network", "via"),
        [
            polarion("RHEVM3-12165")([net_1, "host"]),
            polarion("RHEVM3-12166")([net_2, "host"]),
            polarion("RHEVM3-11432")([net_3, "sn"]),
            polarion("RHEVM3-12164")([net_4, "sn"]),
        ]
    )
    def test_remove_un_managed_network(self, network, via):
        """
        Remove the un-managed network from host
        """
        host_0 = conf.HOST_0_NAME
        testflow.step(
            "Get un-managed network %s object from host %s via %s",
            network, host_0, via
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host_name=host_0, networks=[network]
        )
        testflow.step(
            "Remove the un-managed network %s from host %s via %s", network,
            host_0, via
        )
        if via == "host":
            assert ll_host_network.remove_unmanaged_networks(
                host_name=host_0, networks=[network]
            )
        if via == "sn":
            sn_dict = {
                "remove": {
                    "networks": [network]
                }
            }
            assert hl_host_network.setup_networks(
                host_name=host_0, **sn_dict
            )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetworkApi07(NetworkTest):
    """
    All tests are done via Host and SetupNetworks API

    1) Attach VM network to host NIC that has VLAN network on it
    2) Attach VLAN network to host NIC that has VM network on it
    """
    # create_networks params
    networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_07_DICT,
            "datacenter": conf.DC_0,
            "cluster": conf.CL_0,
        }
    }

    # test_attach_network_to_nic_mixed params
    net_vlan_host = net_api_conf.NETS[7][8]
    net_vm_host = net_api_conf.NETS[7][9]
    net_vlan_sn = net_api_conf.NETS[7][10]
    net_vm_sn = net_api_conf.NETS[7][11]
    net_vlan_host_bond = net_api_conf.NETS[7][12]
    net_vm_host_bond = net_api_conf.NETS[7][13]
    net_vlan_sn_bond = net_api_conf.NETS[7][14]
    net_vm_sn_bond = net_api_conf.NETS[7][15]

    # setup_networks_fixture params
    net_1 = net_api_conf.NETS[7][0]
    net_2 = net_api_conf.NETS[7][1]
    net_3 = net_api_conf.NETS[7][2]
    net_4 = net_api_conf.NETS[7][3]
    net_5 = net_api_conf.NETS[7][4]
    net_6 = net_api_conf.NETS[7][5]
    net_7 = net_api_conf.NETS[7][6]
    net_8 = net_api_conf.NETS[7][7]
    bond_1 = "bond071"
    bond_2 = "bond072"
    bond_3 = "bond073"
    bond_4 = "bond074"
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 2,
                "network": net_2
            },
            net_3: {
                "nic": 3,
                "network": net_3
            },
            net_4: {
                "nic": 4,
                "network": net_4
            },
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2],
                "network": net_5
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-3, -4],
                "network": net_6
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [-5, -6],
                "network": net_7
            },
            bond_4: {
                "nic": bond_4,
                "slaves": [-7, -8],
                "network": net_8
            },
        }
    }

    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            polarion("RHEVM3-19120")([net_vlan_host, 1, "host"]),
            polarion("RHEVM3-19121")([net_vm_host, 2, "host"]),
            polarion("RHEVM3-14016")([net_vlan_sn, 3, "sn"]),
            polarion("RHEVM3-14015")([net_vm_sn, 4, "sn"]),
            polarion("RHEVM3-19122")([net_vlan_host_bond, bond_1, "host"]),
            polarion("RHEVM3-19123")([net_vm_host_bond, bond_2, "host"]),
            polarion("RHEVM3-14019")([net_vlan_sn_bond, bond_3, "sn"]),
            polarion("RHEVM3-14018")([net_vm_sn_bond, bond_4, "sn"]),
        ]
    )
    def test_attach_network_to_nic_mixed(self, network, nic, via):
        """
        Attach VLAN network to host NIC that has VM network on it
        Attach VM network to host NIC that has VLAN network on it
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        log_ = (
            "Attach network %s to host NIC %s via %s" %
            (network, host_nic, via)
        )
        host_net_helper.attach_networks_for_parametrize(
            network=network, nic=host_nic, via=via, log_=log_
        )
