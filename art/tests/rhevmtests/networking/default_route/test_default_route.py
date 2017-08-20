#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Default route tests
"""
import pytest

import helper as dr_helper
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as dr_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
    NetworkTest,
)
from fixtures import set_route_to_engine_and_local_host  # noqa: F401
from rhevmtests.fixtures import create_clusters
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    remove_all_networks,
    create_and_attach_networks,
    setup_networks_fixture,
    clean_host_interfaces_fixture_function,
    restore_network_usage,
    update_cluster_network_usages
)


@pytest.mark.usefixtures(
    create_clusters.__name__,
    create_and_attach_networks.__name__,
)
class TestDefaultRoute01(NetworkTest):
    """
    Check that default route as the default role for non ovirtmgmt management
    network
    """
    dc = conf.DC_0
    net = dr_conf.NETS[1][0]
    ext_cluster = dr_conf.EXTRA_CL_NAME
    default_route_usage = conf.DEFAULT_ROUTE_USAGE

    # create_clusters params
    clusters_dict = {
        ext_cluster: {
            "name": ext_cluster,
            "data_center": conf.DC_0,
            "version": conf.COMP_VERSION,
            "cpu": conf.CPU_NAME,
        },
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [ext_cluster],
            "networks": dr_conf.NET_DICT_CASE_01
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier2
    @polarion("RHEVM-21370")
    def test_custom_mgmt_default_route_role(self):
        """
        1. Set default route role to non default management network
        2. Check that the network has default route role
        """
        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.ext_cluster, network=self.net,
            usages=self.default_route_usage
        )
        assert ll_networks.check_network_usage(
            cluster_name=self.ext_cluster, network=self.net,
            attrs=[self.default_route_usage]
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
)
class TestDefaultRoute02(NetworkTest):
    """
    1. Check that default route role require IP configuration when attaching
        to host
    2. Try to remove IP configuration from default route network that is
        attached to host
    """
    dc = conf.DC_0
    cluster = conf.CL_0
    net_1 = dr_conf.NETS[2][0]
    net_2 = dr_conf.NETS[2][1]
    default_route_usage = conf.DEFAULT_ROUTE_USAGE

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": dr_conf.NET_DICT_CASE_02
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            }
        }
    }

    @tier2
    @polarion("RHEVM-21375")
    def test_default_route_require_ip_network_attached(self):
        """
        Check that default route role require IP configuration while the
        network attached to the host
        """
        assert ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster, network=self.net_1,
            usages=self.default_route_usage
        )

    @tier2
    @polarion("RHEVM-21371")
    def test_default_route_require_ip_attach_network(self):
        """
        Check that default route role require IP configuration when attaching
        the network to host
        """
        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster, network=self.net_2,
            usages=self.default_route_usage
        )
        sn_dict = {
            "add": {
                self.net_2: {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2]
                }
            }
        }
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    restore_network_usage.__name__,
    create_and_attach_networks.__name__,
    clean_host_interfaces_fixture_function.__name__
)
class TestDefaultRoute03(NetworkTest):
    """
    1. Set default route network with DHCP
    2. Set default route network with static IP
    """
    dc = conf.DC_0
    cluster = conf.CL_0
    net_1 = dr_conf.NETS[3][0]
    net_2 = dr_conf.NETS[3][1]
    default_route_usage = conf.DEFAULT_ROUTE_USAGE
    ip = None

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": dr_conf.NET_DICT_CASE_03
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # restore_network_usage params
    network_usage = conf.MGMT_BRIDGE
    cluster_usage = conf.CL_0

    @tier2
    @pytest.mark.parametrize(
        ("network", "boot_protocol"),
        [
            pytest.param(*[net_1, "dhcp"], marks=(polarion("RHEVM3-21387"))),
            pytest.param(*[net_2, "static"], marks=(polarion("RHEVM3-21378"))),
        ],
        ids=[
            "With_DHCP",
            "With_static_IP",
        ]
    )
    @bz({"1443292": {}})
    def test_default_route_network(self, network, boot_protocol):
        """
        Set default route network with DHCP
        """
        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster, network=network,
            usages=self.default_route_usage
        )
        ip_dict = {
            "1": {
                "boot_protocol": boot_protocol
            }
        }
        if boot_protocol == "static":
            if not self.ip:
                self.ip = conf.VDS_0_HOST.network.find_ip_by_int(
                    interface=conf.HOST_0_NICS[1]
                )
            assert self.ip

            ip_dict["1"]["netmask"] = "24"
            ip_dict["1"]["address"] = self.ip

        sn_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": ip_dict
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
        assert dr_helper.is_dgw_from_ip_subnet(vds=conf.VDS_0_HOST, ip=self.ip)


@pytest.mark.usefixtures(
    restore_network_usage.__name__,
    create_and_attach_networks.__name__,
    update_cluster_network_usages.__name__,
    setup_networks_fixture.__name__,
)
class TestDefaultRoute04(NetworkTest):
    """
    1. Try to remove IP from network with default route role
    """
    dc = conf.DC_0
    cluster = conf.CL_0
    net_1 = dr_conf.NETS[4][0]
    default_route_usage = conf.DEFAULT_ROUTE_USAGE

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": dr_conf.NET_DICT_CASE_03
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "ip": {
                    "1": {
                        "boot_protocol": "dhcp"
                    }
                }
            }
        }
    }

    # update_cluster_network_usages params
    update_cluster = cluster
    update_cluster_network = net_1
    update_cluster_network_usages = default_route_usage

    # restore_network_usage params
    network_usage = net_1
    cluster_usage = cluster

    @tier2
    @polarion("RHEVM-21377")
    @bz({"1443292": {}})
    def test_remove_ip_from_default_route_network(self):
        """
        Try to remove IP from network with default route role
        """
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": {
                        "1": {
                            "boot_protocol": "none"
                        }
                    }
                }
            }
        }
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
