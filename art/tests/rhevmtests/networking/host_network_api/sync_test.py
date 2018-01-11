#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sync tests from host network API
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import config as net_api_conf
import helper
import rhevmtests.helpers as global_helper
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import (
    update_host_to_another_cluster, manage_ip_and_refresh_capabilities
)
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.fixture(scope="module", autouse=True)
def sync_prepare_setup(request):
    """
    Prepare setup for sync tests
    """
    host = conf.HOST_0_NAME
    datacentr = net_api_conf.SYNC_DC
    cluster = net_api_conf.SYNC_CL
    result = list()

    def fin3():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)
    request.addfinalizer(fin3)

    def fin2():
        """
        Activate host
        """
        result.append(
            (
                ll_hosts.activate_host(
                    positive=True, host=host,
                    host_resource=conf.VDS_0_HOST
                ),
                "fin2: ll_hosts.activate_host"
            )
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove basic setup
        """
        testflow.teardown(
            "Remove datacenter %s and cluster %s", datacentr, cluster
        )
        result.append(
            (
                hl_networks.remove_basic_setup(
                    datacenter=datacentr, cluster=cluster
                ), "fin1: hl_networks.remove_basic_setup"
            )
        )
    request.addfinalizer(fin1)

    testflow.setup("Create dtacenter %s and cluster %s", datacentr, cluster)
    assert hl_networks.create_basic_setup(
        datacenter=datacentr, version=conf.COMP_VERSION,
        cluster=cluster, cpu=conf.CPU_NAME
    )
    assert ll_hosts.deactivate_host(
        positive=True, host=host, host_resource=conf.VDS_0_HOST
    )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    update_host_to_another_cluster.__name__
)
class TestHostNetworkApiSync01(NetworkTest):
    """
    All tests on NIC and BOND
    1. Check sync/un-sync different VLAN networks and sync the network.
    2. Check sync/un-sync different MTU networks over NIC and sync the network.
    3. Check sync/un-sync for VM/Non-VM networks over NIC and sync the network.
    4. Check sync/un-sync for VLAN/MTU/Bridge on the same network over NIC and
        sync the network.
    """

    # Types
    vlan = net_api_conf.VLAN_STR
    mtu = net_api_conf.MTU_STR
    bridge = net_api_conf.BRIDGE_STR

    share = net_api_conf.AVERAGE_SHARE_STR
    limit = net_api_conf.AVERAGE_LIMIT_STR
    real = net_api_conf.AVERAGE_REAL_STR
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": net_api_conf.SYNC_DICT_1_CASE_1,
        },
        "2": {
            "data_center": net_api_conf.SYNC_DC,
            "clusters": [net_api_conf.SYNC_CL],
            "networks": net_api_conf.SYNC_DICT_2_CASE_1,
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc, net_api_conf.SYNC_DC]

    # NIC
    # Sync change VLAN on NIC
    net_1 = net_api_conf.SYNC_NETS_DC_1[1][0]
    param_dict_1 = helper.get_dict(network=net_1, type_=vlan)
    vlan_to_vlan_nic = [param_dict_1]

    # Sync VLAN to no VLAN on NIC
    net_2 = net_api_conf.SYNC_NETS_DC_1[1][1]
    param_dict_2 = helper.get_dict(network=net_2, type_=vlan)
    vlan_to_none_nic = [param_dict_2]

    # Sync no VLAN to VLAn on NIC
    net_3 = net_api_conf.SYNC_NETS_DC_1[1][2]
    param_dict_3 = helper.get_dict(network=net_3, type_=vlan)
    none_to_vlan_nic = [param_dict_3]

    # Sync change MTU on NIC
    net_4 = net_api_conf.SYNC_NETS_DC_1[1][3]
    param_dict_4 = helper.get_dict(network=net_4, type_=mtu)
    mtu_to_mtu_nic = [param_dict_4]

    # Sync MTU to no MTU on NIC
    net_5 = net_api_conf.SYNC_NETS_DC_1[1][4]
    param_dict_5 = helper.get_dict(network=net_5, type_=mtu)
    mtu_to_none_nic = [param_dict_5]

    # Sync no MTU to MTU on NIC
    net_6 = net_api_conf.SYNC_NETS_DC_1[1][5]
    param_dict_6 = helper.get_dict(network=net_6, type_=mtu)
    none_to_mtu_nic = [param_dict_6]

    # Sync VM to non-VM on NIC
    net_7 = net_api_conf.SYNC_NETS_DC_1[1][6]
    param_dict_7 = helper.get_dict(network=net_7, type_=bridge)
    vm_to_non_vm_nic = [param_dict_7]

    # Sync non-VM to VM on NIC
    net_8 = net_api_conf.SYNC_NETS_DC_1[1][7]
    param_dict_8 = helper.get_dict(network=net_8, type_=bridge)
    non_vm_to_vm_nic = [param_dict_8]

    # Sync VLAN, MTU and VM on NIC
    net_9 = net_api_conf.SYNC_NETS_DC_1[1][8]
    param_dict_9_1 = helper.get_dict(network=net_9, type_=vlan)
    param_dict_9_2 = helper.get_dict(network=net_9, type_=mtu)
    param_dict_9_3 = helper.get_dict(network=net_9, type_=bridge)
    vlan_mtu_vm_nic = [param_dict_9_1, param_dict_9_2, param_dict_9_3]

    # BOND
    # Sync change VLAN on BOND
    net_10 = net_api_conf.SYNC_NETS_DC_1[1][9]
    param_dict_10 = helper.get_dict(network=net_10, type_=vlan)
    vlan_to_vlan_bond = [param_dict_10]

    # Sync VLAN to no VLAN on BOND
    net_11 = net_api_conf.SYNC_NETS_DC_1[1][10]
    param_dict_11 = helper.get_dict(network=net_11, type_=vlan)
    vlan_to_none_bond = [param_dict_11]

    # Sync no VLAN to VLAn on BOND
    net_12 = net_api_conf.SYNC_NETS_DC_1[1][11]
    param_dict_12 = helper.get_dict(network=net_12, type_=vlan)
    none_to_vlan_bond = [param_dict_12]

    # Sync change MTU on BOND
    net_13 = net_api_conf.SYNC_NETS_DC_1[1][12]
    param_dict_13 = helper.get_dict(network=net_13, type_=mtu)
    mtu_to_mtu_bond = [param_dict_13]

    # Sync MTU to no MTU on BOND
    net_14 = net_api_conf.SYNC_NETS_DC_1[1][13]
    param_dict_14 = helper.get_dict(network=net_14, type_=mtu)
    mtu_to_none_bond = [param_dict_14]

    # Sync no MTU to MTU on BOND
    net_15 = net_api_conf.SYNC_NETS_DC_1[1][14]
    param_dict_15 = helper.get_dict(network=net_15, type_=mtu)
    none_to_mtu_bond = [param_dict_15]

    # Sync VM to non-VM on BOND
    net_16 = net_api_conf.SYNC_NETS_DC_1[1][15]
    param_dict_16 = helper.get_dict(network=net_16, type_=bridge)
    vm_to_non_vm_bond = [param_dict_16]

    # Sync non-VM to VM on BOND
    net_17 = net_api_conf.SYNC_NETS_DC_1[1][16]
    param_dict_17 = helper.get_dict(network=net_17, type_=bridge)
    non_vm_to_vm_bond = [param_dict_17]

    # Sync VLAN, MTU and VM on BOND
    net_18 = net_api_conf.SYNC_NETS_DC_1[1][17]
    param_dict_18_1 = helper.get_dict(network=net_18, type_=vlan)
    param_dict_18_2 = helper.get_dict(network=net_18, type_=mtu)
    param_dict_18_3 = helper.get_dict(network=net_18, type_=bridge)
    vlan_mtu_vm_bond = [param_dict_18_1, param_dict_18_2, param_dict_18_3]

    # setup_networks_fixture params
    bond_1 = "bond01"
    bond_2 = "bond02"
    bond_3 = "bond03"
    bond_4 = "bond04"
    bond_5 = "bond05"
    bond_6 = "bond06"
    bond_7 = "bond07"
    bond_8 = "bond08"
    bond_9 = "bond09"
    hosts_nets_nic_dict = {
        0: {
            # Sync over NIC
            net_1: {
                "nic": 1,
                "network": net_1,
                "datacenter": conf.DC_0
            },
            net_2: {
                "nic": 2,
                "network": net_2,
                "datacenter": conf.DC_0
            },
            net_3: {
                "nic": 3,
                "network": net_3,
                "datacenter": conf.DC_0
            },
            net_4: {
                "nic": 4,
                "network": net_4,
                "datacenter": conf.DC_0
            },
            net_5: {
                "nic": 5,
                "network": net_5,
                "datacenter": conf.DC_0
            },
            net_6: {
                "nic": 6,
                "network": net_6,
                "datacenter": conf.DC_0
            },
            net_7: {
                "nic": 7,
                "network": net_7,
                "datacenter": conf.DC_0
            },
            net_8: {
                "nic": 8,
                "network": net_8,
                "datacenter": conf.DC_0
            },
            net_9: {
                "nic": 9,
                "network": net_9,
                "datacenter": conf.DC_0
            },
            # Sync over BOND
            bond_1: {
                "nic": bond_1,
                "slaves": [10, 11],
                "network": net_10,
                "datacenter": conf.DC_0
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [12, 13],
                "network": net_11,
                "datacenter": conf.DC_0
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [14, 15],
                "network": net_12,
                "datacenter": conf.DC_0
            },
            bond_4: {
                "nic": bond_4,
                "slaves": [16, 17],
                "network": net_13,
                "datacenter": conf.DC_0
            },
            bond_5: {
                "nic": bond_5,
                "slaves": [18, 19],
                "network": net_14,
                "datacenter": conf.DC_0
            },
            bond_6: {
                "nic": bond_6,
                "slaves": [20, 21],
                "network": net_15,
                "datacenter": conf.DC_0
            },
            bond_7: {
                "nic": bond_7,
                "slaves": [22, 23],
                "network": net_16,
                "datacenter": conf.DC_0
            },
            bond_8: {
                "nic": bond_8,
                "slaves": [24, 25],
                "network": net_17,
                "datacenter": conf.DC_0
            },
            bond_9: {
                "nic": bond_9,
                "slaves": [26, 27],
                "network": net_18,
                "datacenter": conf.DC_0
            },
        }
    }

    @tier2
    @pytest.mark.parametrize(
        "compare_dicts",
        [
            # Sync over NIC
            pytest.param(vlan_to_vlan_nic, marks=(polarion("RHEVM3-13977"))),
            pytest.param(vlan_to_none_nic, marks=(polarion("RHEVM3-13979"))),
            pytest.param(none_to_vlan_nic, marks=(polarion("RHEVM3-13980"))),
            pytest.param(
                mtu_to_mtu_nic, marks=(
                    (polarion("RHEVM3-13987"), bz({"1533067": {}}))
                )
            ),
            pytest.param(
                mtu_to_none_nic, marks=(
                    (polarion("RHEVM3-13988"), bz({"1533067": {}}))
                )
            ),
            pytest.param(
                none_to_mtu_nic, marks=(
                    (polarion("RHEVM3-13989"), bz({"1533067": {}}))
                )
            ),
            pytest.param(vm_to_non_vm_nic, marks=(polarion("RHEVM3-13993"))),
            pytest.param(non_vm_to_vm_nic, marks=(polarion("RHEVM3-13994"))),
            pytest.param(
                vlan_mtu_vm_nic, marks=(
                    (polarion("RHEVM3-13997"), bz({"1533067": {}}))
                )
            ),

            # Sync over BOND
            pytest.param(vlan_to_vlan_bond, marks=(polarion("RHEVM3-13981"))),
            pytest.param(vlan_to_none_bond, marks=(polarion("RHEVM3-13982"))),
            pytest.param(none_to_vlan_bond, marks=(polarion("RHEVM3-13985"))),
            pytest.param(
                mtu_to_mtu_bond, marks=(
                    (polarion("RHEVM3-13990"), bz({"1533067": {}}))
                )
            ),
            pytest.param(
                mtu_to_none_bond, marks=(
                    (polarion("RHEVM3-13991"), bz({"1533067": {}}))
                )
            ),
            pytest.param(
                none_to_mtu_bond, marks=(
                    (polarion("RHEVM3-13992"), bz({"1533067": {}}))
                )
            ),
            pytest.param(vm_to_non_vm_bond, marks=(polarion("RHEVM3-13995"))),
            pytest.param(non_vm_to_vm_bond, marks=(polarion("RHEVM3-13996"))),
            pytest.param(
                vlan_mtu_vm_bond, marks=(
                    (polarion("RHEVM3-13998"), bz({"1533067": {}}))
                )
            ),
        ],
        ids=[
            # Sync over NIC
            "Change_VLAN_on_NIC",
            "Remove_VLAN_from_NIC",
            "Add_VLAN_to_NIC",
            "Change_MTU_on_NIC",
            "Remove_MTU_from_NIC",
            "Set_MTU_on_NIC",
            "Change_VM_to_non-VM_on_NIC",
            "Change_Non-VM_to_VM_on_NIC",
            "Mixed:_Change_VLAN_MTU_and_VM_on_NIC",

            # Sync over BOND
            "Change_VLAN_on_BOND",
            "Remove_VLAN_from_BOND",
            "Add_VLAN_to_BOND",
            "Change_MTU_on_BOND",
            "Remove_MTU_from_BOND",
            "Set_MTU_on_BOND",
            "Change_VM_to_non-VM_on_BOND",
            "Change_Non-VM_to_VM_on_BOND",
            "Mixed:_Change_VLAN_MTU_and_VM_on_BOND",
        ]
    )
    def test_vlan_mtu_bridge_unsync_networks(self, compare_dicts):
        """
        1. Check that the network is un-sync and the sync reason is different
           VLAN, MTU or bridge
        2. Sync the network
        """
        network = None
        for dict_ in compare_dicts:
            network = dict_.keys()[0]
            type_ = dict_.get(network).keys()[0]
            testflow.step(
                "Check that the network %s is un-sync and the sync reason is "
                "different %s %s", network, type_, dict_
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                net_sync_reason=dict_
            )
        testflow.step("Sync the network %s", network)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[network]
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    manage_ip_and_refresh_capabilities.__name__,
)
class TestHostNetworkApiSync02(NetworkTest):
    """
    All tests on NIC and BOND
    1. Check sync/un-sync for changed IP and sync the network.
    2. Check sync/un-sync for changed netmask and sync the network.
    3. Check sync/un-sync for changed netmask prefix and sync the network.
    4. Check sync/un-sync for no-IP to IP and sync the network.
    5. Check sync/un-sync for removed IP and sync the network.
    """
    # General params
    ips = network_helper.create_random_ips(num_of_ips=20, mask=24)

    # Types
    proto = net_api_conf.BOOTPROTO_STR
    mask = net_api_conf.NETMASK_STR
    ip = net_api_conf.IPADDR_STR
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": net_api_conf.IP_DICT_CASE_2,
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # NIC
    # Sync IP to IP NIC
    net_1 = net_api_conf.SYNC_NETS_DC_1[2][0]
    net_1_ip = ips.pop(0)
    net_1_ip_actual = ips.pop(0)
    net_1_ip_expected = net_1_ip
    ip_to_ip_nic = helper.get_dict(
        network=net_1, type_=ip, act=net_1_ip_actual, ex=net_1_ip_expected
    )

    # Sync mask to mask NIC
    net_2 = net_api_conf.SYNC_NETS_DC_1[2][1]
    net_2_ip = ips.pop(0)
    net_2_mask_actual = "255.255.255.255"
    net_2_mask_expected = net_api_conf.IP_DICT_NETMASK["netmask"]
    mask_to_mask_nic = helper.get_dict(
        network=net_2, type_=mask, act=net_2_mask_actual,
        ex=net_2_mask_expected
    )

    # Sync prefix to prefix NIC
    net_3 = net_api_conf.SYNC_NETS_DC_1[2][2]
    net_3_ip = ips.pop(0)
    net_3_mask_actual = "255.255.255.255"
    net_3_prefix_expected = net_api_conf.IP_DICT_PREFIX["netmask"]
    prefix_to_prefix_nic = helper.get_dict(
        network=net_3, type_=mask, act=net_3_mask_actual,
        ex=net_3_prefix_expected
    )

    # Sync no IP to IP NIC
    net_4 = net_api_conf.SYNC_NETS_DC_1[2][3]
    net_4_ip = ips.pop(0)
    net_case_4_boot_proto_actual = "STATIC_IP"
    net_case_4_boot_proto_expected = "NONE"
    no_ip_to_ip_nic = helper.get_dict(
        network=net_4, type_=proto, act=net_case_4_boot_proto_actual,
        ex=net_case_4_boot_proto_expected
    )

    # Sync IP to no IP NIC
    net_5 = net_api_conf.SYNC_NETS_DC_1[2][4]
    net_5_ip = ips.pop(0)
    net_5_proto_actual = "NONE"
    net_5_proto_expected = "STATIC_IP"
    ip_to_no_ip_nic = helper.get_dict(
        network=net_5, type_=proto, act=net_5_proto_actual,
        ex=net_5_proto_expected
    )

    # BOND
    # Sync IP to IP BOND
    net_6 = net_api_conf.SYNC_NETS_DC_1[2][5]
    net_6_ip = ips.pop(0)
    net_6_ip_actual = ips.pop(0)
    net_6_ip_expected = net_6_ip
    ip_to_ip_bond = helper.get_dict(
        network=net_6, type_=ip, act=net_6_ip_actual, ex=net_6_ip_expected
    )

    # Sync mask to mask BOND
    net_7 = net_api_conf.SYNC_NETS_DC_1[2][6]
    net_7_ip = ips.pop(0)
    net_7_mask_actual = "255.255.255.255"
    net_7_mask_expected = net_api_conf.IP_DICT_NETMASK["netmask"]
    mask_to_mask_bond = helper.get_dict(
        network=net_7, type_=mask, act=net_7_mask_actual,
        ex=net_7_mask_expected
    )

    # Sync prefix to prefix BOND
    net_8 = net_api_conf.SYNC_NETS_DC_1[2][7]
    net_8_ip = ips.pop(0)
    net_8_mask_actual = "255.255.255.255"
    net_8_prefix_expected = net_api_conf.IP_DICT_PREFIX["netmask"]
    prefix_to_prefix_bond = helper.get_dict(
        network=net_8, type_=mask, act=net_8_mask_actual,
        ex=net_8_prefix_expected
    )

    # Sync no IP to IP BOND
    net_9 = net_api_conf.SYNC_NETS_DC_1[2][8]
    net_9_ip = ips.pop(0)
    net_case_9_boot_proto_actual = "STATIC_IP"
    net_case_9_boot_proto_expected = "NONE"
    no_ip_to_ip_bond = helper.get_dict(
        network=net_9, type_=proto, act=net_case_9_boot_proto_actual,
        ex=net_case_9_boot_proto_expected
    )

    # Sync IP to no IP BOND
    net_10 = net_api_conf.SYNC_NETS_DC_1[2][9]
    net_10_ip = ips.pop(0)
    net_10_proto_actual = "NONE"
    net_10_proto_expected = "STATIC_IP"
    ip_to_no_ip_bond = helper.get_dict(
        network=net_10, type_=proto, act=net_10_proto_actual,
        ex=net_10_proto_expected
    )

    # manage_ip_and_refresh_capabilities params
    # Network, IP, mask, set_ip
    manage_ip_list = [
        # NIC
        (net_1, net_1_ip_actual, None),
        (net_2, None, net_2_mask_actual),
        (net_3, None, net_3_mask_actual),
        (net_4, net_4_ip, None),
        (net_5, None, None),

        # BOND
        (net_6, net_6_ip_actual, None),
        (net_7, None, net_7_mask_actual),
        (net_8, None, net_8_mask_actual),
        (net_9, net_9_ip, None),
        (net_10, None, None)
    ]

    # setup_networks_fixture params
    bond_1 = "bond21"
    bond_2 = "bond22"
    bond_3 = "bond23"
    bond_4 = "bond24"
    bond_5 = "bond25"
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "ip": {
                    "1": {
                        "address": net_1_ip,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            net_2: {
                "nic": 2,
                "network": net_2,
                "ip": {
                    "1": {
                        "address": net_2_ip,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            net_3: {
                "nic": 3,
                "network": net_3,
                "ip": {
                    "1": {
                        "address": net_3_ip
                    }
                }
            },
            net_4: {
                "nic": 4,
                "network": net_4,
            },
            net_5: {
                "nic": 5,
                "network": net_5,
                "ip": {
                    "1": {
                        "address": net_5_ip,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            bond_1: {
                "nic": bond_1,
                "slaves": [6, 7],
                "network": net_6,
                "ip": {
                    "1": {
                        "address": net_6_ip,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [8, 9],
                "network": net_7,
                "ip": {
                    "1": {
                        "address": net_7_ip,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [10, 11],
                "network": net_8,
                "ip": {
                    "1": {
                        "address": net_8_ip,
                    }
                }
            },
            bond_4: {
                "nic": bond_4,
                "slaves": [12, 13],
                "network": net_9,
            },
            bond_5: {
                "nic": bond_5,
                "slaves": [14, 15],
                "network": net_10,
                "ip": {
                    "1": {
                        "address": net_10_ip,
                        "netmask": "255.255.255.0",
                    }
                }
            },
        }
    }

    @tier2
    @pytest.mark.parametrize(
        "compare_dict",
        [
            # Sync over NIC
            pytest.param(ip_to_ip_nic, marks=(polarion("RHEVM3-13999"))),
            pytest.param(mask_to_mask_nic, marks=(polarion("RHEVM3-14000"))),
            pytest.param(
                prefix_to_prefix_nic, marks=(polarion("RHEVM3-14001"))
            ),
            pytest.param(no_ip_to_ip_nic, marks=(polarion("RHEVM3-14009"))),
            pytest.param(ip_to_no_ip_nic, marks=(polarion("RHEVM3-14011"))),

            # Sync over BOND
            pytest.param(ip_to_ip_bond, marks=(polarion("RHEVM3-14002"))),
            pytest.param(mask_to_mask_bond, marks=(polarion("RHEVM3-14003"))),
            pytest.param(
                prefix_to_prefix_bond, marks=(polarion("RHEVM3-14004"))
            ),
            pytest.param(no_ip_to_ip_bond, marks=(polarion("RHEVM3-14010"))),
            pytest.param(ip_to_no_ip_bond, marks=(polarion("RHEVM3-14012"))),
        ],
        ids=[
            # Sync over NIC
            "Change_IP_on_NIC",
            "Change_netmask_on_NIC",
            "Change_prefix_on_NIC",
            "Add_IP_to_NIC",
            "Remove_IP_from_NIC",

            # Sync over BOND
            "Change_IP_on_BOND",
            "Change_netmask_on_BOND",
            "Change_prefix_on_BOND",
            "Add_IP_to_BOND",
            "Remove_IP_from_BOND",
        ]
    )
    def test_unsync_network_ip_mask_prefix_proto(self, compare_dict):
        """
        1. Check that the network is un-sync and the sync reason is different
           IP, netmask or boot protocol
        2. Sync the network
        """
        network = compare_dict.keys()[0]
        type_ = compare_dict.get(network).keys()[0]
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different %s %s", network, type_, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(
            net_sync_reason=compare_dict
        )
        testflow.step("Sync the network %s", network)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[network]
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    update_host_to_another_cluster.__name__
)
class TestHostNetworkApiSync03(NetworkTest):
    """
    All tests on NIC and BOND
    Check sync/un-sync for:
     1. Changed QoS
     2. No QoS to QoS
     3. QoS to no QoS
    Sync the network
    """
    # Types
    share = net_api_conf.AVERAGE_SHARE_STR
    limit = net_api_conf.AVERAGE_LIMIT_STR
    real = net_api_conf.AVERAGE_REAL_STR
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": net_api_conf.SYNC_DICT_1_CASE_3,
        },
        "2": {
            "data_center": net_api_conf.SYNC_DC,
            "clusters": [net_api_conf.SYNC_CL],
            "networks": net_api_conf.SYNC_DICT_2_CASE_3,
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc, net_api_conf.SYNC_DC]

    # NIC
    # Sync QoS to QoS NIC
    net_1 = net_api_conf.SYNC_NETS_DC_1[3][0]
    net_1_share_nic = helper.get_dict(network=net_1, type_=share)
    net_1_limit_nic = helper.get_dict(network=net_1, type_=limit)
    net_1_real_nic = helper.get_dict(network=net_1, type_=real)
    qos_to_qos_nic = [net_1_share_nic, net_1_limit_nic, net_1_real_nic]

    # Sync no QoS to QoS NIC
    net_2 = net_api_conf.SYNC_NETS_DC_1[3][1]
    net_2_share_nic = helper.get_dict(network=net_2, type_=share)
    net_2_limit_nic = helper.get_dict(network=net_2, type_=limit)
    net_2_real_nic = helper.get_dict(network=net_2, type_=real)
    no_qos_to_qos_nic = [net_2_share_nic, net_2_limit_nic, net_2_real_nic]

    # Sync QoS to no QoS NIC
    net_3 = net_api_conf.SYNC_NETS_DC_1[3][2]
    net_3_share_nic = helper.get_dict(network=net_3, type_=share)
    net_3_limit_nic = helper.get_dict(network=net_3, type_=limit)
    net_3_real_nic = helper.get_dict(network=net_3, type_=real)
    qos_to_no_qos_nic = [net_3_share_nic, net_3_limit_nic, net_3_real_nic]

    # BOND
    # Sync QoS to QoS BOND
    net_4 = net_api_conf.SYNC_NETS_DC_1[3][3]
    net_4_share_nic = helper.get_dict(network=net_4, type_=share)
    net_4_limit_nic = helper.get_dict(network=net_4, type_=limit)
    net_4_real_nic = helper.get_dict(network=net_4, type_=real)
    qos_to_qos_bond = [net_4_share_nic, net_4_limit_nic, net_4_real_nic]

    # Sync no QoS to QoS BOND
    net_5 = net_api_conf.SYNC_NETS_DC_1[3][4]
    net_5_share_nic = helper.get_dict(network=net_5, type_=share)
    net_5_limit_nic = helper.get_dict(network=net_5, type_=limit)
    net_5_real_nic = helper.get_dict(network=net_5, type_=real)
    no_qos_to_qos_bond = [net_5_share_nic, net_5_limit_nic, net_5_real_nic]

    # Sync QoS to no QoS BOND
    net_6 = net_api_conf.SYNC_NETS_DC_1[3][5]
    net_6_share_nic = helper.get_dict(network=net_6, type_=share)
    net_6_limit_nic = helper.get_dict(network=net_6, type_=limit)
    net_6_real_nic = helper.get_dict(network=net_6, type_=real)
    qos_to_no_qos_bond = [net_6_share_nic, net_6_limit_nic, net_6_real_nic]

    # setup_networks_fixture params
    bond_1 = "bond31"
    bond_2 = "bond32"
    bond_3 = "bond33"
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "datacenter": conf.DC_0
            },
            net_2: {
                "nic": 2,
                "network": net_2,
                "datacenter": conf.DC_0
            },
            net_3: {
                "nic": 3,
                "network": net_3,
                "datacenter": conf.DC_0
            },
            bond_1: {
                "nic": bond_1,
                "slaves": [4, 5],
                "network": net_4,
                "datacenter": conf.DC_0
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [6, 7],
                "network": net_5,
                "datacenter": conf.DC_0
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [8, 9],
                "network": net_6,
                "datacenter": conf.DC_0
            },
        }
    }

    @tier2
    @pytest.mark.parametrize(
        "compare_dicts",
        [
            # Sync over NIC
            pytest.param(qos_to_qos_nic, marks=(polarion("RHEVM3-14026"))),
            pytest.param(no_qos_to_qos_nic, marks=(polarion("RHEVM3-14027"))),
            pytest.param(qos_to_no_qos_nic, marks=(polarion("RHEVM3-14028"))),

            # Sync over BOND
            pytest.param(qos_to_qos_bond, marks=(polarion("RHEVM3-14029"))),
            pytest.param(
                no_qos_to_qos_bond, marks=(polarion("RHEVM3-14030"))
            ),
            pytest.param(
                qos_to_no_qos_bond, marks=(polarion("RHEVM3-14031"))
            ),
        ],
        ids=[
            # Sync over NIC
            "Change_QoS_on_NIC",
            "Add_QoS_to_NIC",
            "Remove_QoS_from_NIC",

            # Sync over BOND
            "Change_QoS_on_BOND",
            "Add_QoS_to_BOND",
            "Remove_QoS_from_BOND",
        ]
    )
    def test_unsync_network_qos(self, compare_dicts):
        """
        1. Check that the network is un-sync and the sync reasons changed QoS
        2. Sync the network
        """
        network = None
        for compare_dict in compare_dicts:
            network = compare_dict.keys()[0]
            type_ = compare_dict.get(network).keys()[0]
            testflow.step(
                "Check that the network %s is un-sync and the sync reason is "
                "different %s %s", network, type_, compare_dict
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict
            )

        testflow.step("Sync the network %s", network)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[network]
        )
