'''
Created on May 12, 2014

@author: ncredi
'''

from nose.tools import istest
from nose.plugins.attrib import attr

import config

from art.unittest_lib import BaseTestCase as TestCase
import logging
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import clusters
from art.test_handler.exceptions import DataCenterException, ClusterException
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError

logger = logging.getLogger(__name__)


def setup_module():
    """
    Setup prerequisites for testing host functionality:
    create data center & cluster
    """
    logger.info('Add data center')
    status = datacenters.addDataCenter(
        positive=True, name=config.DATA_CENTER_1_NAME,
        local=False, version=config.COMPATIBILITY_VERSION)
    if not status:
        raise DataCenterException('Failed to add data center')
    logger.info('Add cluster')
    status = clusters.addCluster(positive=True, name=config.CLUSTER_NAME,
                                 cpu=config.CPU_NAME,
                                 data_center=config.DATA_CENTER_1_NAME,
                                 version=config.COMPATIBILITY_VERSION,
                                 on_error='migrate')
    if not status:
        logger.info('Failed to add cluster - clean environment')
        logger.info('Remove data center')
        status = datacenters.removeDataCenter(
            positive=True, datacenter=config.DATA_CENTER_1_NAME)
        if not status:
            raise DataCenterException('Failed to remove data center')
        raise ClusterException('Failed to add cluster')


def teardown_module():
    """
    Tear down prerequisites for testing host functionality:
    remove data center & cluster
    """
    logger.info('Remove cluster')
    status = clusters.removeCluster(positive=True,
                                    cluster=config.CLUSTER_NAME)
    if not status:
        raise ClusterException('Failed to remove cluster')
    logger.info('Remove data center')
    status = datacenters.removeDataCenter(
        positive=True, datacenter=config.DATA_CENTER_1_NAME)
    if not status:
        raise DataCenterException('Failed to remove data center')


@attr(team='automationInfra', tier=0)
class TestCaseHost(TestCase):
    """
    Host sanity tests for basic functionality
    """

    @classmethod
    def teardown_class(cls):
        """
        Clear the environment
        Remove host if it still exists
        """
        logger.info('Remove host in case it was not removed in the tests')
        try:
            hosts.deactivateHost(positive=True, host=config.HOST_NAME)
            hosts.removeHost(positive=True, host=config.HOST_NAME)
        except EntityNotFound:
            logger.info('Failed to remove host - this is expected if: '
                        '1. remove host test passed successfully '
                        '2. add host test failed')

    __test__ = True

    @istest
    def t01_add_host(self):
        """
        test verifies add host functionality
        the test adds a host
        """
        logger.info('Add host')
        status = hosts.addHost(
            positive=True, name=config.HOST_NAME, wait=True, reboot=False,
            root_password=config.VDS_PASSWORD, cluster=config.CLUSTER_NAME,
            vdcPort=config.VDC_PORT)
        self.assertTrue(status, 'Add host')

    @istest
    def t02_check_host_type_property(self):
        """
        test checks host type property functionality
        """
        logger.info('Check host type property')
        xpathMatch = XPathMatch(hosts.HOST_API)
        expr = 'count(/hosts/host[name="%s"]/type/text())' % config.HOST_NAME
        try:
            status = xpathMatch(True, 'hosts', expr)
            self.assertTrue(status, 'Check host type property')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    @istest
    def t03_update_host(self):
        """
        test verifies update host functionality
        the test updates the host name &
        than returns it back to the original name
        """
        logger.info('Update host name')
        new_name = config.HOST_NAME + 'Updated'
        status = hosts.updateHost(positive=True, host=config.HOST_NAME,
                                  name=new_name)
        self.assertTrue(status, 'Update host name')
        logger.info('Change host name back to the default value')
        status = hosts.updateHost(positive=True, host=new_name,
                                  name=config.HOST_NAME)
        self.assertTrue(status, 'Update host name to default value')

    @istest
    def t04_activate_active_host(self):
        """
        test verifies activate activate host functionality
        the test activates an active host & verifies it fails
        """
        logger.info('Activate active host')
        status = hosts.activateHost(positive=False, host=config.HOST_NAME)
        self.assertTrue(status, 'Activate active host')

    @istest
    def t05_set_active_host_to_maintenance(self):
        """
        test verifies set host to maintenance state functionality
        the test sets the host to maintenance mode
        """
        logger.info('Set active host to maintenance')
        status = hosts.deactivateHost(positive=True, host=config.HOST_NAME)
        self.assertTrue(status, 'Set active host to maintenance')

    @istest
    def t06_activate_host(self):
        """
        test verifies activate host functionality
        the test activates a host from maintenance mode
        """
        logger.info('Activate host')
        status = hosts.activateHost(positive=True, host=config.HOST_NAME)
        self.assertTrue(status, 'Activate host')

    @istest
    def t07_remove_host(self):
        """
        test verifies remove host functionality
        the test sets the host to maintenance mode & removes it
        """
        logger.info('Remove host')
        status = hosts.deactivateHost(positive=True, host=config.HOST_NAME)
        self.assertTrue(status, 'Set active host to maintenance')
        status = hosts.removeHost(positive=True, host=config.HOST_NAME)
        self.assertTrue(status, 'Remove host')
