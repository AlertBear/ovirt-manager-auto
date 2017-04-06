"""
Unittest lib fixtures
"""
import pytest


@pytest.fixture(scope='class')
def skip_invalid_storage_type(request):
    """
    Skip the test case if the storage type is not valid for it
    """
    self = request.node.cls

    if self.storage not in self.storages:
        pytest.skip(
            "Storage type %s is not valid for testing this case" % self.storage
        )
