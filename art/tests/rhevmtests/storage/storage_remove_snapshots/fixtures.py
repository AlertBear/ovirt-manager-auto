from rhevmtests.storage import config
import logging
import pytest
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
)
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def initialize_params(request):
    """
    Initialize parameters
    """
    self = request.node.cls

    self.snapshot_list = list()
    self.spm = ll_hosts.getSPMHost(config.HOSTS)
    self.snapshot_description = storage_helpers.create_unique_object_name(
        self.test_case, config.OBJECT_TYPE_SNAPSHOT
    )
