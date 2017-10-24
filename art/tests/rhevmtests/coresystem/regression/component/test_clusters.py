"""
-----------------
test clusters
-----------------
"""
import rhevmtests.compute.sla.config as sla_conf
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    clusters as ll_cluster,
)
from art.test_handler.tools import bz
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    testflow,
    tier1,
    tier2,
)
from rhevmtests.config import (
    CLUSTER_NAME as clusters_names,
    COMP_VERSION as comp_version,
    CPU_NAME as cpu_name,
    DC_NAME as dcs_names,
)


class TestCaseCluster(TestCase):
    """
    Cluster sanity tests for basic functionality
    """
    MEMORY_OVER_COMMIT = 77

    cluster_name = clusters_names[0]
    dc_name = dcs_names[0]

    def get_partial_cluster_name(self):
        if len(clusters_names[0]) == 1:
            return clusters_names[0]
        else:
            return clusters_names[0][:len(clusters_names[0]) / 2] + '*'

    def get_mixed_case_partial_cluster_name(self):
        return "_".join([
            w[0].upper() + w[1:]
            for w in self.get_partial_cluster_name().split('_')
        ])

    def set_thresholds_to_default(self):
        """
        Description:
            Set thresholds to default cluster
        Returns:
            bool: True if update cluster succeeded False otherwise
        """
        return ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy='none'
        )

    @tier2
    def test_add_existing_cluster(self):
        """
        Negative - add a cluster with already existing name & verify it fails
        """
        testflow.step('Add existing cluster')
        assert ll_cluster.addCluster(
            positive=False,
            cpu=cpu_name,
            name=self.cluster_name,
            data_center=self.dc_name,
            version=comp_version,
            on_error='migrate'
        )

    @tier2
    def test_add_cluster_wrong_cpu(self):
        """
        Negative - adds a cluster with wrong cpu name & verify it fails
        """
        testflow.step('Add cluster - wrong cpu')
        assert ll_cluster.addCluster(
            positive=False,
            cpu='badConfig',
            name='test_cluster',
            data_center=self.dc_name,
            version=comp_version,
            on_error='migrate'
        )

    @tier1
    def test_search_cluster(self):
        """
        Positive - send a query to search for cluster
        """
        partial_cl_name = self.get_partial_cluster_name()

        testflow.step('Search cluster by name')
        assert ll_cluster.searchForCluster(
            positive=True,
            query_key='name',
            query_val=partial_cl_name,
            key_name='name'
        )

    @tier1
    def test_search_cluster_case_insensitive(self):
        """
        Positive - send a query to search for cluster case insensitive
        """
        partial_cl_name = self.get_mixed_case_partial_cluster_name()

        testflow.step('Search cluster by name - case insensitive')
        assert ll_cluster.searchForCluster(
            positive=True,
            query_key='name',
            query_val=partial_cl_name,
            key_name='name',
            case_sensitive=False
        )

    @tier1
    def test_search_cluster_max_matches(self):
        """
        Positive - send query to search for cluster with max matches parameter
        """
        partial_cl_name = self.get_partial_cluster_name()

        testflow.step('Search cluster by name - max matches')
        assert ll_cluster.searchForCluster(
            positive=True,
            query_key='name',
            query_val=partial_cl_name,
            key_name='name',
            max=1
        )

    @bz({"1451390": {}})
    @tier1
    def test_update_cluster_name(self):
        """
        Positive - verify update cluster name functionality
        update the cluster name & return it back to the original name
        """
        old_name = self.cluster_name
        new_name = old_name + 'Updated'

        testflow.step('Update cluster name')
        assert ll_cluster.updateCluster(
            positive=True,
            name=new_name,
            cluster=old_name
        )

        testflow.step('Revert cluster name update')
        assert ll_cluster.updateCluster(
            positive=True,
            name=old_name,
            cluster=new_name
        )

    @tier1
    def test_update_cluster_description(self):
        """
        Positive - verify update cluster description functionality
        update the cluster description & then clear it
        """
        testflow.step('Update cluster description')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            description='Cluster Description'
        )

        testflow.step('Clear cluster description')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            description=''
        )

    @tier1
    def test_update_cluster_on_error(self):
        """
        Positive - verify update cluster on_error functionality
        update the cluster 'on error' field & revert the change
        """
        old_on_error = "migrate"

        testflow.step('Update cluster on error behavior')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            on_error='migrate_highly_available'
        )

        testflow.step('Revert cluster on error behavior')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            on_error=old_on_error
        )

    @tier2
    def test_update_cluster_data_center(self):
        """
        Negative - verify update cluster functionality
        update cluster data center & verify failure
        'Cannot change Data Center association when editing a Cluster.'
        """
        testflow.step('Add data center')
        assert ll_dc.addDataCenter(
            positive=True,
            name='test_data_center',
            local=False,
            version=comp_version
        )

        testflow.step('Update cluster data center')
        assert ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            data_center='test_data_center'
        )
        assert ll_dc.remove_datacenter(
            positive=True,
            datacenter='test_data_center'
        )

    @tier1
    def test_update_cluster_memory_overcommit(self):
        """
        verify update cluster functionality
        update cluster specific memory overcommit & revert the change
        allowed values- 100/150/200% (in the UI), but all positive in API
        """
        cluster = ll_cluster.get_cluster_object(self.cluster_name)
        old_over_commit_obj = cluster.get_memory_policy().get_over_commit()
        old_over_commit_val = old_over_commit_obj.get_percent()

        testflow.step('Update cluster - memory overcommit')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            mem_ovrcmt_prc=self.MEMORY_OVER_COMMIT
        )

        testflow.step('Check cluster - memory overcommit')
        assert ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            over_commit=self.MEMORY_OVER_COMMIT
        )

        testflow.step('Revert cluster memory overcommit update')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            mem_ovrcmt_prc=old_over_commit_val
        )

        testflow.step('Check cluster - revert memory overcommit')
        assert ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            over_commit=old_over_commit_val
        )

    @tier2
    @bz({'1316456': {}})
    def test_update_cluster_high_threshold_out_of_range(self):
        """
        Negative - verify update cluster functionality
        update the cluster with high threshold out of range
        need to check if any parameter changed
        """
        LOW_UTILIZATION = 21
        HIGH_UTILIZATION = 110
        OVER_COMMITMENT_DURATION = 240

        properties = {
            sla_conf.LOW_UTILIZATION: LOW_UTILIZATION,
            sla_conf.HIGH_UTILIZATION: HIGH_UTILIZATION,
            sla_conf.OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION
        }

        testflow.step('Update cluster - high threshold out of range')
        assert ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            cpu=cpu_name,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )
        assert self.set_thresholds_to_default(), (
            'Revert cluster - high threshold out of range'
        )

    @tier2
    @bz({'1316456': {}})
    def test_update_cluster_low_threshold_out_of_range(self):
        """
        Negative - verify update cluster functionality
        update the cluster with low threshold out of range
        need to check if any parameter changed
        """
        LOW_UTILIZATION = -1
        HIGH_UTILIZATION = 60
        OVER_COMMITMENT_DURATION = 240

        properties = {
            sla_conf.LOW_UTILIZATION: LOW_UTILIZATION,
            sla_conf.HIGH_UTILIZATION: HIGH_UTILIZATION,
            sla_conf.OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION
        }

        testflow.step('Update cluster - low threshold out of range')
        assert ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            cpu=cpu_name,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )
        assert self.set_thresholds_to_default(), (
            'Revert cluster - low threshold out of range'
        )

    @bz({'1316456': {}})
    @tier1
    def test_update_cluster_thresholds_power_saving(self):
        """
        Positive - verify update cluster functionality
        update the cluster with specific thresholds relevant to power_saving
        """
        LOW_UTILIZATION = 21
        HIGH_UTILIZATION = 61
        OVER_COMMITMENT_DURATION = 240

        properties = {
            sla_conf.LOW_UTILIZATION: LOW_UTILIZATION,
            sla_conf.HIGH_UTILIZATION: HIGH_UTILIZATION,
            sla_conf.OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION,
        }

        testflow.step('Update cluster - power_saving thresholds')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

        testflow.step('Check cluster - power_saving thresholds')
        assert ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

    @bz({'1316456': {}})
    @tier1
    def test_update_cluster_threshold_evenly_distributed(self):
        """
        Positive - verify update cluster functionality
        update cluster with specific thresholds relevant to evenly_distributed
        """
        HIGH_UTILIZATION = 61
        OVER_COMMITMENT_DURATION = 240

        properties = {
            sla_conf.HIGH_UTILIZATION: HIGH_UTILIZATION,
            sla_conf.OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION
        }

        testflow.step('Update cluster - evenly_distributed thresholds')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_EVEN_DISTRIBUTION,
            properties=properties
        )

        testflow.step('Check cluster - evenly_distributed threshold')
        assert ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_EVEN_DISTRIBUTION,
            properties=properties
        )

    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    @tier1
    def test_update_cluster_scheduling_policy(self):
        """
        Positive - verify update cluster functionality
        update the cluster scheduling policy from evenly_distributed
        to power_saving
        """
        LOW_UTILIZATION = 20

        properties = {
            sla_conf.LOW_UTILIZATION: LOW_UTILIZATION
        }

        testflow.step('Update cluster - scheduling policy')
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

        testflow.step('Check cluster - scheduling policy')
        assert ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

        assert self.set_thresholds_to_default(), 'Restore - scheduling policy'

    @bz({'1316456': {}})
    @tier2
    def test_update_cluster_bad_threshold_range(self):
        """
        Negative - try to set thrhld_low > thrhld_high
        need to check if any parameter changed
        """
        LOW_UTILIZATION = 60
        HIGH_UTILIZATION = 20

        properties = {
            sla_conf.LOW_UTILIZATION: LOW_UTILIZATION,
            sla_conf.HIGH_UTILIZATION: HIGH_UTILIZATION
        }

        testflow.step('Update cluster - bad threshold range')
        assert ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

        assert self.set_thresholds_to_default(), (
            'Revert cluster - bad threshold range'
        )
