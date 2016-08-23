import pytest
import config
from rhevmtests.storage import helpers as storage_helpers


@pytest.fixture(scope='class')
def initialize_template_name(request, storage):
    """
    Initialize template name for test
    """

    self = request.node.cls

    self.template_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_TEMPLATE
    )
