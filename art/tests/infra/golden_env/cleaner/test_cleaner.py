import logging

from art.unittest_lib import BaseTestCase, testflow

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    clusters as ll_clusters,
    external_providers as ll_ep,
)
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    clusters as hl_clusters,
)

import golden_env.config as config


LOGGER = logging.getLogger(__name__)


class CleanGoldenEnv(BaseTestCase):

    __test__ = True

    def test_clean_dc(self):
        """
        Clean the GE. For each DC (including default) list the attached
        clusters and hosts, remove SDs connected to DC and DC itself.
        Remove all hosts and clusters listed. In case there were clusters
        unattached to DC, they and the hosts attached to them
        will also be removed.
        """
        for dc in ll_dc.get_datacenters_list():
            testflow.step("Clean datacenter: %s", dc.get_name())
            hl_dc.clean_datacenter(
                True,
                dc.name,
                vdc=config.VDC,
                vdc_password=config.VDC_PASSWORD
            )
        for cluster in ll_clusters.get_cluster_list():
            hosts_to_remove = (
                hl_clusters.get_hosts_connected_to_cluster(
                    cluster.get_id()
                )
            )
            for host in hosts_to_remove:
                testflow.step(
                    "Remove host: %s from cluster: %s", host.get_name(),
                    cluster.get_name()
                )
                ll_hosts.removeHost(
                    positive=True, host=host.get_name(), deactivate=True
                )
            testflow.step("Remove cluster: %s", cluster.get_name())
            ll_clusters.removeCluster(True, cluster.get_name())
        for glance_ep in ll_ep.get_glance_ep_objs():
            testflow.step(
                "Remove glance image external provider: %s",
                glance_ep.get_name()
            )
            ll_ep.remove_glance_ep(glance_ep.get_name())
        for cinder_ep in ll_ep.get_cinder_ep_objs():
            testflow.step(
                "Remove cinder volume external provider: %s",
                cinder_ep.get_name()
            )
            ll_ep.remove_cinder_ep(cinder_ep.get_name())
