import pytest
import logging
import config
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sds,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def get_storage_domain_size(request):
    """
    Get storage domain size
    """
    self = request.node.cls

    self.domain_size = ll_sds.get_total_size(self.new_storage_domain)
    logger.info(
        "Total size for domain '%s' is '%s'",
        self.new_storage_domain, self.domain_size
    )


@pytest.fixture(scope='class')
def prepare_storage_parameters(request):
    """
    Prepare storage parameters
    """
    self = request.node.cls

    self.disk_count = 0
    self.formats = [config.COW_DISK, config.RAW_DISK]
    self.num_of_disks = 2

    self.domains = list()
    for storage_type in config.STORAGE_SELECTOR:
        self.domains.append(
            ll_sds.getStorageDomainNamesForType(
                config.DATA_CENTER_NAME, storage_type
            )[0]
        )
