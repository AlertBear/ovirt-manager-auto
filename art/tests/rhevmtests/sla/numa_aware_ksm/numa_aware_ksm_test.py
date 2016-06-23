"""
NUMA aware KSM test
"""
import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.unittest_lib as u_libs
import rhevmtests.sla.config as sla_conf
import rhevmtests.sla.helpers as sla_helpers
from art.test_handler.tools import polarion  # pylint: disable=E0611


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


class BaseNumaAwareKsm(u_libs.SlaTest):
    """
    Base class for all NUMA aware KSM tests
    """
    ksm_merge_across_nodes = None

    @staticmethod
    def update_merge_across_nodes_parameter(ksm_merge_across_nodes):
        """
        1) Update cluster merge_across_node_parameters
        """
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
        assert ll_hosts.deactivateHost(positive=True, host=sla_conf.HOSTS[0])
        cls.update_merge_across_nodes_parameter(
            ksm_merge_across_nodes=ksm_merge_across_nodes
        )
        assert ll_hosts.activateHost(positive=True, host=sla_conf.HOSTS[0])
        assert sla_helpers.wait_for_numa_aware_ksm_status(
            resource=sla_conf.VDS_HOSTS[0],
            expected_value=ksm_merge_across_nodes
        )


@pytest.mark.usefixtures(
    "update_cluster_merge_across_nodes"
)
@u_libs.attr(tier=2)
class TestNumaAwareKsm1(BaseNumaAwareKsm):
    """
    Activate host under cluster with merge_across_nodes=True
    """
    __test__ = True
    ksm_merge_across_nodes = False

    @polarion("RHEVM3-10734")
    def test_check_numa_aware_ksm_status(self):
        """
        1) Deactivate host
        2) Change cluster merge_across_nodes parameter to True
        3) Activate host
        4) Check host NUMA aware KSM status
        """
        self.check_host_activation(ksm_merge_across_nodes=True)


@pytest.mark.usefixtures(
    "update_cluster_merge_across_nodes"
)
@u_libs.attr(tier=2)
class TestNumaAwareKsm2(BaseNumaAwareKsm):
    """
    Activate host under cluster with merge_across_nodes=False
    """
    __test__ = True
    ksm_merge_across_nodes = True

    @polarion("RHEVM3-10735")
    def test_check_numa_aware_ksm_status(self):
        """
        1) Deactivate host
        2) Change cluster merge_across_nodes parameter to False
        3) Activate host
        4) Check host NUMA aware KSM status
        """
        self.check_host_activation(ksm_merge_across_nodes=False)


@pytest.mark.usefixtures(
    "update_cluster_merge_across_nodes"
)
@u_libs.attr(tier=2)
class TestNumaAwareKsm3(BaseNumaAwareKsm):
    """
    Update cluster merge_across_nodes=True and check if host receive new value
    """
    __test__ = True
    ksm_merge_across_nodes = False

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


@pytest.mark.usefixtures(
    "update_cluster_merge_across_nodes"
)
@u_libs.attr(tier=2)
class TestNumaAwareKsm4(BaseNumaAwareKsm):
    """
    Update cluster merge_across_nodes=False and check if host receive new value
    """
    __test__ = True
    ksm_merge_across_nodes = True

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