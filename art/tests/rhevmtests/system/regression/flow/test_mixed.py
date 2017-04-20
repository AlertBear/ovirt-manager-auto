"""
-----------------
test_mixed
-----------------
"""
from art.test_handler.tools import bz
from art.unittest_lib import (
    attr, testflow,
    CoreSystemTest as TestCase,
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
    @attr(tier=1)
    def test_check_product_name(self):
        """
        verify product name
        """
        testflow.step('Check product name')
        assert ll_general.checkProductName(
            product_name
        ), 'Failed to check product name'

    @attr(tier=1)
    def test_check_existing_permissions(self):
        """
        verify users functionality
        check existing permissions
        """
        testflow.step('Check existing permissions')
        assert ll_mla.check_system_permits(
            positive=True
        ), 'Failed to check existing permissions'

    @attr(tier=2)
    @bz({'1303346': {}})
    def test_check_xsd_schema_validations(self):
        """
        verify xsd functionality
        check xsd schema validations
        """
        testflow.step('Check xsd schema validations')
        assert ll_general.checkResponsesAreXsdValid(), (
            'Failed to check xsd schema validations'
        )
