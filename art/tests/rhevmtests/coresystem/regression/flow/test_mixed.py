"""
-----------------
test_mixed
-----------------
"""
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    testflow,
    tier1,
    tier2,
)
from art.rhevm_api.tests_lib.low_level import (
    general as ll_general,
    mla as ll_mla,
)
from rhevmtests.config import PRODUCT_NAME as product_name


class TestCaseMixed(TestCase):
    """
    Scenario tests
    """
    @tier1
    def test_check_product_name(self):
        """
        verify product name
        """
        testflow.step('Check product name')
        assert ll_general.checkProductName(
            product_name
        ), 'Failed to check product name'

    @tier1
    def test_check_existing_permissions(self):
        """
        verify users functionality
        check existing permissions
        """
        testflow.step('Check existing permissions')
        assert ll_mla.check_system_permits(
            positive=True
        ), 'Failed to check existing permissions'

    @tier2
    def test_check_xsd_schema_validations(self):
        """
        verify xsd functionality
        check xsd schema validations
        """
        testflow.step('Check xsd schema validations')
        assert ll_general.checkResponsesAreXsdValid(), (
            'Failed to check xsd schema validations'
        )
