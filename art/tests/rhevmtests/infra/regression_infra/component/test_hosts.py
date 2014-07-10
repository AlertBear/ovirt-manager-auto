'''
Created on May 12, 2014

@author: ncredi
'''

import logging

from nose.tools import istest
from art.unittest_lib import attr

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError

from rhevmtests.infra.regression_infra import config
from rhevmtests.infra.regression_infra import help_functions

logger = logging.getLogger(__name__)


def setup_module():
    """
    Setup prerequisites for testing host functionality:
    create data center & cluster
    """
    help_functions.utils.add_dc()
    help_functions.utils.add_cluster()


def teardown_module():
    """
    Tear down prerequisites for testing host functionality:
    remove data center & cluster
    """
    help_functions.utils.remove_cluster()
    help_functions.utils.remove_dc()


@attr(team='automationInfra', tier=0)
class TestCaseHost(TestCase):
    """
    Host sanity tests for basic functionality
    """

    __test__ = True

    host_name = config.HOST_NAME

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

    @istest
    def t01_add_host(self):
        """
        test verifies add host functionality
        the test adds a host
        """
        logger.info('Add host')
        status = hosts.addHost(
            positive=True, name=config.HOST_NAME, wait=True, reboot=False,
            root_password=config.VDS_PASSWORD, cluster=config.CLUSTER_1_NAME,
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
        new_name = 'Host_updated_name'
        status = hosts.updateHost(positive=True, host=config.HOST_NAME,
                                  name=new_name)
        self.assertTrue(status, 'Update host name')
        self.__class__.host_name = new_name

    @istest
    def t04_activate_active_host(self):
        """
        test verifies activate activate host functionality
        the test activates an active host & verifies it fails
        """
        logger.info('Activate active host')
        status = hosts.activateHost(positive=False,
                                    host=self.host_name)
        self.assertTrue(status, 'Activate active host')

    @istest
    def t05_set_active_host_to_maintenance(self):
        """
        test verifies set host to maintenance state functionality
        the test sets the host to maintenance mode
        """
        logger.info('Set active host to maintenance')
        status = hosts.deactivateHost(positive=True,
                                      host=self.host_name)
        self.assertTrue(status, 'Set active host to maintenance')

    @istest
    def t06_activate_host(self):
        """
        test verifies activate host functionality
        the test activates a host from maintenance mode
        """
        logger.info('Activate host')
        status = hosts.activateHost(positive=True,
                                    host=self.host_name)
        self.assertTrue(status, 'Activate host')

    @istest
    def t07_remove_host(self):
        """
        test verifies remove host functionality
        the test sets the host to maintenance mode & removes it
        """
        logger.info('Remove host')
        status = hosts.deactivateHost(positive=True, host=self.host_name)
        self.assertTrue(status, 'Set active host to maintenance')
        status = hosts.removeHost(positive=True, host=self.host_name)
        self.assertTrue(status, 'Remove host')

    def _add_host_enforce_protocol(self, protocol):
        logger.info('Add host - %s protocol', protocol)
        status = hosts.addHost(
            positive=True, name=config.HOST_NAME, wait=True, reboot=False,
            root_password=config.VDS_PASSWORD, cluster=config.CLUSTER_1_NAME,
            vdcPort=config.VDC_PORT, protocol=protocol)
        self.assertTrue(status, 'Add host - %s protocol' % protocol)
        logger.info('Remove host')
        status = hosts.deactivateHost(positive=True, host=config.HOST_NAME)
        self.assertTrue(status, 'Set active host to maintenance')
        status = hosts.removeHost(positive=True, host=config.HOST_NAME)
        self.assertTrue(status, 'Remove host')

    @istest
    def t08_add_host_stomp_protocol(self):
        self._add_host_enforce_protocol("stomp")

    @istest
    def t09_add_host_xml_protocol(self):
        self._add_host_enforce_protocol("xml")
