"""
-----------------
test_storage_domain
-----------------
"""
from art.unittest_lib import (
    attr, testflow,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd

from rhevmtests.config import (
    DATA_DOMAIN_ADDRESSES as data_domain_addresses,
    DATA_DOMAIN_PATHS as data_domain_paths,
    ENUMS as enums,
    HOSTS as hosts,
    STORAGE_NAME as storages_names,
)


class TestCaseStorageDomain(TestCase):
    """
    Storage domain tests
    """
    __test__ = True

    sd_name = storages_names[0]

    @attr(tier=2)
    def test_create_storage_domain_wrong_type(self):
        """
        Negative - verify storage domain functionality
        add a storage domain with wrong type & verify failure
        """
        testflow.step('Add storage domain')
        assert ll_sd.addStorageDomain(
            positive=False,
            type='bad_config',
            name=self.sd_name,
            storage_type=enums['storage_type_nfs'],
            address=data_domain_addresses[0],
            host=hosts[0],
            path=data_domain_paths[0]
        )

    @attr(tier=1)
    def test_update_storage_domain(self):
        """
        Positive - verify storage domain functionality
        update storage domain name and revert to original
        """
        new_name = self.sd_name + 'Updated'

        testflow.step('Update storage domain')
        assert ll_sd.updateStorageDomain(
            positive=True,
            storagedomain=self.sd_name,
            name=new_name
        )

        testflow.step("Reverting storage domain")
        assert ll_sd.updateStorageDomain(
            positive=True,
            storagedomain=new_name,
            name=self.sd_name
        )
