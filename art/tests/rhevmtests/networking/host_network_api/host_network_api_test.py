# -*- coding: utf-8 -*-

"""
Tests for Host Network API
Test via host NIC href
Test via host href
Test via SetupNetworks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
from art.rhevm_api.tests_lib.low_level import (
    host_network as ll_host_network,
    hosts as ll_hosts
)
import config as net_api_conf
import helper as host_net_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.network_custom_properties.config as cust_prop_conf
from art.test_handler.tools import polarion
from fixtures import remove_network
from art.unittest_lib import (
    tier2,
    NetworkTest, testflow
)

from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_01_DICT,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # HostNic
    net_1 = net_api_conf.NETS[1][0]
    net_2 = net_api_conf.NETS[1][1]
    net_3 = net_api_conf.NETS[1][2]
    net_4 = net_api_conf.NETS[1][3]
    host_nic_vm_network = [net_1, 1, vm_type, "host_nic"]
    host_nic_vlan_network = [net_2, 2, vlan_type, "host_nic"]
    host_nic_non_vm_network = [net_3, 3, non_vm_type, "host_nic"]
    host_nic_non_vm_vlan_network = [net_4, 4, non_vm_vlan_type, "host_nic"]

    # Host
    net_5 = net_api_conf.NETS[1][4]
    net_6 = net_api_conf.NETS[1][5]
    net_7 = net_api_conf.NETS[1][6]
    net_8 = net_api_conf.NETS[1][7]
    host_vm_network = [net_5, 5, vm_type, "host"]
    host_vlan_network = [net_6, 6, vlan_type, "host"]
    host_non_vm_network = [net_7, 7, non_vm_type, "host"]
    host_non_vm_vlan_network = [net_8, 8, non_vm_vlan_type, "host"]

    # SetupNetworks
    net_9 = net_api_conf.NETS[1][8]
    net_10 = net_api_conf.NETS[1][9]
    net_11 = net_api_conf.NETS[1][10]
    net_12 = net_api_conf.NETS[1][11]
    sn_vm_network = [net_9, 9, vm_type, "sn"]
    sn_vlan_network = [net_10, 10, vlan_type, "sn"]
    sn_non_vm_network = [net_11, 11, non_vm_type, "sn"]
    sn_non_vm_vlan_network = [net_12, 12, non_vm_vlan_type, "sn"]

    # clean_host_interfaces fixture
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @tier2
    @pytest.mark.parametrize(
        ("network", "nic", "type_", "via"),
        [
            # Host NIC
            pytest.param(
                *host_nic_vm_network, marks=(polarion("RHEVM3-9601"))
            ),
            pytest.param(
                *host_nic_vlan_network, marks=(polarion("RHEVM3-9619"))
            ),
            pytest.param(
                *host_nic_non_vm_network, marks=(polarion("RHEVM3-9618"))
            ),
            pytest.param(
                *host_nic_non_vm_vlan_network, marks=(polarion("RHEVM3-9620"))
            ),

            # Host
            pytest.param(*host_vm_network, marks=(polarion("RHEVM3-10456"))),
            pytest.param(*host_vlan_network, marks=(polarion("RHEVM3-10458"))),
            pytest.param(
                *host_non_vm_network, marks=(polarion("RHEVM3-10457"))
            ),
            pytest.param(*host_non_vm_vlan_network, marks=(
                polarion("RHEVM3-10459")
                )
            ),

            # SetupNetwork
            pytest.param(*sn_vm_network, marks=(polarion("RHEVM3-10470"))),
            pytest.param(*sn_vlan_network, marks=(polarion("RHEVM3-10472"))),
            pytest.param(*sn_non_vm_network, marks=(polarion("RHEVM3-10471"))),
            pytest.param(
                *sn_non_vm_vlan_network, marks=(polarion("RHEVM3-10473"))
            )
        ],
        ids=[
            "Attach_VM_network_via_host_NIC",
            "Attach_VLAN_network_via_host_NIC",
            "Attach_Non-VM_network_via_host_NIC",
            "Attach_Non-VM_VLAN_network_via_host_NIC",
            "Attach_VM_network_via_host",
            "Attach_VLAN_network_via_host",
            "Attach_Non-VM_network_via_host_",
            "Attach_Non-VM_VLAN_network_via_host",
            "Attach_VM_network_via_sn",
            "Attach_VLAN_network_via_sn",
            "Attach_Non-VM_network_via_sn",
            "Attach_Non-VM_VLAN_network_via_sn",
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_02_DICT,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

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

    @tier2
    @pytest.mark.parametrize(
        ("network", "nic", "ip", "type_", "via"),
        [
            # Host NIC
            pytest.param(*nic_mask_vm, marks=(polarion("RHEVM3-10446"))),
            pytest.param(*nic_pre_vm, marks=(polarion("RHEVM3-19101"))),
            pytest.param(*nic_mask_vlan, marks=(polarion("RHEVM3-10447"))),
            pytest.param(*nic_pre_vlan, marks=(polarion("RHEVM3-19102"))),
            pytest.param(*nic_mask_non_vm, marks=(polarion("RHEVM3-10448"))),
            pytest.param(*nic_pre_non_vm, marks=(polarion("RHEVM3-19103"))),
            pytest.param(
                *nic_mask_non_vm_vlan, marks=(polarion("RHEVM3-10449"))
            ),
            pytest.param(
                *nic_pre_non_vm_vlan, marks=(polarion("RHEVM3-19104"))
            ),

            # Host
            pytest.param(*host_mask_vm, marks=(polarion("RHEVM3-10460"))),
            pytest.param(*host_pre_vm, marks=(polarion("RHEVM3-19106"))),
            pytest.param(*host_mask_vlan, marks=(polarion("RHEVM3-10461"))),
            pytest.param(*host_pre_vlan, marks=(polarion("RHEVM3-19107"))),
            pytest.param(*host_mask_non_vm, marks=(polarion("RHEVM3-10462"))),
            pytest.param(*host_pre_non_vm, marks=(polarion("RHEVM3-19108"))),
            pytest.param(
                *host_mask_non_vm_vlan, marks=(polarion("RHEVM3-10463"))
            ),
            pytest.param(
                *host_pre_non_vm_vlan, marks=(polarion("RHEVM3-19109"))
            ),

            # SetupNetwork
            pytest.param(*sn_mask_vm, marks=(polarion("RHEVM3-10474"))),
            pytest.param(*sn_pre_vm, marks=(polarion("RHEVM3-19111"))),
            pytest.param(*sn_mask_vlan, marks=(polarion("RHEVM3-10475"))),
            pytest.param(*sn_pre_vlan, marks=(polarion("RHEVM3-19112"))),
            pytest.param(*sn_mask_non_vm, marks=(polarion("RHEVM3-10476"))),
            pytest.param(*sn_pre_non_vm, marks=(polarion("RHEVM3-19113"))),
            pytest.param(
                *sn_mask_non_vm_vlan, marks=(polarion("RHEVM3-10477"))
            ),
            pytest.param(
                *sn_pre_non_vm_vlan, marks=(polarion("RHEVM3-19114"))
            ),
        ],
        ids=[
            "Attach_VM_network_with_IP_(netmask)_via_host_NIC",
            "Attach_VM_network_with_IP_(prefix)_via_host_NIC",
            "Attach_VLAN_network_with_IP_(netmask)_via_host_NIC",
            "Attach_VLAN_network_with_IP_(prefix)_via_host_NIC",
            "Attach_Non-VM_network_with_IP_(netmask)_via_host_NIC",
            "Attach_Non-VM_network_with_IP_(prefix)_via_host_NIC",
            "Attach_Non-VM_VLAN_network_with_IP_(netmask)_via_host_NIC",
            "Attach_Non-VM_VLAN_network_with_IP_(prefix)_via_host_NIC",

            "Attach_VM_network_with_IP_(netmask)_via_host",
            "Attach_VM_network_with_IP_(prefix)_via_host",
            "Attach_VLAN_network_with_IP_(netmask)_via_host",
            "Attach_VLAN_network_with_IP_(prefix)_via_host",
            "Attach_Non-VM_network_with_IP_(netmask)_via_host",
            "Attach_Non-VM_network_with_IP_(prefix)_via_host",
            "Attach_Non-VM_VLAN_network_with_IP_(netmask)_via_host",
            "Attach_Non-VM_VLAN_network_with_IP_(prefix)_via_host",

            "Attach_VM_network_with_IP_(netmask)_via_sn",
            "Attach_VM_network_with_IP_(prefix)_via_sn",
            "Attach_VLAN_network_with_IP_(netmask)_via_sn",
            "Attach_VLAN_network_with_IP_(prefix)_via_sn",
            "Attach_Non-VM_network_with_IP_(netmask)_via_sn",
            "Attach_Non-VM_network_with_IP_(prefix)_via_sn",
            "Attach_Non-VM_VLAN_network_with_IP_(netmask)_via_sn",
            "Attach_Non-VM_VLAN_network_with_IP_(prefix)_via_sn",
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_03_DICT,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # HostNic
    net_1 = net_api_conf.NETS[3][0]
    host_nic_network = [net_1, 1, "host_nic"]

    # Host
    net_2 = net_api_conf.NETS[3][1]
    host_network = [net_2, 2, "host"]

    # SetupNetworks
    net_3 = net_api_conf.NETS[3][2]
    sn_network = [net_3, bond_1, "sn"]

    # setup_networks_fixture fixture
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
               "nic": bond_1,
               "slaves": [-1, -2]
            }
        }
    }

    @tier2
    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            pytest.param(*host_nic_network, marks=(polarion("RHEVM3-10450"))),
            pytest.param(*host_network, marks=(polarion("RHEVM3-10464"))),
            pytest.param(*sn_network, marks=(polarion("RHEVM3-11880"))),
        ],
        ids=[
            "Attach_VM_network_with_custom_properties_via_host_NIC",
            "Attach_VM_network_with_custom_properties_via_host",
            "Attach_VM_network_with_custom_properties_via_sn",
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


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_04_DICT,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

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

    # Host NIC
    test01_host_nic_network = [1, "host_nic"]
    test02_host_nic_network = [net_1, 1, "host_nic"]

    # Host
    test01_host_network = [2, "host"]
    test02_host_network = [net_2, 2, "host"]

    # SetupNetworks
    test01_sn_network = [3, "sn"]
    test02_sn_network = [net_3, 3, "sn"]

    @tier2
    @pytest.mark.parametrize(
        ("nic", "via"),
        [
            pytest.param(
                *test01_host_nic_network, marks=(polarion("RHEVM3-10451"))
            ),
            pytest.param(
                *test01_host_network, marks=(polarion("RHEVM3-10465"))
            ),
            pytest.param(*test01_sn_network, marks=(polarion("RHEVM3-10513"))),
        ],
        ids=[
            "Attach_VM_network_with_via_host_NIC",
            "Attach_VM_network_with_via_host",
            "Attach_VM_network_with_via_sn",
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

    @tier2
    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            pytest.param(
                *test02_host_nic_network, marks=(polarion("RHEVM3-10452"))
            ),
            pytest.param(
                *test02_host_network, marks=(polarion("RHEVM3-10466"))
            ),
            pytest.param(*test02_sn_network, marks=(polarion("RHEVM3-10514"))),
        ],
        ids=[
            "Remove_network_from_host_via_host_NIC",
            "Remove_network_from_host_via_host",
            "Remove_network_from_host_via_sn",
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    # General
    net_1 = net_api_conf.NETS[5][0]
    net_2 = net_api_conf.NETS[5][1]
    net_3 = net_api_conf.NETS[5][2]
    net_4 = net_api_conf.NETS[5][3]

    bond_1 = "bond51"
    bond_2 = "bond52"
    bond_3 = "bond53"
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_05_DICT,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # test_attach_network_on_bond_nic params
    # HostNic
    net_5 = net_api_conf.NETS[5][4]

    # Host
    net_6 = net_api_conf.NETS[5][5]

    # SetupNetworks
    net_7 = net_api_conf.NETS[5][6]

    # test_update_network_with_ip_nic params
    # HostNic
    host_nic_ip_mask = [net_api_conf.IPS.pop(0), "host_nic"]
    host_nic_ip_pre = [net_api_conf.IPS.pop(0), "host_nic"]
    host_nic_to_bond = [net_5, bond_1, "host_nic"]
    host_nic_remove_bond = [net_2, "host_nic"]

    # Host
    host_ip_mask = [net_api_conf.IPS.pop(0), "host"]
    host_ip_pre = [net_api_conf.IPS.pop(0), "host"]
    host_to_bond = [net_6, bond_1, "host"]
    host_remove_bond = [net_3, "host"]

    # SetupNetworks
    sn_ip_mask = [net_api_conf.IPS.pop(0), "sn"]
    sn_ip_pre = [net_api_conf.IPS.pop(0), "sn"]
    sn_to_bond = [net_7, bond_1, "sn"]
    sn_remove_bond = [net_4, "sn"]

    # Test params
    netmask_ips = [host_nic_ip_mask, host_ip_mask, sn_ip_mask]
    prefix_ips = [host_nic_ip_pre, host_ip_pre, sn_ip_pre]

    # setup_networks_fixture fixture
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

    @tier2
    @pytest.mark.parametrize(
        ("ip", "via"),
        [
            pytest.param(*host_nic_ip_mask, marks=(polarion("RHEVM3-10453"))),
            pytest.param(*host_nic_ip_pre, marks=(polarion("RHEVM3-19116"))),
            pytest.param(*host_ip_mask, marks=(polarion("RHEVM3-10467"))),
            pytest.param(*host_ip_pre, marks=(polarion("RHEVM3-19115"))),
            pytest.param(*sn_ip_mask, marks=(polarion("RHEVM3-10515"))),
            pytest.param(*sn_ip_pre, marks=(polarion("RHEVM3-19110"))),
        ],
        ids=[
            "Update_network_to_have_IP_(netmask)_via_host_NIC",
            "Update_network_to_have_IP_(prefix)_via_host_NIC",
            "Update_network_to_have_IP_(netmask)_via_host",
            "Update_network_to_have_IP_(prefix)_via_host",
            "Update_network_to_have_IP_(netmask)_via_sn",
            "Update_network_to_have_IP_(prefix)_via_sn",
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

    @tier2
    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            pytest.param(*host_nic_to_bond, marks=(polarion("RHEVM3-10454"))),
            pytest.param(*host_to_bond, marks=(polarion("RHEVM3-10468"))),
            pytest.param(*sn_to_bond, marks=(polarion("RHEVM3-10516"))),
        ],
        ids=[
            "Attach_network_to_BOND_via_host_NIC",
            "Attach_network_to_BOND_via_host",
            "Attach_network_to_BOND_via_sn",
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

    @tier2
    @pytest.mark.parametrize(
        ("network", "via"),
        [
            pytest.param(
                *host_nic_remove_bond, marks=(polarion("RHEVM3-10455"))
            ),
            pytest.param(*host_remove_bond, marks=(polarion("RHEVM3-10469"))),
            pytest.param(*sn_remove_bond, marks=(polarion("RHEVM3-10517"))),
        ],
        ids=[
            "Remove_VLAN_network_and_Non-VM_network_via_host_NIC",
            "Remove_VLAN_network_and_Non-VM_network_via_host",
            "Remove_VLAN_network_and_Non-VM_network_via_host_NIC"
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_06_DICT,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

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

    # Host
    host_network = [net_1, "host"]
    host_network_bond = [net_2, "host"]

    # SetupNetwork
    sn_network = [net_3, "sn"]
    sn_network_bond = [net_4, "sn"]

    @tier2
    @pytest.mark.parametrize(
        ("network", "via"),
        [
            pytest.param(*host_network, marks=(polarion("RHEVM3-12165"))),
            pytest.param(*host_network_bond, marks=(polarion("RHEVM3-12166"))),
            pytest.param(*sn_network, marks=(polarion("RHEVM3-11432"))),
            pytest.param(*sn_network_bond, marks=(polarion("RHEVM3-12164"))),
        ]
    )
    def test_remove_un_managed_network(self, network, via):
        """
        Remove the un-managed network from host
        """
        host_0 = conf.HOST_0_NAME
        host_obj = ll_hosts.get_host_object(host_name=host_0)
        testflow.step(
            "Get un-managed network %s object from host %s via %s",
            network, host_0, via
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host=host_obj, networks=[network]
        )
        testflow.step(
            "Remove the un-managed network %s from host %s via %s", network,
            host_0, via
        )
        if via == "host":
            assert ll_host_network.remove_unmanaged_networks(
                host=host_obj, networks=[network]
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetworkApi07(NetworkTest):
    """
    All tests are done via Host and SetupNetworks API

    1) Attach VM network to host NIC that has VLAN network on it
    2) Attach VLAN network to host NIC that has VM network on it
    """
    # General
    bond_1 = "bond071"
    bond_2 = "bond072"
    bond_3 = "bond073"
    bond_4 = "bond074"
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.NETS_CLASS_07_DICT,
            "data_center": conf.DC_0,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # test_attach_network_to_nic_mixed params
    # Host
    net_vm_host = [net_api_conf.NETS[7][9], 2, "host"]
    net_vlan_host = [net_api_conf.NETS[7][8], 1, "host"]
    net_vm_host_bond = [net_api_conf.NETS[7][13], bond_2, "host"]
    net_vlan_host_bond = [net_api_conf.NETS[7][12], bond_1, "host"]

    # SetupNetworks
    net_vm_sn = [net_api_conf.NETS[7][11], 4, "sn"]
    net_vlan_sn = [net_api_conf.NETS[7][10], 3, "sn"]
    net_vm_sn_bond = [net_api_conf.NETS[7][15], bond_4, "sn"]
    net_vlan_sn_bond = [net_api_conf.NETS[7][14], bond_3, "sn"]

    # setup_networks_fixture params
    net_1 = net_api_conf.NETS[7][0]
    net_2 = net_api_conf.NETS[7][1]
    net_3 = net_api_conf.NETS[7][2]
    net_4 = net_api_conf.NETS[7][3]
    net_5 = net_api_conf.NETS[7][4]
    net_6 = net_api_conf.NETS[7][5]
    net_7 = net_api_conf.NETS[7][6]
    net_8 = net_api_conf.NETS[7][7]
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

    @tier2
    @pytest.mark.parametrize(
        ("network", "nic", "via"),
        [
            # Host
            pytest.param(*net_vm_host, marks=(polarion("RHEVM3-19121"))),
            pytest.param(*net_vlan_host, marks=(polarion("RHEVM3-19120"))),
            pytest.param(*net_vm_host_bond, marks=(polarion("RHEVM3-19123"))),
            pytest.param(
                *net_vlan_host_bond, marks=(polarion("RHEVM3-19122"))
            ),

            # SetupNetworks
            pytest.param(*net_vm_sn, marks=(polarion("RHEVM3-14015"))),
            pytest.param(*net_vlan_sn, marks=(polarion("RHEVM3-14016"))),
            pytest.param(*net_vm_sn_bond, marks=(polarion("RHEVM3-14018"))),
            pytest.param(*net_vlan_sn_bond, marks=(polarion("RHEVM3-14019"))),
        ],
        ids=[
            "Attach_VLAN_network_to_host_NIC_via_host",
            "Attach_VM_network_to_host_NIC_via_host",
            "Attach_VLAN_network_to_host_NIC_via_sn",
            "Attach_VM_network_to_host_NIC_via_sn",
            "Attach_VLAN_network_to_bond_via_host",
            "Attach_VM_network_to_bond_via_host",
            "Attach_VLAN_network_to_bond_via_sn",
            "Attach_VM_network_to_bond_via_host",
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
