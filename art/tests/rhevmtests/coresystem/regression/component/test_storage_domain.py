"""
-----------------
test_storage_domain
-----------------
"""
import pytest

from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    testflow,
    tier1,
    tier2,
)

from rhevmtests.config import (
    DATA_DOMAIN_ADDRESSES as data_domain_addresses,
    DATA_DOMAIN_PATHS as data_domain_paths,
    ENUMS as enums,
    HOSTS as hosts,
    STORAGE_NAME as storages_names,
    DC_NAME as datacenters_names,
    SD_ACTIVE as active_status
)


def skip_if_sd_is_not_active(sd_name):
    """
    Kindly asks pytest to skip test if storage domain is not active.

    Args:
        sd_name (str): Name of storage domain to check.
    """
    try:
        ll_sd.wait_for_storage_domain_status(
            True, datacenters_names[0], sd_name, active_status, time_out=60
        )
    except APITimeout:
        pytest.skip(
            "Skipped because storage domain '{}' is not active.".format(
                sd_name
            )
        )


class TestCaseStorageDomain(TestCase):
    """
    Storage domain tests
    """
    sd_name = storages_names[0]
    new_sd_name = sd_name + 'Updated'

    @tier2
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

    @tier1
    def test_update_storage_domain(self):
        """
        Positive - verify storage domain functionality
        update storage domain name and revert to original
        """
        testflow.step('Update storage domain')
        skip_if_sd_is_not_active(self.sd_name)
        assert ll_sd.updateStorageDomain(
            positive=True,
            storagedomain=self.sd_name,
            name=self.new_sd_name
        )

        testflow.step("Reverting storage domain")
        skip_if_sd_is_not_active(self.new_sd_name)
        assert ll_sd.updateStorageDomain(
            positive=True,
            storagedomain=self.new_sd_name,
            name=self.sd_name
        )
