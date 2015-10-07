"""
-----------------
test_data_centers
-----------------
this module used for test data center creation, modification and deletion.
to run it via command in local environment you should use the following
command:
~/git/ART/art $ ./run.py -conf ../../jenkins/qe/conf/3.4-regression_mixed.conf

@author: Kobi Hakimi
"""
import logging

from art.unittest_lib import attr

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level.datacenters import datacenters

from rhevmtests.infra.regression_infra import config

logger = logging.getLogger(__name__)


def setup_module():
    """
    Nothing for setup.
    """


def teardown_module():
    """
    Nothing for teardown.
    """


def create_datacenter(is_positive, dc_name, is_local):
    """
    Description : this method wrapped the datacenters.addDataCenter
    Parameters:
        * is_positive - True if its a positive tests, False otherwise
        * dc_name - name of a data center that should removed
        * is_local - True for localFS DC type, False for shared DC type
    Return: status (True if data center was added properly, False otherwise)
    """
    return datacenters.addDataCenter(
        is_positive,
        name=dc_name,
        local=is_local,
        version=config.COMP_VERSION
    )


def remove_datacenter(dc_name):
    """
    Description : this method wrapped the datacenters.removeDataCenter
    Parameters:
        * dc_name - name of a data center that should removed
    Return: status (True if data center was removed properly, False otherwise)
    """
    return datacenters.removeDataCenter(positive=True, datacenter=dc_name)


@attr(team='automationInfra', tier=1)
class TestCaseDataCenter(TestCase):
    """
    Data Center sanity test the basic operations of data center
    """

    __test__ = True

    dc_name = config.DATA_CENTER_1_NAME

    def test01_create_shared_data_center(self):
        """
        test checks if Create Shared data center works correctly
        """
        logger.info('Create Shared data center')
        status = create_datacenter(True, config.DATA_CENTER_1_NAME, False)
        self.assertTrue(status, 'Create Shared data center')

    def test02_create_temporary_local_data_center(self):
        """
        test checks if Create temporary Local data center works correctly
        """
        logger.info('Create temporary Local data center')
        status = create_datacenter(True, config.DATA_CENTER_2_NAME, True)
        self.assertTrue(status, 'Create temporary Local data center')

    def test03_create_data_center_with_spaces_in_name(self):
        """
        test checks if Create data center with spaces in name failed
        as expected - Negative test
        """
        logger.info('Create data center with spaces in name')
        status = create_datacenter(False, 'No Data Center', True)
        self.assertTrue(status, 'Create data center with spaces in name')

    def test04_create_data_center_with_existing_name(self):
        """
        test checks if Create data center with existing name don't works
        """
        logger.info('Create data center with existing name')
        status = create_datacenter(False, config.DATA_CENTER_2_NAME, True)
        self.assertTrue(status, 'Create data center with existing name')

    def test05_update_data_center_name_and_description(self):
        """
        test checks if Update data center name and description works properly
        """

        logger.info('Update data center name and description')
        status = datacenters.updateDataCenter(
            positive=True, datacenter=config.DATA_CENTER_1_NAME,
            name=config.DATA_CENTER_1_NAME_UPDATED,
            description='Data Center Description')
        self.assertTrue(status, 'Update data center name and description')
        self.__class__.dc_name = config.DATA_CENTER_1_NAME_UPDATED

    def test06_remove_temporary_data_center(self):
        """
        test checks if Remove temporary data center works properly
        """

        logger.info('Remove temporary data center')
        self.assertTrue(remove_datacenter(config.DATA_CENTER_2_NAME),
                        'Remove temporary data center')

    def test07_search_for_data_center(self):
        """
        test if Search for data center works properly
        """
        log_msg = 'Search for %s data center' % self.dc_name
        logger.info(log_msg)
        status = datacenters.searchForDataCenter(positive=True,
                                                 query_key='name',
                                                 query_val=self.dc_name,
                                                 key_name='name')
        self.assertTrue(status, log_msg)

    def test08_remove_few_temporary_data_centers(self):
        """
        test checks if Remove few temporary data centers works properly
        """
        create_datacenter(True, config.DATA_CENTER_2_NAME, True)
        create_datacenter(True, config.DATA_CENTER_3_NAME, True)

        logger.info('Remove few temporary data centers')
        dcs_to_remove = ','.join([self.dc_name,
                                 config.DATA_CENTER_2_NAME,
                                 config.DATA_CENTER_3_NAME])
        status = datacenters.removeDataCenters(positive=True,
                                               datacenters=dcs_to_remove)
        self.assertTrue(status, 'Remove few temporary data centers')
