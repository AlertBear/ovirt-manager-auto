"""
-----------------
test clusters
-----------------

@author: ncredi
"""

import logging

from art.test_handler.tools import bz
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    attr,
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    clusters as ll_cluster,
)
from rhevmtests import config
import rhevmtests.sla.config as sla_conf

logger = logging.getLogger(__name__)


class TestCaseCluster(TestCase):
    """
    Cluster sanity tests for basic functionality
    """

    __test__ = True

    cluster_name = config.CLUSTER_NAME[0]
    dc_name = config.DC_NAME[0]

    def set_thresholds_to_default(self):
        """
        Set thresholds to default cluster
        :return: True if update cluster succeeded False otherwise
        :rtype: bool
        """
        return ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name, scheduling_policy='none'
        )

    @attr(tier=2)
    def test_add_existing_cluster(self):
        """
        Negative - add a cluster with already existing name & verify it fails
        """
        logger.info('Add existing cluster')
        status = ll_cluster.addCluster(
            positive=False, cpu=config.CPU_NAME, name=self.cluster_name,
            data_center=self.dc_name, version=config.COMP_VERSION,
            on_error='migrate'
        )
        assert status, 'Add existing cluster'

    @attr(tier=2)
    def test_add_cluster_wrong_cpu(self):
        """
        Negative - adds a cluster with wrong cpu name & verify it fails
        """
        logger.info('Add cluster - wrong cpu')
        status = ll_cluster.addCluster(
            positive=False, cpu='badConfig', name='test_cluster',
            data_center=self.dc_name, version=config.COMP_VERSION,
            on_error='migrate'
        )
        assert status, 'Add cluster - wrong cpu'

    @attr(tier=1)
    def test_search_cluster(self):
        """
        Positive - send a query to search for cluster
        """
        logger.info('Search cluster by name')
        partial_cl_name = config.CLUSTER_NAME[0][:10] + '*'
        status = ll_cluster.searchForCluster(
            positive=True, query_key='name', query_val=partial_cl_name,
            key_name='name'
        )
        assert status, 'Search cluster by name'

    @attr(tier=1)
    def test_search_cluster_case_insensitive(self):
        """
        Positive - send a query to search for cluster case insensitive
        """
        logger.info('Search cluster by name - case insensitive')
        partial_cl_name = config.CLUSTER_NAME[0][:10] + '*'
        lst = [w[0].upper() + w[1:] for w in partial_cl_name.split('_')]
        partial_cl_name = "_".join(lst)
        status = ll_cluster.searchForCluster(
            positive=True, query_key='name', query_val=partial_cl_name,
            key_name='name', case_sensitive=False
        )
        assert status, 'Search cluster by name - case insensitive'

    @attr(tier=1)
    def test_search_cluster_max_matches(self):
        """
        Positive - send query to search for cluster with max matches parameter
        """
        logger.info('Search cluster by name - max matches')
        partial_cl_name = config.CLUSTER_NAME[0][:10] + '*'
        status = ll_cluster.searchForCluster(
            positive=True, query_key='name', query_val=partial_cl_name,
            key_name='name', max=1
        )
        assert status, 'Search cluster by name - max matches'

    @attr(tier=1)
    def test_update_cluster_name(self):
        """
        Positive - verify update cluster name functionality
        update the cluster name & return it back to the original name
        """
        logger.info('Update cluster name')
        old_name = self.cluster_name
        new_name = old_name + 'Updated'
        status = ll_cluster.updateCluster(
            positive=True, name=new_name, cluster=old_name
        )
        assert status, 'Update cluster name'

        logger.info('Revert cluster name update')
        status = ll_cluster.updateCluster(
            positive=True, name=old_name, cluster=new_name
        )
        assert status, 'Revert cluster name update'

    @attr(tier=1)
    def test_update_cluster_description(self):
        """
        Positive - verify update cluster description functionality
        update the cluster description & then clear it
        """
        logger.info('Update cluster description')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            description='Cluster Description'
        )
        assert status, 'Update cluster description'
        logger.info('Clear cluster description')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name, description=''
        )
        assert status, 'Clear cluster description'

    @attr(tier=1)
    def test_update_cluster_on_error(self):
        """
        Positive - verify update cluster on_error functionality
        update the cluster 'on error' field & revert the change
        """
        old_on_error = "migrate"  # the default value
        logger.info('Update cluster on error behavior')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            on_error='migrate_highly_available'
        )
        assert status, 'Update cluster on error behavior'
        logger.info('Revert cluster on error behavior')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name, on_error=old_on_error
        )
        assert status, 'Revert cluster on error behavior'

    @attr(tier=2)
    def test_update_cluster_data_center(self):
        """
        Negative - verify update cluster functionality
        update cluster data center & verify failure
        'Cannot change Data Center association when editing a Cluster.'
        """
        logger.info('Add data center')
        status = ll_dc.addDataCenter(
            positive=True, name='test_data_center',
            local=False, version=config.COMP_VERSION
        )
        assert status, 'Add data center'

        logger.info('Update cluster data center')
        test_status = ll_cluster.updateCluster(
            positive=False, cluster=self.cluster_name,
            data_center='test_data_center'
        )
        remove_status = ll_dc.remove_datacenter(
            positive=True, datacenter='test_data_center'
        )
        assert remove_status, 'Remove data center'
        assert test_status, 'Update cluster data center'

    @attr(tier=1)
    def test_update_cluster_memory_overcommit(self):
        """
        verify update cluster functionality
        update cluster specific memory overcommit & revert the change
        allowed values- 100/150/200% (in the UI), but all positive in API
        """
        cluster = ll_cluster.get_cluster_object(self.cluster_name)
        old_over_commit_obj = cluster.get_memory_policy().get_over_commit()
        old_over_commit_val = old_over_commit_obj.get_percent()
        logger.info('Update cluster - memory overcommit')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name, mem_ovrcmt_prc=77
        )
        assert status, 'Update cluster memory overcommit'
        logger.info('Check cluster - memory overcommit')
        status = ll_cluster.check_cluster_params(
            positive=True, cluster=self.cluster_name, over_commit=77
        )
        assert status, 'Check cluster - memory overcommit'

        logger.info('Revert cluster memory overcommit update')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name, mem_ovrcmt_prc=old_over_commit_val
        )
        assert status, 'Revert cluster memory overcommit'

        logger.info('Check cluster - revert memory overcommit')
        status = ll_cluster.check_cluster_params(
            positive=True, cluster=self.cluster_name,
            over_commit=old_over_commit_val
        )
        assert status, 'Check cluster - Revert memory overcommit'

    @attr(tier=2)
    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    def test_update_cluster_high_threshold_out_of_range(self):
        """
        Negative - verify update cluster functionality
        update the cluster with high threshold out of range
        need to check if any parameter changed
        """
        logger.info('Update cluster - high threshold out of range')
        update_status = ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            cpu=config.CPU_NAME,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties={
                sla_conf.LOW_UTILIZATION: 21,
                sla_conf.HIGH_UTILIZATION: 110,
                sla_conf.OVER_COMMITMENT_DURATION: 240
            }
        )
        assert update_status, 'Update cluster - high threshold out of range'
        assert self.set_thresholds_to_default(), (
            'Revert cluster - high threshold out of range'
        )

    @attr(tier=2)
    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    def test_update_cluster_low_threshold_out_of_range(self):
        """
        Negative - verify update cluster functionality
        update the cluster with low threshold out of range
        need to check if any parameter changed
        """
        logger.info('Update cluster - low threshold out of range')
        update_status = ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            cpu=config.CPU_NAME,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties={
                sla_conf.LOW_UTILIZATION: -1,
                sla_conf.HIGH_UTILIZATION: 60,
                sla_conf.OVER_COMMITMENT_DURATION: 240
            }
        )
        assert update_status, 'Update cluster - low threshold out of range'
        assert self.set_thresholds_to_default(), (
            'Revert cluster - low threshold out of range'
        )

    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    @attr(tier=1)
    def test_update_cluster_thresholds_power_saving(self):
        """
        Positive - verify update cluster functionality
        update the cluster with specific thresholds relevant to power_saving
        """
        logger.info('Update cluster - power_saving thresholds')
        properties = {
            sla_conf.LOW_UTILIZATION: 21,
            sla_conf.HIGH_UTILIZATION: 61,
            sla_conf.OVER_COMMITMENT_DURATION: 240
        }
        update_status = ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )
        assert update_status, 'Update cluster - power_saving thresholds'
        logger.info('Check cluster - power_saving thresholds')
        check_status = ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )
        assert check_status, 'Check cluster - power_saving thresholds'

    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    @attr(tier=1)
    def test_update_cluster_threshold_evenly_distributed(self):
        """
        Positive - verify update cluster functionality
        update cluster with specific thresholds relevant to evenly_distributed
        """
        logger.info('Update cluster - evenly_distributed thresholds')
        properties = {
            sla_conf.HIGH_UTILIZATION: 61,
            sla_conf.OVER_COMMITMENT_DURATION: 240
        }
        status = ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy=sla_conf.POLICY_EVEN_DISTRIBUTION,
            properties=properties
        )
        assert status, (
            'Update cluster - evenly_distributed threshold'
        )
        logger.info('Check cluster - evenly_distributed threshold')
        status = ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_EVEN_DISTRIBUTION,
            properties=properties
        )
        assert status, 'Check cluster - evenly_distributed threshold'

    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    @attr(tier=1)
    def test_update_cluster_scheduling_policy(self):
        """
        Positive - verify update cluster functionality
        update the cluster scheduling policy from evenly_distributed
        to power_saving
        """

        logger.info('Update cluster - scheduling policy')
        properties = {
            sla_conf.LOW_UTILIZATION: 20
        }
        update_status = ll_cluster.updateCluster(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

        logger.info('Check cluster - scheduling policy')
        check_status = ll_cluster.check_cluster_params(
            positive=True,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties=properties
        )

        assert update_status, 'Update cluster - scheduling policy'
        assert check_status, 'Check cluster - scheduling policy'
        assert self.set_thresholds_to_default(), 'Restore - scheduling policy'

    @bz({'1316456': {}, '1315657': {'engine': ['cli']}})
    @attr(tier=2)
    def test_update_cluster_bad_threshold_range(self):
        """
        Negative - try to set thrhld_low > thrhld_high
        need to check if any parameter changed
        """
        logger.info('Update cluster - bad threshold range')
        update_status = ll_cluster.updateCluster(
            positive=False,
            cluster=self.cluster_name,
            scheduling_policy=sla_conf.POLICY_POWER_SAVING,
            properties={
                sla_conf.LOW_UTILIZATION: 60,
                sla_conf.HIGH_UTILIZATION: 20
            }
        )
        assert update_status, 'Update cluster - bad threshold range'
        assert self.set_thresholds_to_default(), (
            'Revert cluster - bad threshold range'
        )
