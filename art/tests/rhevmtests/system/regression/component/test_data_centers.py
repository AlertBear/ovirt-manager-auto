"""
-----------------
test_data_centers
-----------------

@author: Kobi Hakimi
"""

import logging

from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from rhevmtests import config

logger = logging.getLogger(__name__)


class TestCaseDataCenter(TestCase):
    """
    Data Center sanity test the basic operations of data center
    """
    __test__ = True

    dc_name = config.DC_NAME[0]

    @attr(tier=1)
    def test_create_remove_temporary_local_data_center(self):
        """
        Positive - check Create temporary Local data center functionality
        remove data center if successful
        """
        logger.info('Create temporary Local data center')
        status = ll_dc.addDataCenter(
            True, name='temp_data_center', local=True,
            version=config.COMP_VERSION
        )
        self.assertTrue(status, 'Create temporary Local data center')
        logger.info('Remove temporary data center')
        status = ll_dc.removeDataCenter(
            positive=True, datacenter='temp_data_center'
        )
        self.assertTrue(status, 'Remove temporary data center')

    @attr(tier=2)
    def test_create_data_center_with_spaces_in_name(self):
        """
        Negative - check if Create data center with spaces in name fails
        as expected
        """
        logger.info('Create data center with spaces in name')
        status = ll_dc.addDataCenter(
            False, name='No Data Center', local=True,
            version=config.COMP_VERSION
        )
        self.assertTrue(status, 'Create data center with spaces in name')

    @attr(tier=2)
    def test_create_data_center_with_existing_name(self):
        """
        Negative - check if Create data center with existing name fails
        """
        logger.info('Create data center with existing name')
        status = ll_dc.addDataCenter(
            False, name=self.dc_name, local=True,
            version=config.COMP_VERSION
        )
        self.assertTrue(status, 'Create data center with existing name')

    @attr(tier=1)
    def test_update_data_center_name_and_description(self):
        """
        check if Update data center name and description works properly
        revert the change
        """
        updated_name = self.dc_name + 'updated'
        logger.info('Update data center name and description')
        update_status = ll_dc.updateDataCenter(
            positive=True, datacenter=self.dc_name,
            name=updated_name, description='Data Center Description'
        )
        revert_status = ll_dc.updateDataCenter(
            positive=True, datacenter=updated_name,
            name=self.dc_name, description=''
        )
        self.assertTrue(
            update_status, 'Update data center name and description'
        )
        self.assertTrue(
            revert_status, 'Revert data center name and description'
        )

    @attr(tier=1)
    def test_search_for_data_center(self):
        """
        Positive - Search for data center
        """
        log_msg = 'Search for %s data center' % self.dc_name
        logger.info(log_msg)
        status = ll_dc.searchForDataCenter(
            positive=True, query_key='name',
            query_val=self.dc_name, key_name='name'
        )
        self.assertTrue(status, log_msg)
