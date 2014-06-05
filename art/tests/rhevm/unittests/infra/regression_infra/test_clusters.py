'''
Created on June 3, 2014

@author: ncredi
'''

from nose.tools import istest
from nose.plugins.attrib import attr

import config

from art.unittest_lib import BaseTestCase as TestCase
import logging
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import clusters
from art.test_handler.exceptions import DataCenterException
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


def setup_module():
    """
    Setup prerequisites for testing cluster functionality:
    create data center
    """
    logger.info('Add data center')
    status = datacenters.addDataCenter(
        positive=True, name=config.DATA_CENTER_1_NAME,
        local=False, version=config.COMPATIBILITY_VERSION)
    if not status:
        raise DataCenterException('Failed to add data center')


def teardown_module():
    """
    Tear down prerequisites for testing cluster functionality:
    remove data center
    """
    logger.info('Remove data center')
    status = datacenters.removeDataCenter(
        positive=True, datacenter=config.DATA_CENTER_1_NAME)
    if not status:
        raise DataCenterException('Failed to remove data center')


@attr(team='automationInfra', tier=0)
class TestCaseCluster(TestCase):
    """
    Cluster sanity tests for basic functionality
    """

    @classmethod
    def teardown_class(cls):
        """
        Clear the environment
        Remove cluster if it still exists
        """
        logger.info('Remove clusters in case not removed in the tests')
        clusters_to_remove = [config.CLUSTER_1_NAME, config.CLUSTER_2_NAME,
                              config.CLUSTER_3_NAME, config.CLUSTER_4_NAME]
        try:
            for claster_name in clusters_to_remove:
                clusters.removeCluster(positive=False, cluster=claster_name)
        except EntityNotFound:
            logger.info('Failed to remove cluster - this is expected if: '
                        '1. remove clusters test passed successfully '
                        '2. add cluster tests failed')

    __test__ = True

    @istest
    def t01_add_cluster(self):
        """
        test verifies add cluster functionality
        the test adds a cluster
        """
        logger.info('Add cluster')
        status = clusters.addCluster(positive=True, name=config.CLUSTER_1_NAME,
                                     cpu=config.CPU_NAME,
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMPATIBILITY_VERSION,
                                     on_error='migrate')
        self.assertTrue(status, 'Add cluster')

    @istest
    def t02_add_existing_cluster(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with the same name & verifies it fails
        """
        logger.info('Add existing cluster')
        status = clusters.addCluster(positive=False, cpu=config.CPU_NAME,
                                     name=config.CLUSTER_1_NAME,
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMPATIBILITY_VERSION,
                                     on_error='migrate')
        self.assertTrue(status, 'Add existing cluster')

    @istest
    def t03_add_cluster_wrong_cpu(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with wrong cpu name & verifies it fails
        """
        logger.info('Add cluster - wrong cpu')
        status = clusters.addCluster(positive=False, cpu='badConfig',
                                     name=config.CLUSTER_2_NAME,
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMPATIBILITY_VERSION,
                                     on_error='migrate')
        self.assertTrue(status, 'Add cluster - wrong cpu')

    @istest
    def t04_add_cluster_memory_overcommit(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with specific memory overcommit
        """
        logger.info('Add cluster - specific memory overcommit')
        status = clusters.addCluster(positive=True, name=config.CLUSTER_2_NAME,
                                     cpu=config.CPU_NAME, mem_ovrcmt_prc='75',
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMPATIBILITY_VERSION,
                                     on_error='do_not_migrate')
        self.assertTrue(status, 'Add cluster - specific memory overcommit')

    @istest
    def t05_add_cluster_wrong_scheduling_policy(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with wrong scheduling policy
        """
        logger.info('Add cluster - wrong scheduling policy')
        status = clusters.addCluster(
            positive=False, name=config.CLUSTER_3_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMPATIBILITY_VERSION,
            scheduling_policy='badConfig',
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Add cluster - wrong scheduling policy')

    @istest
    def t06_add_cluster_scheduling_policy_power_saving(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with scheduling policy power_saving
        """
        logger.info('Add cluster - scheduling policy power_saving')
        status = clusters.addCluster(
            positive=True, name=config.CLUSTER_3_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMPATIBILITY_VERSION,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Add cluster - scheduling policy power_saving')

    @istest
    def t07_add_cluster_scheduling_policy_evenly_distributed(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with scheduling policy evenly_distributed
        """
        logger.info('Add cluster - scheduling policy evenly_distributed')
        status = clusters.addCluster(
            positive=True, name=config.CLUSTER_4_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMPATIBILITY_VERSION,
            scheduling_policy=ENUMS['scheduling_policy_evenly_distributed'],
            thrhld_high='60', duration='180')
        self.assertTrue(status, 'Add cluster - scheduling policy '
                        'evenly_distributed')

    @istest
    def t08_check_cluster_memory_overcommit(self):
        """
        test verifies check cluster parameters functionality
        the test checks cluster memory over-commit
        """
        logger.info('Check cluster - memory over-commit')
        status = clusters.checkClusterParams(positive=True,
                                             cluster=config.CLUSTER_2_NAME,
                                             mem_ovrcmt_prc='75')
        self.assertTrue(status, 'Check cluster - memory over-commit')

    @istest
    def t09_check_cluster_scheduling_policy_power_saving(self):
        """
        test verifies check cluster parameters functionality
        the test checks cluster scheduling policy power_saving
        """
        logger.info('Check cluster - scheduling policy power_saving')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_3_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Check cluster - scheduling policy '
                        'power_saving')

    @istest
    def t10_check_cluster_scheduling_policy_evenly_distributed(self):
        """
        test verifies check cluster parameters functionality
        the test checks cluster scheduling policy evenly_distributed
        """
        logger.info('Check cluster - scheduling policy evenly_distributed')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_4_NAME,
            scheduling_policy=ENUMS['scheduling_policy_evenly_distributed'],
            thrhld_high='60', duration='180')
        self.assertTrue(status, 'Check cluster - scheduling policy '
                        'evenly_distributed')

    @istest
    def t11_search_cluster(self):
        """
        test verifies search cluster functionality
        the test searches a cluster by name
        """
        logger.info('Search cluster by name')
        status = clusters.searchForCluster(positive=True, query_key='name',
                                           query_val='RestCluster*',
                                           key_name='name')
        self.assertTrue(status, 'Search cluster by name')

    @istest
    def t12_search_cluster_case_insensitive(self):
        """
        test verifies search cluster functionality
        the test searches a cluster by name case insensitive
        """
        logger.info('Search cluster by name - case insensitive')
        status = clusters.searchForCluster(positive=True, query_key='name',
                                           query_val='restcluster*',
                                           key_name='name',
                                           case_sensitive=False)
        self.assertTrue(status, 'Search cluster by name - case insensitive')

    @istest
    def t13_search_cluster_max_matches(self):
        """
        test verifies search cluster functionality
        the test searches a cluster by name with max matches parameter
        """
        logger.info('Search cluster by name - max matches')
        status = clusters.searchForCluster(positive=True, query_key='name',
                                           query_val='RestCluster*',
                                           key_name='name', max=2)
        self.assertTrue(status, 'Search cluster by name - max matches')

    @istest
    def t14_search_cluster_case_insensitive_and_max_matches(self):
        """
        test verifies search cluster functionality
        the test searches a cluster by name with max matches parameter
        """
        logger.info('Search cluster by name - case insensitive & max matches')
        status = clusters.searchForCluster(positive=True, query_key='name',
                                           query_val='restcluster*',
                                           key_name='name', max=3,
                                           case_sensitive=False)
        self.assertTrue(status, 'Search cluster by name - '
                        'case insensitive & max matches')

    @istest
    def t15_update_cluster_name(self):
        """
        test verifies update cluster functionality
        the test updates the cluster name &
        than returns it back to the original name
        """
        logger.info('Update cluster name')
        new_name = config.CLUSTER_1_NAME + 'Updated'
        status = clusters.updateCluster(positive=True, name=new_name,
                                        cluster=config.CLUSTER_1_NAME)
        self.assertTrue(status, 'Update cluster name')
        logger.info('Change cluster name back to the default value')
        status = clusters.updateCluster(positive=True, cluster=new_name,
                                        name=config.CLUSTER_1_NAME)
        self.assertTrue(status, 'Update cluster name to default value')

    @istest
    def t16_update_cluster_description(self):
        """
        test verifies update cluster functionality
        the test updates the cluster description
        """
        logger.info('Update cluster description')
        status = clusters.updateCluster(positive=True,
                                        cluster=config.CLUSTER_1_NAME,
                                        description='Cluster Description')
        self.assertTrue(status, 'Update cluster description')

    @istest
    def t17_update_cluster_on_error(self):
        """
        test verifies update cluster functionality
        the test updates the cluster on error behavior
        """
        logger.info('Update cluster on error behavior')
        status = clusters.updateCluster(positive=True,
                                        cluster=config.CLUSTER_1_NAME,
                                        on_error='migrate_highly_available')
        self.assertTrue(status, 'Update cluster on error behavior')

    @istest
    def t18_update_cluster_data_center(self):
        """
        test verifies update cluster functionality
        the test updates the cluster data center to a non existing DC
        & verifies failure
        """
        logger.info('Add data center')
        status = datacenters.addDataCenter(
            positive=True, name=config.DATA_CENTER_2_NAME,
            local=False, version=config.COMPATIBILITY_VERSION)
        self.assertTrue(status, 'Add data center')
        logger.info('Update cluster data center')
        status = clusters.updateCluster(positive=False,
                                        cluster=config.CLUSTER_1_NAME,
                                        data_center=config.DATA_CENTER_2_NAME)
        self.assertTrue(status, 'Remove data center')
        status = datacenters.removeDataCenter(
            positive=True, datacenter=config.DATA_CENTER_2_NAME)
        self.assertTrue(status, 'Remove data center')

    @istest
    def t19_update_cluster_memory_overcommit(self):
        """
        test verifies update cluster functionality
        the test updates the cluster specific memory overcommit
        """
        logger.info('Update cluster - memory overcommit')
        status = clusters.updateCluster(positive=True,
                                        cluster=config.CLUSTER_2_NAME,
                                        data_center=config.DATA_CENTER_1_NAME,
                                        mem_ovrcmt_prc='76')
        self.assertTrue(status, 'Update cluster memory overcommit')

        logger.info('Check cluster - memory overcommit')
        status = clusters.checkClusterParams(positive=True,
                                             cluster=config.CLUSTER_2_NAME,
                                             mem_ovrcmt_prc='76')
        self.assertTrue(status, 'Check cluster - memory overcommit')

    @istest
    def t20_update_cluster_high_treshold_out_of_range(self):
        """
        test verifies update cluster functionality
        the test updates the cluster with high threshold out of range
        """
        logger.info('Update cluster - high threshold out of range')
        status = clusters.updateCluster(
            positive=False, cluster=config.CLUSTER_3_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='21', thrhld_high='110', duration='240')
        self.assertTrue(status, 'Update cluster - high threshold out of range')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_3_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Check cluster - threshold')

    @istest
    def t21_update_cluster_low_treshold_out_of_range(self):
        """
        test verifies update cluster functionality
        the test updates the cluster with low threshold out of range
        """
        logger.info('Update cluster - low threshold out of range')
        status = clusters.updateCluster(
            positive=False, cluster=config.CLUSTER_3_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='-1', thrhld_high='60', duration='240')
        self.assertTrue(status, 'Update cluster - low threshold out of range')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_3_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Check cluster - threshold')

    @istest
    def t22_update_cluster_thersholds_power_saving(self):
        """
        test verifies update cluster functionality
        the test updates the cluster with specific thresholds
        relevant to power_saving
        """
        logger.info('Update cluster - power_saving thresholds')
        status = clusters.updateCluster(
            positive=True, cluster=config.CLUSTER_3_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='21', thrhld_high='61', duration='240')
        self.assertTrue(status, 'Update cluster - power_saving thresholds')

        logger.info('Check cluster - power_saving thresholds')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_3_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='21', thrhld_high='61', duration='240')
        self.assertTrue(status, 'Check cluster - power_saving thresholds')

    @istest
    def t23_update_cluster_thershold_evenly_ditributed(self):
        """
        test verifies update cluster functionality
        the test updates the cluster with specific thresholds
        relevant to evenly_ditributed
        """
        logger.info('Update cluster - evenly_ditributed thresholds')
        status = clusters.updateCluster(
            positive=True, cluster=config.CLUSTER_4_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            scheduling_policy=ENUMS['scheduling_policy_evenly_distributed'],
            thrhld_high='61', duration='240')
        self.assertTrue(status, 'Update cluster - evenly_ditributed threshold')

        logger.info('Check cluster - evenly_distributed threshold')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_4_NAME,
            scheduling_policy=ENUMS['scheduling_policy_evenly_distributed'],
            thrhld_high='61', duration='240')
        self.assertTrue(status, 'Check cluster - evenly_distributed threshold')

    @istest
    def t24_update_cluster_scheduling_policy(self):
        """
        test verifies update cluster functionality
        the test updates the cluster scheduling policy from evenly_ditributed
        to power_saving
        """
        logger.info('Update cluster - scheduling policy')
        status = clusters.updateCluster(
            positive=True, cluster=config.CLUSTER_4_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20')
        self.assertTrue(status, 'Update cluster - scheduling policy')

        logger.info('Check cluster - scheduling policy')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_4_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='61', duration='240')
        self.assertTrue(status, 'Check cluster - scheduling policy')

    @istest
    def t25_update_cluster_bad_treshold_range(self):
        """
        test verifies update cluster functionality
        the test updates the cluster with bad threshold range - low > high
        """
        logger.info('Update cluster - bad threshold range')
        status = clusters.updateCluster(
            positive=False, cluster=config.CLUSTER_4_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='60', thrhld_high='20')
        self.assertTrue(status, 'Update cluster - bad threshold range')
        status = clusters.checkClusterParams(
            positive=True, cluster=config.CLUSTER_4_NAME,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='61', duration='240')
        self.assertTrue(status, 'Check cluster - threshold')

    @istest
    def t26_check_cluster_capabilities(self):
        """
        test checks cluster capabilities property functionality
        """
        logger.info('Check cluster capabilities property'
                    'contains \'Transparent-Huge-Pages Memory Policy\'')

        version_major = str(config.COMPATIBILITY_VERSION).split(".")[0]
        version_minor = str(config.COMPATIBILITY_VERSION).split(".")[1]
        xpathMatch = XPathMatch(clusters.CLUSTER_API)
        expr = 'count(/capabilities/version[@major=' + version_major + \
               ' and @minor=' + version_minor + ']/ \
               features/feature/name \
               [text()="Transparent-Huge-Pages Memory Policy"])'
        try:
            status = xpathMatch(True, 'capabilities', expr)
            self.assertTrue(status, 'Check cluster capabilities property')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    @istest
    def t27_remove_clusters(self):
        """
        test verifies remove cluster functionality
        the test removes all clusters
        """
        logger.info('Remove clusters')
        clusters_to_remove = ','.join([config.CLUSTER_1_NAME,
                                       config.CLUSTER_2_NAME,
                                       config.CLUSTER_3_NAME,
                                       config.CLUSTER_4_NAME])
        status = clusters.removeClusters(positive=True,
                                         clusters=clusters_to_remove)
        self.assertTrue(status, 'Remove clusters')
