"""
-----------------
test_storage_domain
-----------------

@author: Nelly Credi
"""

import logging
from nose.tools import istest
from art.test_handler.tools import bz  # pylint: disable=E0611
from art.unittest_lib import attr

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level import datacenters, storagedomains

from rhevmtests.infra.regression_infra import config
from rhevmtests.infra.regression_infra import help_functions

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


@attr(team='automationInfra', tier=0)
class TestCaseStorageDomain(TestCase):
    """
    Storage domain tests
    """

    __test__ = (config.STORAGE_TYPE == 'nfs')

    sd_name = config.STORAGE_DOMAIN_NAME

    @classmethod
    def setup_class(cls):
        """
        Setup prerequisites for testing scenario:
        create data center, cluster & host
        """
        help_functions.utils.reverse_env_list = []
        help_functions.utils.add_dc()
        help_functions.utils.add_cluster()
        help_functions.utils.add_host()

    @classmethod
    def teardown_class(cls):
        """
        Tear down prerequisites for testing host functionality:
        remove data center, cluster & host
        """
        help_functions.utils.clean_environment()

    @istest
    def t01_create_storage_domain_wrong_type(self):
        """
        test verifies storage domain functionality
        the test adds a storage domain with wrong type & verifies it fails
        """
        logger.info('Add storage domain')
        status = storagedomains.addStorageDomain(
            positive=False, type='bad_config',
            name=config.STORAGE_DOMAIN_NAME,
            storage_type=ENUMS['storage_type_nfs'],
            address=config.DATA_DOMAIN_ADDRESS,
            host=config.HOST_NAME, path=config.DATA_DOMAIN_PATH)
        self.assertTrue(status, 'Add storage domain')

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']},
         '1213393': {'engine': ['cli'], 'version': ['3.6']}})
    def t02_create_storage_domain(self):
        """
        test verifies storage domain functionality
        the test adds a storage domain
        """
        logger.info('Create storage domain')
        status = storagedomains.addStorageDomain(
            positive=True, name=config.STORAGE_DOMAIN_NAME,
            type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_nfs'],
            address=config.DATA_DOMAIN_ADDRESS,
            host=config.HOST_NAME, path=config.DATA_DOMAIN_PATH)
        self.assertTrue(status, 'Create storage domain')

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']},
         '1213393': {'engine': ['cli'], 'version': ['3.6']}})
    def t03_attach_nfs_storage_domain_to_data_center(self):
        """
        test verifies storage domain functionality
        the test attaches storage domain
        """
        logger.info('Attach storage domain')
        status = storagedomains.attachStorageDomain(
            positive=True, datacenter=config.DATA_CENTER_1_NAME,
            storagedomain=config.STORAGE_DOMAIN_NAME)
        self.assertTrue(status, 'Attach storage domain')

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']},
         '1213393': {'engine': ['cli'], 'version': ['3.6']}})
    def t04_update_storage_domain(self):
        """
        test verifies storage domain functionality
        the test updates storage domain name
        """
        logger.info('Update storage domain')
        new_name = config.STORAGE_DOMAIN_NAME + 'Updated'
        status = storagedomains.updateStorageDomain(
            positive=True, storagedomain=config.STORAGE_DOMAIN_NAME,
            name=new_name)
        self.assertTrue(status, 'Update storage domain')
        self.__class__.sd_name = new_name

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']},
         '1213393': {'engine': ['cli'], 'version': ['3.6']}})
    def t05_deactivate_storage_domain(self):
        """
        test verifies storage domain functionality
        the test deactivates a storage domain
        """
        logger.info('Deactivate storage domain')
        status = storagedomains.deactivateStorageDomain(
            positive=True, datacenter=config.DATA_CENTER_1_NAME,
            storagedomain=self.sd_name)
        self.assertTrue(status, 'Deactivate storage domain')

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']},
         '1213393': {'engine': ['cli'], 'version': ['3.6']}})
    def t06_remove_storage_domain(self):
        """
        test verifies storage domain functionality
        the test removes a storage domain
        """
        logger.info('Remove data center')
        status = datacenters.removeDataCenter(
            positive=True, datacenter=config.DATA_CENTER_1_NAME)
        self.assertTrue(status, 'Remove data center')
        logger.info('Remove storage domain')
        status = storagedomains.removeStorageDomain(
            positive=True, storagedomain=self.sd_name,
            host=config.HOST_NAME, format='true')
        self.assertTrue(status, 'Remove storage domain')
        logger.info('Add data center')
