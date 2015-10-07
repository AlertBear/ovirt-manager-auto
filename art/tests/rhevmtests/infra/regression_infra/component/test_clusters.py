'''
Created on June 3, 2014

@author: ncredi
'''

import logging

from art.test_handler.tools import bz  # pylint: disable=E0611
from art.unittest_lib import attr

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError

from rhevmtests.infra.regression_infra import config
from rhevmtests.infra.regression_infra import help_functions

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


def setup_module():
    """
    Setup prerequisites for testing cluster functionality:
    create data center
    """
    help_functions.utils.reverse_env_list = []
    help_functions.utils.add_dc()


def teardown_module():
    """
    Tear down prerequisites for testing cluster functionality:
    remove data center
    """
    help_functions.utils.clean_environment()


@attr(team='automationInfra', tier=1)
class TestCaseCluster(TestCase):
    """
    Cluster sanity tests for basic functionality
    """

    __test__ = True

    cluster_name = config.STORAGE_DOMAIN_NAME

    @classmethod
    def teardown_class(cls):
        """
        Clear the environment
        Remove cluster if it still exists
        """
        logger.info('Remove clusters in case not removed in the tests')
        clusters_to_remove = [cls.cluster_name, config.CLUSTER_2_NAME,
                              config.CLUSTER_3_NAME, config.CLUSTER_4_NAME]

        for claster_name in clusters_to_remove:
            try:
                clusters.removeCluster(positive=False, cluster=claster_name)
            except EntityNotFound:
                logger.info(
                    'Failed to remove cluster %s - this is expected if: '
                    '1. remove clusters test passed successfully '
                    '2. add cluster tests failed', claster_name
                )

    def test01_add_cluster(self):
        """
        test verifies add cluster functionality
        the test adds a cluster
        """
        logger.info('Add cluster')
        status = clusters.addCluster(positive=True, name=config.CLUSTER_1_NAME,
                                     cpu=config.CPU_NAME,
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMP_VERSION,
                                     on_error='migrate')
        self.assertTrue(status, 'Add cluster')

    def test02_add_existing_cluster(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with the same name & verifies it fails
        """
        logger.info('Add existing cluster')
        status = clusters.addCluster(positive=False, cpu=config.CPU_NAME,
                                     name=config.CLUSTER_1_NAME,
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMP_VERSION,
                                     on_error='migrate')
        self.assertTrue(status, 'Add existing cluster')

    def test03_add_cluster_wrong_cpu(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with wrong cpu name & verifies it fails
        """
        logger.info('Add cluster - wrong cpu')
        status = clusters.addCluster(positive=False, cpu='badConfig',
                                     name=config.CLUSTER_2_NAME,
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMP_VERSION,
                                     on_error='migrate')
        self.assertTrue(status, 'Add cluster - wrong cpu')

    def test04_add_cluster_memory_overcommit(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with specific memory overcommit
        """
        logger.info('Add cluster - specific memory overcommit')
        status = clusters.addCluster(positive=True, name=config.CLUSTER_2_NAME,
                                     cpu=config.CPU_NAME, mem_ovrcmt_prc='75',
                                     data_center=config.DATA_CENTER_1_NAME,
                                     version=config.COMP_VERSION,
                                     on_error='do_not_migrate')
        self.assertTrue(status, 'Add cluster - specific memory overcommit')

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test05_add_cluster_wrong_scheduling_policy(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with wrong scheduling policy
        """
        logger.info('Add cluster - wrong scheduling policy')
        status = clusters.addCluster(
            positive=False, name=config.CLUSTER_3_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMP_VERSION,
            scheduling_policy='badConfig',
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Add cluster - wrong scheduling policy')

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test06_add_cluster_scheduling_policy_power_saving(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with scheduling policy power_saving
        """
        logger.info('Add cluster - scheduling policy power_saving')
        status = clusters.addCluster(
            positive=True, name=config.CLUSTER_3_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMP_VERSION,
            scheduling_policy=ENUMS['scheduling_policy_power_saving'],
            thrhld_low='20', thrhld_high='60', duration='180')
        self.assertTrue(status, 'Add cluster - scheduling policy power_saving')

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test07_add_cluster_scheduling_policy_evenly_distributed(self):
        """
        test verifies add cluster functionality
        the test adds a cluster with scheduling policy evenly_distributed
        """
        logger.info('Add cluster - scheduling policy evenly_distributed')
        status = clusters.addCluster(
            positive=True, name=config.CLUSTER_4_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMP_VERSION,
            scheduling_policy=ENUMS['scheduling_policy_evenly_distributed'],
            thrhld_high='60', duration='180')
        self.assertTrue(status, 'Add cluster - scheduling policy '
                        'evenly_distributed')

    def test08_check_cluster_memory_overcommit(self):
        """
        test verifies check cluster parameters functionality
        the test checks cluster memory over-commit
        """
        logger.info('Check cluster - memory over-commit')
        status = clusters.checkClusterParams(positive=True,
                                             cluster=config.CLUSTER_2_NAME,
                                             mem_ovrcmt_prc='75')
        self.assertTrue(status, 'Check cluster - memory over-commit')

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test09_check_cluster_scheduling_policy_power_saving(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test10_check_cluster_scheduling_policy_evenly_distributed(self):
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

    def test11_search_cluster(self):
        """
        test verifies search cluster functionality
        the test searches a cluster by name
        """
        logger.info('Search cluster by name')
        status = clusters.searchForCluster(positive=True, query_key='name',
                                           query_val='RestCluster*',
                                           key_name='name')
        self.assertTrue(status, 'Search cluster by name')

    def test12_search_cluster_case_insensitive(self):
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

    def test13_search_cluster_max_matches(self):
        """
        test verifies search cluster functionality
        the test searches a cluster by name with max matches parameter
        """
        logger.info('Search cluster by name - max matches')
        status = clusters.searchForCluster(positive=True, query_key='name',
                                           query_val='RestCluster*',
                                           key_name='name', max=2)
        self.assertTrue(status, 'Search cluster by name - max matches')

    def test14_search_cluster_case_insensitive_and_max_matches(self):
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

    def test15_update_cluster_name(self):
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
        self.__class__.cluster_name = new_name

    def test16_update_cluster_description(self):
        """
        test verifies update cluster functionality
        the test updates the cluster description
        """
        logger.info('Update cluster description')
        status = clusters.updateCluster(positive=True,
                                        cluster=self.cluster_name,
                                        description='Cluster Description')
        self.assertTrue(status, 'Update cluster description')

    def test17_update_cluster_on_error(self):
        """
        test verifies update cluster functionality
        the test updates the cluster on error behavior
        """
        logger.info('Update cluster on error behavior')
        status = clusters.updateCluster(positive=True,
                                        cluster=self.cluster_name,
                                        on_error='migrate_highly_available')
        self.assertTrue(status, 'Update cluster on error behavior')

    def test18_update_cluster_data_center(self):
        """
        test verifies update cluster functionality
        the test updates the cluster data center & verifies failure
        'Cannot change Data Center association when editing a Cluster.'
        """
        logger.info('Add data center')
        status = datacenters.addDataCenter(
            positive=True, name=config.DATA_CENTER_2_NAME,
            local=False, version=config.COMP_VERSION)
        self.assertTrue(status, 'Add data center')
        logger.info('Update cluster data center')
        test_status = clusters.updateCluster(
            positive=False, cluster=self.cluster_name,
            data_center=config.DATA_CENTER_2_NAME)
        status = datacenters.removeDataCenter(
            positive=True, datacenter=config.DATA_CENTER_2_NAME)
        self.assertTrue(status, 'Remove data center')
        self.assertTrue(test_status, 'Update cluster data center')

    def test19_update_cluster_memory_overcommit(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test20_update_cluster_high_treshold_out_of_range(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test21_update_cluster_low_treshold_out_of_range(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test22_update_cluster_thersholds_power_saving(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test23_update_cluster_thershold_evenly_ditributed(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test24_update_cluster_scheduling_policy(self):
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test25_update_cluster_bad_treshold_range(self):
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

    def test26_check_cluster_capabilities(self):
        """
        test checks cluster capabilities property functionality
        """
        logger.info('Check cluster capabilities property'
                    'contains \'Transparent-Huge-Pages Memory Policy\'')

        version_major = str(config.COMP_VERSION).split(".")[0]
        version_minor = str(config.COMP_VERSION).split(".")[1]
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

    @bz({'1189095': {'engine': ['cli'], 'version': ['3.5']}})
    def test27_remove_clusters(self):
        """
        test verifies remove cluster functionality
        the test removes all clusters
        """
        logger.info('Remove clusters')
        clusters_to_remove = ','.join([self.cluster_name,
                                       config.CLUSTER_2_NAME,
                                       config.CLUSTER_3_NAME,
                                       config.CLUSTER_4_NAME])
        status = clusters.removeClusters(positive=True,
                                         clusters=clusters_to_remove)
        self.assertTrue(status, 'Remove clusters')
