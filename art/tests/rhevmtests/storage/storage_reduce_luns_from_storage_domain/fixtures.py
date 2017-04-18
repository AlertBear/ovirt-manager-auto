"""
Fixtures for reduce_luns_from_storage_domain module
"""
import pytest
import config
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd
)


@pytest.fixture(scope='class')
def set_disk_params(request):
    """
    Set disk size
    """
    self = request.node.cls

    self.disk_size = ll_sd.get_free_space(
        self.new_storage_domain
    ) - 5 * config.GB
    assert self.disk_size, "Failed to get storage domain %s size" % (
        self.new_storage_domain
    )
    self.storage_domain = self.new_storage_domain
    self.add_disk_params = {'sparse': False, 'format': config.RAW_DISK}
