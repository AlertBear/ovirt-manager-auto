"""
Auto-sync OVN feature tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import config as enp_conf
import helper
import rhevmtests.networking.config as net_conf
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    networks as ll_networks
)
from art.test_handler.tools import bz, polarion
from art.unittest_lib import NetworkTest, tier2, testflow
from rhevmtests.fixtures import (
    create_clusters,
    create_datacenters
)
from fixtures import (
    create_ovn_networks_on_provider,
    get_provider_connection,
    set_auto_sync_time,
    set_cluster_external_network_provider
)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    set_cluster_external_network_provider.__name__,
    set_auto_sync_time.__name__,
    create_datacenters.__name__,
    create_clusters.__name__,
    get_provider_connection.__name__,
    create_ovn_networks_on_provider.__name__
)
class TestOVNAutoSync(NetworkTest):
    """
    1. Create OVN network on OVN provider
    2. Update OVN network name property on OVN provider
    3. Edit of cluster default network provider
    4. Import of OVN network with subnet with multiple DC and cluster scenarios
    5. Delete OVN network from provider
    6. Auto-sync bulk of 30 OVN networks
    """
    # Common settings
    dc = net_conf.DC_0
    cl = net_conf.CL_0
    provider_name = enp_conf.OVN_PROVIDER_NAME

    # Common network among multiple tests
    auto_sync_net = enp_conf.OVN_AUTO_SYNC_NET
    auto_sync_subnet = enp_conf.OVN_AUTO_SYNC_SUBNET

    # Edit cluster external network provider test
    edit_cluster_dc = enp_conf.OVN_AUTO_SYNC_EDIT_ENP_TEST_DC
    edit_cluster_cl = enp_conf.OVN_AUTO_SYNC_EDIT_ENP_TEST_CL

    # create_datacenters fixture parameters
    datacenters_dict = enp_conf.OVN_AUTO_SYNC_DCS_SETUP

    # create_clusters fixture parameters
    clusters_dict = enp_conf.OVN_AUTO_SYNC_CLUSTERS_SETUP

    # create_ovn_networks_on_provider fixture parameters
    add_ovn_networks_to_provider = {auto_sync_net: auto_sync_subnet}
    remove_ovn_networks_from_provider = {auto_sync_net: auto_sync_subnet}
    for net_name in enp_conf.OVN_AUTO_SYNC_30_NET_NAMES:
        remove_ovn_networks_from_provider.update({net_name: None})

    @tier2
    @polarion("RHEVM-25030")
    def test_create_ovn_network(self):
        """
        Create OVN network on OVN provider
        """
        assert helper.wait_for_auto_sync(
            networks=[self.auto_sync_net], cluster=self.cl, removal=False
        )

        testflow.step(
            "Verifying that vNIC profile exists for network: %s",
            self.auto_sync_net
        )
        assert ll_networks.get_vnic_profile_from_network(
            network=self.auto_sync_net, vnic_profile=self.auto_sync_net,
            data_center=self.dc, cluster=self.cl
        )

    @tier2
    @polarion("RHEVM-25073")
    @bz({"1539765": {}})
    def test_update_ovn_network_name(self):
        """
        Update OVN network name property on OVN provider
        """
        old_name = self.auto_sync_net
        new_name = self.auto_sync_net + "_new"

        assert enp_conf.PROVIDER_CLS.update_network_properties(
            network=self.auto_sync_net, properties={"name": new_name}
        )
        self.auto_sync_net = new_name
        assert helper.wait_for_auto_sync(
            networks=[self.auto_sync_net], removal=False
        )

        testflow.step(
            "Verifying that the old network name: %s does not exist on engine",
            self.auto_sync_net
        )
        assert old_name not in hl_networks.get_network_names()

        testflow.step(
            "Verifying that vNIC profile exists for network: %s",
            self.auto_sync_net
        )
        assert ll_networks.get_vnic_profile_from_network(
            network=self.auto_sync_net, vnic_profile=self.auto_sync_net,
            data_center=self.dc, cluster=self.cl
        )

    @tier2
    @bz({"1543062": {}})
    @polarion("RHEVM-25119")
    def test_edit_cluster_default_network_provider(self):
        """
        Edit of cluster default network provider
        """
        testflow.step(
            "Updating cluster: %s external network provider to be "
            "'ovirt-provider-ovn'", self.edit_cluster_cl
        )
        assert ll_clusters.updateCluster(
            positive=True, cluster=self.edit_cluster_cl,
            external_network_provider=self.provider_name,
            data_center=self.edit_cluster_dc
        )
        assert helper.wait_for_auto_sync(
            networks=[self.auto_sync_net], cluster=self.edit_cluster_cl,
            removal=False
        )
        self.clusters_dict.pop(self.edit_cluster_cl)

    @tier2
    @polarion("RHEVM-25075")
    def test_import_ovn_network(self):
        """
        Import of OVN network (with subnet) on multiple DC and cluster
            setup scenarios:

        On DC_1:
        - Check that OVN network is imported and attached to cluster with
            'ovirt-provider-ovn'
        - Check that OVN network is not imported to cluster with no default
            provider

        On DC_2:
        - Check that OVN network is imported and attached to cluster with
            'ovirt-provider-ovn'

        On DC_3:
        - Check that OVN network is not imported to cluster with no default
            provider
        """
        for cluster, cluster_properties in self.clusters_dict.items():
            removal = (
                "external_network_provider" not in cluster_properties.keys()
            )
            assert helper.wait_for_auto_sync(
                networks=[self.auto_sync_net], cluster=cluster, removal=removal
            )

    @tier2
    @polarion("RHEVM-25034")
    def test_delete_ovn_network(self):
        """
        Delete OVN network from provider
        """
        assert enp_conf.PROVIDER_CLS.delete_network_by_name(
            network=self.auto_sync_net
        )
        self.remove_ovn_networks_from_provider.pop(self.auto_sync_net)
        assert helper.wait_for_auto_sync(networks=[self.auto_sync_net])

    @tier2
    @polarion("RHEVM-25031")
    def test_autosync_30_networks(self):
        """
        Auto-sync bulk of 30 OVN networks
        """
        # TODO: RFE https://bugzilla.redhat.com/show_bug.cgi?id=1539402
        # Currently we do not support the bulk creation of networks
        # when RFE will be accepted, add_networks should accept list of
        # networks to reduce API calls
        for network_name in enp_conf.OVN_AUTO_SYNC_30_NET_NAMES:
            assert enp_conf.PROVIDER_CLS.add_network(
                network={"name": network_name}
            )

        assert helper.wait_for_auto_sync(
            networks=enp_conf.OVN_AUTO_SYNC_30_NET_NAMES, removal=False
        )
