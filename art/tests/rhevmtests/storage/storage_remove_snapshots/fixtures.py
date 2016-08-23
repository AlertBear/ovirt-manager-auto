from rhevmtests.storage import config
import logging
import pytest
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
)
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def initialize_params(request, storage):
    """
    Initialize parameters
    """
    self = request.node.cls

    self.snapshot_list = list()
    self.host = getattr(self, 'host', None)
    self.spm = ll_hosts.get_spm_host([
        host for host in config.HOSTS if self.host != host
    ])
    self.snapshot_description = storage_helpers.create_unique_object_name(
        self.test_case, config.OBJECT_TYPE_SNAPSHOT
    )


@pytest.fixture(scope='class')
def initialize_params_new_dc(request, storage):
    """
    Initialize storage_domain attribute
    """
    self = request.node.cls

    if self.new_storage_domain:
        self.storage_domain = self.new_storage_domain
