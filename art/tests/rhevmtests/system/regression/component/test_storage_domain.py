"""
-----------------
test_storage_domain
-----------------

@author: Nelly Credi
"""

import logging

from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd

from rhevmtests import config

logger = logging.getLogger(__name__)


class TestCaseStorageDomain(TestCase):
    """
    Storage domain tests
    """
    __test__ = True

    sd_name = config.STORAGE_NAME[0]

    @attr(tier=2)
    def test_create_storage_domain_wrong_type(self):
        """
        Negative - verify storage domain functionality
        add a storage domain with wrong type & verify failure
        """
        logger.info('Add storage domain')
        status = ll_sd.addStorageDomain(
            positive=False, type='bad_config', name=self.sd_name,
            storage_type=config.ENUMS['storage_type_nfs'],
            address=config.DATA_DOMAIN_ADDRESSES[0], host=config.HOSTS[0],
            path=config.DATA_DOMAIN_PATHS[0]
        )
        assert status, 'Add storage domain'

    @attr(tier=1)
    def test_update_storage_domain(self):
        """
        Positive - verify storage domain functionality
        update storage domain name and revert to original
        """
        logger.info('Update storage domain')
        new_name = self.sd_name + 'Updated'
        status = ll_sd.updateStorageDomain(
            positive=True, storagedomain=self.sd_name, name=new_name
        )
        assert status, 'Update storage domain'
        status = ll_sd.updateStorageDomain(
            positive=True, storagedomain=new_name, name=self.sd_name
        )
        assert status, 'Revert storage domain'
