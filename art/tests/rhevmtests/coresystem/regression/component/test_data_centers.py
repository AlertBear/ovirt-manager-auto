"""
-----------------
test_data_centers
-----------------
"""

import logging

from art.unittest_lib import (
    CoreSystemTest as TestCase,
    testflow,
    tier1,
    tier2,
)
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from rhevmtests.config import (
    COMP_VERSION as comp_version,
    DC_NAME as dcs_names
)

logger = logging.getLogger(__name__)


class TestCaseDataCenter(TestCase):
    """
    Data Center sanity test the basic operations of data center
    """
    dc_name = dcs_names[0]
    tmp_dc_name = "temp_data_center"

    @tier1
    def test_create_remove_temporary_local_data_center(self):
        """
        Positive - check Create temporary Local data center functionality
        remove data center if successful
        """
        testflow.step('Create temporary Local data center')
        assert ll_dc.addDataCenter(
            positive=True,
            name=self.tmp_dc_name,
            local=True,
            version=comp_version
        )

        testflow.step('Remove temporary data center')
        assert ll_dc.remove_datacenter(
            positive=True,
            datacenter=self.tmp_dc_name
        )

    @tier2
    def test_create_data_center_with_spaces_in_name(self):
        """
        Negative - check if Create data center with spaces in name fails
        as expected
        """
        testflow.step('Create data center with spaces in name')
        assert ll_dc.addDataCenter(
            positive=False,
            name='No Data Center',
            local=True,
            version=comp_version
        )

    @tier2
    def test_create_data_center_with_existing_name(self):
        """
        Negative - check if Create data center with existing name fails
        """
        testflow.step('Create data center with existing name')
        assert ll_dc.addDataCenter(
            positive=False,
            name=self.dc_name,
            local=True,
            version=comp_version
        )

    @tier1
    def test_update_data_center_name_and_description(self):
        """
        check if Update data center name and description works properly
        revert the change
        """
        updated_name = self.dc_name + 'updated'

        testflow.step('Update data center name and description')
        assert ll_dc.update_datacenter(
            positive=True,
            datacenter=self.dc_name,
            name=updated_name,
            description='Data Center Description'
        )
        assert ll_dc.update_datacenter(
            positive=True,
            datacenter=updated_name,
            name=self.dc_name,
            description=''
        )

    @tier1
    def test_search_for_data_center(self):
        """
        Positive - Search for data center
        """
        testflow.step("Searching for %s data center", self.dc_name)
        assert ll_dc.searchForDataCenter(
            positive=True,
            query_key='name',
            query_val=self.dc_name,
            key_name='name'
        )
