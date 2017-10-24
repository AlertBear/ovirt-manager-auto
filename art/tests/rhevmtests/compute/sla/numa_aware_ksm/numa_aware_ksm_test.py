"""
NUMA aware KSM test
"""
import pytest
import rhevmtests.compute.sla.config as sla_conf
import rhevmtests.compute.sla.helpers as sla_helpers

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier2, SlaTest
from rhevmtests.compute.sla.fixtures import (
    activate_hosts,
    choose_specific_host_as_spm
)

host_as_spm = 2


@pytest.fixture(scope="class", autouse=True)
def update_cluster_merge_across_nodes(request):
    """
    1) Update cluster merge_across_nodes parameter
    """
    ksm_merge_across_nodes = getattr(
        request.node.cls, "ksm_merge_across_nodes"
    )

    def fin():
        """
        1) Disable KSM
        """
        ll_clusters.updateCluster(
            positive=True, cluster=sla_conf.CLUSTER_NAME[0], ksm_enabled=False
        )
    request.addfinalizer(fin)

    assert ll_clusters.updateCluster(
        positive=True,
        cluster=sla_conf.CLUSTER_NAME[0],
        ksm_enabled=True,
        ksm_merge_across_nodes=ksm_merge_across_nodes
    )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    activate_hosts.__name__
)
class BaseNumaAwareKsm(SlaTest):
    """
    Base class for all NUMA aware KSM tests
    """
    ksm_merge_across_nodes = None
    hosts_to_activate_indexes = [0]

    @staticmethod
    def update_merge_across_nodes_parameter(ksm_merge_across_nodes):
        """
        1) Update cluster merge_across_node_parameters
        """
        testflow.step(
            "Update cluster %s merge_across_nodes parameter",
            sla_conf.CLUSTER_NAME[0]
        )
        assert ll_clusters.updateCluster(
            positive=True,
            cluster=sla_conf.CLUSTER_NAME[0],
            ksm_enabled=True,
            ksm_merge_across_nodes=ksm_merge_across_nodes
        )

    @classmethod
    def check_host_activation(cls, ksm_merge_across_nodes):
        """
        1) Deactivate host
        2) Change cluster merge_across_nodes parameter to True
        3) Activate host
        4) Check host NUMA aware KSM status

        Args:
            ksm_merge_across_nodes (bool): NUMA aware KSM parameter
        """
        testflow.step("Deactivate the host %s", sla_conf.HOSTS[0])
        assert ll_hosts.deactivate_host(
            positive=True,
            host=sla_conf.HOSTS[0],
            host_resource=sla_conf.VDS_HOSTS[0]
        )
        cls.update_merge_across_nodes_parameter(
            ksm_merge_across_nodes=ksm_merge_across_nodes
        )
        assert ll_hosts.activate_host(
            positive=True,
            host=sla_conf.HOSTS[0],
            host_resource=sla_conf.VDS_HOSTS[0]
        )
        testflow.step(
            "%s: wait until KSM merge across nodes will be equal to %s",
            sla_conf.VDS_HOSTS[0], ksm_merge_across_nodes
        )
        assert sla_helpers.wait_for_numa_aware_ksm_status(
            resource=sla_conf.VDS_HOSTS[0],
            expected_value=ksm_merge_across_nodes
        )


class TestNumaAwareKsm1(BaseNumaAwareKsm):
    """
    Activate host under cluster with merge_across_nodes=True
    """
    ksm_merge_across_nodes = False

    @tier2
    @polarion("RHEVM3-10734")
    def test_check_numa_aware_ksm_status(self):
        """
        1) Deactivate host
        2) Change cluster merge_across_nodes parameter to True
        3) Activate host
        4) Check host NUMA aware KSM status
        """
        self.check_host_activation(ksm_merge_across_nodes=True)


class TestNumaAwareKsm2(BaseNumaAwareKsm):
    """
    Activate host under cluster with merge_across_nodes=False
    """
    ksm_merge_across_nodes = True

    @tier2
    @polarion("RHEVM3-10735")
    def test_check_numa_aware_ksm_status(self):
        """
        1) Deactivate host
        2) Change cluster merge_across_nodes parameter to False
        3) Activate host
        4) Check host NUMA aware KSM status
        """
        self.check_host_activation(ksm_merge_across_nodes=False)


class TestNumaAwareKsm3(BaseNumaAwareKsm):
    """
    Update cluster merge_across_nodes=True and check if host receive new value
    """
    ksm_merge_across_nodes = False

    @tier2
    @polarion("RHEVM3-10735")
    def test_check_numa_aware_ksm_status(self):
        """
        1) Change cluster merge_across_nodes parameter to True
        2) Check host NUMA aware KSM status
        """
        self.update_merge_across_nodes_parameter(ksm_merge_across_nodes=True)
        assert sla_helpers.wait_for_numa_aware_ksm_status(
            resource=sla_conf.VDS_HOSTS[0],
            expected_value=True
        )


class TestNumaAwareKsm4(BaseNumaAwareKsm):
    """
    Update cluster merge_across_nodes=False and check if host receive new value
    """
    ksm_merge_across_nodes = True

    @tier2
    @polarion("RHEVM3-10735")
    def test_check_numa_aware_ksm_status(self):
        """
        1) Change cluster merge_across_nodes parameter to False
        2) Check host NUMA aware KSM status
        """
        self.update_merge_across_nodes_parameter(ksm_merge_across_nodes=False)
        assert sla_helpers.wait_for_numa_aware_ksm_status(
            resource=sla_conf.VDS_HOSTS[0],
            expected_value=False
        )
