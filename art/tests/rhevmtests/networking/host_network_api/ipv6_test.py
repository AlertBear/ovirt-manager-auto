#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
IPv6 tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as net_api_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)
from art.unittest_lib import (
    tier2,
    NetworkTest,
)


@tier2
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetworkApiIpV601(NetworkTest):
    """
    Attach network with static/autocon/dhcp IPv6 over:
    1. Bridge
    2. VLAN
    3. BOND
    4. VLAN BOND
    5. Non-VM
    6. Non-VM VLAN
    """
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.IPV6_NETS_CLASS_1,
            "datacenter": dc,
            "cluster": conf.CL_0,
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # STATIC
    # Bridge static
    net_1 = net_api_conf.IPV6_NETS[1][0]
    ip_v6_1 = net_api_conf.IPV6_IPS.pop(0)
    param_1 = [net_1, 1, ip_v6_1, "static"]

    # VLAN static
    net_2 = net_api_conf.IPV6_NETS[1][1]
    ip_v6_2 = net_api_conf.IPV6_IPS.pop(0)
    param_2 = [net_2, 2, ip_v6_1, "static"]

    # BOND static
    bond_1 = "bond10"
    net_3 = net_api_conf.IPV6_NETS[1][2]
    ip_v6_3 = net_api_conf.IPV6_IPS.pop(0)
    param_3 = [net_3, bond_1, ip_v6_3, "static"]

    # VLAN BOND static
    bond_2 = "bond11"
    net_4 = net_api_conf.IPV6_NETS[1][3]
    ip_v6_4 = net_api_conf.IPV6_IPS.pop(0)
    param_4 = [net_4, bond_2, ip_v6_4, "static"]

    # Non-VM static
    net_5 = net_api_conf.IPV6_NETS[1][4]
    ip_v6_5 = net_api_conf.IPV6_IPS.pop(0)
    param_5 = [net_5, 7, ip_v6_5, "static"]

    # Non-VM VLAN static
    net_6 = net_api_conf.IPV6_NETS[1][5]
    ip_v6_6 = net_api_conf.IPV6_IPS.pop(0)
    param_6 = [net_6, 8, ip_v6_6, "static"]

    # AUTOCONF
    # Bridge autoconf
    net_7 = net_api_conf.IPV6_NETS[1][6]
    param_7 = [net_7, 9, None, "autoconf"]

    # VLAN autoconf
    net_8 = net_api_conf.IPV6_NETS[1][7]
    param_8 = [net_8, 10, None, "autoconf"]

    # BOND autoconf
    bond_3 = "bond13"
    net_9 = net_api_conf.IPV6_NETS[1][8]
    param_9 = [net_9, bond_3, None, "autoconf"]

    # VLAN BOND autoconf
    bond_4 = "bond14"
    net_10 = net_api_conf.IPV6_NETS[1][9]
    param_10 = [net_10, bond_4, None, "autoconf"]

    # Non-VM autoconf
    net_11 = net_api_conf.IPV6_NETS[1][10]
    param_11 = [net_11, 15, None, "autoconf"]

    # Non-VM VLAN autoconf
    net_12 = net_api_conf.IPV6_NETS[1][11]
    param_12 = [net_12, 16, None, "autoconf"]

    # DHCP
    # Bridge DHCP
    net_13 = net_api_conf.IPV6_NETS[1][12]
    param_13 = [net_13, 17, None, "autoconf"]

    # VLAN DHCP
    net_14 = net_api_conf.IPV6_NETS[1][13]
    param_14 = [net_14, 18, None, "autoconf"]

    # BOND DHCP
    bond_5 = "bond15"
    net_15 = net_api_conf.IPV6_NETS[1][14]
    param_15 = [net_15, bond_5, None, "autoconf"]

    # VLAN BOND DHCP
    bond_6 = "bond16"
    net_16 = net_api_conf.IPV6_NETS[1][15]
    param_16 = [net_16, bond_6, None, "autoconf"]

    # Non-VM DHCP
    net_17 = net_api_conf.IPV6_NETS[1][16]
    param_17 = [net_17, 23, None, "autoconf"]

    # Non-VM VLAN DHCP
    net_18 = net_api_conf.IPV6_NETS[1][17]
    param_18 = [net_18, 24, None, "autoconf"]

    # setup_networks_fixture fixture
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [3, 4]
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [5, 6]
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [11, 12]
            },
            bond_4: {
                "nic": bond_4,
                "slaves": [13, 14]
            },
            bond_5: {
                "nic": bond_5,
                "slaves": [19, 20]
            },
            bond_6: {
                "nic": bond_6,
                "slaves": [21, 22]
            }
        }
    }

    @pytest.mark.parametrize(
        ("network", "nic", "ip", "proto"),
        [
            # Static IPv6
            polarion("RHEVM3-16627")(param_1),
            polarion("RHEVM3-16639")(param_2),
            polarion("RHEVM3-16640")(param_3),
            polarion("RHEVM3-16641")(param_4),
            polarion("RHEVM3-16642")(param_5),
            polarion("RHEVM3-16643")(param_6),

            # Autoconf IPv6
            polarion("RHEVM3-19184")(param_7),
            polarion("RHEVM3-19185")(param_8),
            polarion("RHEVM3-19186")(param_9),
            polarion("RHEVM3-19188")(param_10),
            polarion("RHEVM3-19189")(param_11),
            polarion("RHEVM3-19190")(param_12),

            # DHCP IPv6
            polarion("RHEVM3-19191")(param_13),
            polarion("RHEVM3-19192")(param_14),
            polarion("RHEVM3-19193")(param_15),
            polarion("RHEVM3-19194")(param_16),
            polarion("RHEVM3-19195")(param_17),
            polarion("RHEVM3-19196")(param_18),
        ],
        ids=[
            "Bridge_static",
            "VLAN_static",
            "BOND_static",
            "VLAN_BOND_static",
            "Non-VM_static",
            "Non-VM_VLAN_static",
            "Bridge_autoconf",
            "VLAN_autoconf",
            "BOND_autoconf",
            "VLAN_BOND_autoconf",
            "Non-VM_autoconf",
            "Non-VM_VLAN_autoconf",
            "Bridge_DHCP",
            "VLAN_DHCP",
            "BOND_DHCP",
            "VLAN_BOND_DHCP",
            "Non-VM_DHCP",
            "Non-VM_VLAN_DHCP",
        ]
    )
    def test_static_autoconf_dhcp_ipv6_network_on_host(
        self, network, nic, ip, proto
    ):
        """
        Attach network with static/autoconf/dhcp IPv6
        """
        ip_dict = helper.get_ip_dict(ip=ip, proto=proto)
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        sn_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": host_nic,
                    "ip": {
                        "1": ip_dict
                    }
                },
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@tier2
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetworkApiIpV602(NetworkTest):
    """
    Update IPv6 with static, dhcp and autoconf

    1. Update IPv4 and IPv6 from static to another static IPs
    2. Update from static IPv6 to another static IPv6
    3. Update from static IPv6 to dhcpv6
    4. Update from static IPv6 to autoconf
    5. Update from dhcpv6 to static IPv6
    """
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": net_api_conf.IPV6_NETS_CLASS_2,
            "datacenter": dc,
            "cluster": conf.CL_0,
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # net_1 IP dict
    net_1 = net_api_conf.IPV6_NETS[2][0]
    net_1_dict = net_api_conf.BASIC_IPV4_AND_IPV6_DICT.copy()
    net_1_dict["ipv6"]["address"] = net_api_conf.IPV6_IPS.pop(0)
    net_1_dict["ipv4"]["address"] = net_api_conf.IPV4_IPS.pop(0)

    net_1_new_dict = net_api_conf.BASIC_IPV4_AND_IPV6_DICT.copy()
    net_1_new_dict["ipv6"]["address"] = net_api_conf.IPV6_IPS.pop(0)
    net_1_new_dict["ipv4"]["address"] = net_api_conf.IPV4_IPS.pop(0)

    # net_2 IP dict
    net_2 = net_api_conf.IPV6_NETS[2][1]
    net_2_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_2_dict["address"] = net_api_conf.IPV6_IPS.pop(0)

    net_2_new_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_2_new_dict["address"] = net_api_conf.IPV6_IPS.pop(0)

    # net_3 IP dict
    net_3 = net_api_conf.IPV6_NETS[2][2]
    net_3_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_3_dict["address"] = net_api_conf.IPV6_IPS.pop(0)

    net_3_new_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_3_new_dict["boot_protocol"] = "dhcp"
    net_3_new_dict["address"] = None
    net_3_new_dict["netmask"] = None

    # net_4 IP dict
    net_4 = net_api_conf.IPV6_NETS[2][3]
    net_4_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_4_dict["address"] = net_api_conf.IPV6_IPS.pop(0)

    net_4_new_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_4_new_dict["boot_protocol"] = "autoconf"
    net_4_new_dict["address"] = None
    net_4_new_dict["netmask"] = None

    # net_5 IP dict
    net_5 = net_api_conf.IPV6_NETS[2][4]
    net_5_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_5_dict["boot_protocol"] = "dhcp"
    net_5_dict["address"] = None
    net_5_dict["netmask"] = None

    net_5_new_dict = net_api_conf.IPV6_IP_DICT.copy()
    net_5_new_dict["address"] = net_api_conf.IPV6_IPS.pop(0)

    # setup_networks_fixture fixture
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "ip": net_1_dict
            },
            net_2: {
                "nic": 2,
                "network": net_2,
                "ip": {
                    "1": net_2_dict
                }
            },
            net_3: {
                "nic": 3,
                "network": net_3,
                "ip": {
                    "1": net_3_dict
                }
            },
            net_4: {
                "nic": 4,
                "network": net_4,
                "ip": {
                    "1": net_4_dict
                }
            },
            net_5: {
                "nic": 5,
                "network": net_5,
                "ip": {
                    "1": net_5_dict
                }
            },
        }
    }

    @pytest.mark.parametrize(
        ("network", "nic", "ip_dict"),
        [
            polarion("RHEVM-16884")([net_1, 1, net_1_new_dict]),
            polarion("RHEVM-16899")([net_2, 2, net_2_new_dict]),
            polarion("RHEVM-16900")([net_3, 3, net_3_new_dict]),
            polarion("RHEVM-16901")([net_4, 4, net_4_new_dict]),
            polarion("RHEVM-16902")([net_5, 5, net_5_new_dict]),
        ],
        ids=[
            "Update_IPv4_and_IPv6_from_static_to_another_static_IPs",
            "Update_from_static_IPv6_to_another_static_IPv6",
            "Update_from_static_IPv6_to_dhcpv6",
            "Update_from_static_IPv6_to_autoconf",
            "Update_from_dhcpv6_to_static_IPv6",
        ]
    )
    def test_update_network_ipv6_addresses(self, network, nic, ip_dict):
        """
        Update IPv6 with static, dhcp and autoconf
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        ip_dict = ip_dict if network == self.net_1 else {"1": ip_dict}
        sn_dict = {
            "update": {
                "1": {
                    "network": network,
                    "nic": host_nic,
                    "ip": ip_dict
                },
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
