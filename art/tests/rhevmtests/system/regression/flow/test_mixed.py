"""
-----------------
test_mixed
-----------------

@author: Nelly Credi
"""

import logging

from art.test_handler.tools import bz
from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import (
    general as ll_general,
    mla as ll_mla,
)
from rhevmtests import config

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


class TestCaseMixed(TestCase):
    """
    Scenario tests
    """
    __test__ = True

    @attr(tier=1)
    def test_check_product_name(self):
        """
        verify product name
        """
        logger.info('Check product name')
        status = ll_general.checkProductName(config.PRODUCT_NAME)
        self.assertTrue(status, 'Failed to check product name')

    @attr(tier=1)
    @bz({'1367400': {}})
    def test_check_existing_permissions(self):
        """
        verify users functionality
        check existing permissions
        """
        logger.info('Check existing permissions')
        status = ll_mla.checkSystemPermits(positive=True)
        self.assertTrue(status, 'Failed to check existing permissions')

    @attr(tier=2)
    @bz({'1303346': {}})
    def test_check_xsd_schema_validations(self):
        """
        verify xsd functionality
        check xsd schema validations
        """
        logger.info('Check xsd schema validations')
        status = ll_general.checkResponsesAreXsdValid()
        self.assertTrue(status, 'Failed to check xsd schema validations')
