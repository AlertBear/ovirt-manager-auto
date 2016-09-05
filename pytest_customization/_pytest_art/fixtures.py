import pytest
from art.test_handler import settings

__all__ = (
    "storage",
    "api",
)


@pytest.fixture(scope='class')
def storage(request):
    if request.cls:
        return request.cls.storage
    return settings.opts['storage_type']


@pytest.fixture(scope='class')
def api(request):
    if request.cls:
        return request.cls.api
    return settings.opts['engine']
