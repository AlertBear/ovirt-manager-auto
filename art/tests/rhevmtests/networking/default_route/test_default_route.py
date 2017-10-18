# -*- coding: utf-8 -*-

"""
Default route tests
"""
import pytest

from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    clusters as ll_clusters
)
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as dr_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    NetworkTest,
)
from rhevmtests.fixtures import create_clusters
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    remove_all_networks,
    create_and_attach_networks,
    setup_networks_fixture,
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
        cluster_obj = ll_clusters.get_cluster_object(
            cluster_name=self.ext_cluster
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=self.net,
            usages=self.default_route_usage
        )
        assert ll_networks.check_network_usage(
            cluster=cluster_obj, network=self.net,
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
        cluster_obj = ll_clusters.get_cluster_object(
            cluster_name=self.cluster
        )
        assert ll_networks.update_cluster_network(
            positive=False, cluster=cluster_obj, network=self.net_1,
            usages=self.default_route_usage
        )

    @tier2
    @polarion("RHEVM-21371")
    def test_default_route_require_ip_attach_network(self):
        """
        Check that default route role require IP configuration when attaching
        the network to host
        """
        cluster_obj = ll_clusters.get_cluster_object(
            cluster_name=self.cluster
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=self.net_2,
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
