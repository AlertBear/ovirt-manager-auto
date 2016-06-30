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
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EngineTypeError
from rhevmtests import config

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
        self.assertTrue(status, 'Add existing cluster')

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
        self.assertTrue(status, 'Add cluster - wrong cpu')

    @attr(tier=1)
    def test_search_cluster(self):
        """
        Positive - send a query to search for cluster
        """
        logger.info('Search cluster by name')
        partial_cl_name = config.CLUSTER_NAME[0][:10]+'*'
        status = ll_cluster.searchForCluster(
            positive=True, query_key='name', query_val=partial_cl_name,
            key_name='name'
        )
        self.assertTrue(status, 'Search cluster by name')

    @attr(tier=1)
    def test_search_cluster_case_insensitive(self):
        """
        Positive - send a query to search for cluster case insensitive
        """
        logger.info('Search cluster by name - case insensitive')
        partial_cl_name = config.CLUSTER_NAME[0][:10]+'*'
        lst = [w[0].upper() + w[1:] for w in partial_cl_name.split('_')]
        partial_cl_name = "_".join(lst)
        status = ll_cluster.searchForCluster(
            positive=True, query_key='name', query_val=partial_cl_name,
            key_name='name', case_sensitive=False
        )
        self.assertTrue(status, 'Search cluster by name - case insensitive')

    @attr(tier=1)
    def test_search_cluster_max_matches(self):
        """
        Positive - send query to search for cluster with max matches parameter
        """
        logger.info('Search cluster by name - max matches')
        partial_cl_name = config.CLUSTER_NAME[0][:10]+'*'
        status = ll_cluster.searchForCluster(
            positive=True, query_key='name', query_val=partial_cl_name,
            key_name='name', max=1
        )
        self.assertTrue(status, 'Search cluster by name - max matches')

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
        self.assertTrue(status, 'Update cluster name')

        logger.info('Revert cluster name update')
        status = ll_cluster.updateCluster(
            positive=True, name=old_name, cluster=new_name
        )
        self.assertTrue(status, 'Revert cluster name update')

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
        self.assertTrue(status, 'Update cluster description')
        logger.info('Clear cluster description')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name, description=''
        )
        self.assertTrue(status, 'Clear cluster description')

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
        self.assertTrue(status, 'Update cluster on error behavior')
        logger.info('Revert cluster on error behavior')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name, on_error=old_on_error
        )
        self.assertTrue(status, 'Revert cluster on error behavior')

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
        self.assertTrue(status, 'Add data center')

        logger.info('Update cluster data center')
        test_status = ll_cluster.updateCluster(
            positive=False, cluster=self.cluster_name,
            data_center='test_data_center'
        )
        remove_status = ll_dc.remove_datacenter(
            positive=True, datacenter='test_data_center'
        )
        self.assertTrue(remove_status, 'Remove data center')
        self.assertTrue(test_status, 'Update cluster data center')

    @attr(tier=1)
    def test_update_cluster_memory_overcommit(self):
        """
        verify update cluster functionality
        update cluster specific memory overcommit & revert the change
        allowed values- 100/150/200% (in the UI), but all positive in API
        """
        cluster = ll_cluster.get_cluster_object(self.cluster_name)
        old_ovrcmt = cluster.get_memory_policy().get_overcommit().get_percent()
        logger.info('Update cluster - memory overcommit')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name, mem_ovrcmt_prc='77'
        )
        self.assertTrue(status, 'Update cluster memory overcommit')
        logger.info('Check cluster - memory overcommit')
        status = ll_cluster.checkClusterParams(
            positive=True, cluster=self.cluster_name, mem_ovrcmt_prc='77'
        )
        self.assertTrue(status, 'Check cluster - memory overcommit')

        logger.info('Revert cluster memory overcommit update')
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name, mem_ovrcmt_prc=old_ovrcmt
        )
        self.assertTrue(status, 'Revert cluster memory overcommit')

        logger.info('Check cluster - revert memory overcommit')
        status = ll_cluster.checkClusterParams(
            positive=True, cluster=self.cluster_name,
            mem_ovrcmt_prc=old_ovrcmt
        )
        self.assertTrue(status, 'Check cluster - Revert memory overcommit')

    @attr(tier=2)
    @bz({'1301353': {}})
    def test_update_cluster_memory_overcommit_to_negative_value(self):
        """
        Negative - verify update cluster functionality
        update cluster specific memory overcommit & revert the change
        should fail - only positive numbers are allowed
        """
        cluster = ll_cluster.get_cluster_object(self.cluster_name)
        old_ovrcmt = cluster.get_memory_policy().get_overcommit().get_percent()
        logger.info('Update cluster - memory overcommit')
        status = ll_cluster.updateCluster(
            positive=False, cluster=self.cluster_name,
            data_center=self.dc_name, mem_ovrcmt_prc='-7'
        )
        self.assertTrue(status, 'Update cluster memory overcommit')
        logger.info('Check cluster - memory overcommit')
        status = ll_cluster.checkClusterParams(
            positive=False, cluster=self.cluster_name,
            mem_ovrcmt_prc=old_ovrcmt
        )

        self.assertTrue(status, 'Check cluster - memory overcommit')

    @attr(tier=2)
    @bz({'1315657': {'engine': ['cli']}})
    def test_update_cluster_high_threshold_out_of_range(self):
        """
        Negative - verify update cluster functionality
        update the cluster with high threshold out of range
        need to check if any parameter changed
        """
        logger.info('Update cluster - high threshold out of range')
        update_status = ll_cluster.updateCluster(
            positive=False, cluster=self.cluster_name, cpu=config.CPU_NAME,
            data_center=self.dc_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='21', thrhld_high='110', duration='240'
        )
        self.assertTrue(
            update_status, 'Update cluster - high threshold out of range'
        )
        self.assertTrue(
            self.set_thresholds_to_default(),
            'Revert cluster - high threshold out of range'
        )

    @attr(tier=2)
    @bz({'1315657': {'engine': ['cli']}})
    def test_update_cluster_low_threshold_out_of_range(self):
        """
        Negative - verify update cluster functionality
        update the cluster with low threshold out of range
        need to check if any parameter changed
        """
        logger.info('Update cluster - low threshold out of range')
        update_status = ll_cluster.updateCluster(
            positive=False, cluster=self.cluster_name, cpu=config.CPU_NAME,
            data_center=self.dc_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='-1', thrhld_high='60', duration='240'
        )
        self.assertTrue(
            update_status, 'Update cluster - low threshold out of range'
        )
        self.assertTrue(
            self.set_thresholds_to_default(),
            'Revert cluster - low threshold out of range'
        )

    @bz({'1315657': {'engine': ['cli']}})
    @attr(tier=1)
    def test_update_cluster_thresholds_power_saving(self):
        """
        Positive - verify update cluster functionality
        update the cluster with specific thresholds relevant to power_saving
        """
        logger.info('Update cluster - power_saving thresholds')
        update_status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='21', thrhld_high='61', duration='240'
        )
        self.assertTrue(
            update_status, 'Update cluster - power_saving thresholds'
        )
        logger.info('Check cluster - power_saving thresholds')
        check_status = ll_cluster.checkClusterParams(
            positive=True, cluster=self.cluster_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='21', thrhld_high='61', duration='240'
        )
        self.assertTrue(
            check_status, 'Check cluster - power_saving thresholds'
        )

    @bz({'1315657': {'engine': ['cli']}})
    @attr(tier=1)
    def test_update_cluster_threshold_evenly_distributed(self):
        """
        Positive - verify update cluster functionality
        update cluster with specific thresholds relevant to evenly_distributed
        """
        logger.info('Update cluster - evenly_distributed thresholds')
        even_distribute = config.ENUMS['scheduling_policy_evenly_distributed']
        status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            data_center=self.dc_name,
            scheduling_policy=even_distribute,
            thrhld_high='61', duration='240'
        )
        self.assertTrue(status,
                        'Update cluster - evenly_distributed threshold')
        logger.info('Check cluster - evenly_distributed threshold')
        status = ll_cluster.checkClusterParams(
            positive=True, cluster=self.cluster_name,
            scheduling_policy=even_distribute,
            thrhld_high='61', duration='240'
        )
        self.assertTrue(
            status, 'Check cluster - evenly_distributed threshold'
        )

    @bz({'1315657': {'engine': ['cli']}})
    @attr(tier=1)
    def test_update_cluster_scheduling_policy(self):
        """
        Positive - verify update cluster functionality
        update the cluster scheduling policy from evenly_distributed
        to power_saving
        """

        logger.info('Update cluster - scheduling policy')
        update_status = ll_cluster.updateCluster(
            positive=True, cluster=self.cluster_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20'
        )

        logger.info('Check cluster - scheduling policy')
        check_status = ll_cluster.checkClusterParams(
            positive=True, cluster=self.cluster_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20'
        )

        self.assertTrue(update_status, 'Update cluster - scheduling policy')
        self.assertTrue(check_status, 'Check cluster - scheduling policy')
        self.assertTrue(
            self.set_thresholds_to_default(), 'Restore - scheduling policy'
        )

    @bz({'1315657': {'engine': ['cli']}})
    @attr(tier=2)
    def test_update_cluster_bad_threshold_range(self):
        """
        Negative - try to set thrhld_low > thrhld_high
        need to check if any parameter changed
        """
        logger.info('Update cluster - bad threshold range')
        update_status = ll_cluster.updateCluster(
            positive=False, cluster=self.cluster_name,
            scheduling_policy=config.ENUMS['scheduling_policy_power_saving'],
            thrhld_low='60', thrhld_high='20'
        )
        self.assertTrue(update_status, 'Update cluster - bad threshold range')
        self.assertTrue(
            self.set_thresholds_to_default(),
            'Revert cluster - bad threshold range'
        )

    @attr(tier=1)
    def test_check_cluster_capabilities(self):
        """
        Positive - check cluster capabilities property functionality
        """
        logger.info(
            "Check cluster capabilities property contains "
            "\'Transparent-Huge-Pages Memory Policy\'"
        )
        version_major = str(config.COMP_VERSION).split(".")[0]
        version_minor = str(config.COMP_VERSION).split(".")[1]
        xpathMatch = XPathMatch(ll_cluster.CLUSTER_API)
        expr = 'count(/capabilities/version[@major=' + version_major + \
               ' and @minor=' + version_minor + ']/ \
               features/feature/name \
               [text()="Transparent-Huge-Pages Memory Policy"])'
        try:
            status = xpathMatch(True, 'capabilities', expr)
            self.assertTrue(status, 'Check cluster capabilities property')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')
