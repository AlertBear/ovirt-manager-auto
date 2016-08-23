import pytest
import logging
from art.test_handler import settings

__all__ = (
    "storage",
)

logger = logging.getLogger("_pytest_art.fixtures")

_storages_defined_in_conf = None


@pytest.fixture(scope='class')
def storage(request):
    def fin():
        if settings.ART_CONFIG['RUN'].get('storage_type'):
            settings.ART_CONFIG['RUN']['storage_type'] = None
            logger.info("******** The storage type reset to None *********")
    request.addfinalizer(fin)
    _storage = getattr(request, 'param', None)
    if isinstance(_storage, basestring):
        if settings.ART_CONFIG['RUN'].get('storage_type') != _storage:
            settings.ART_CONFIG['RUN']['storage_type'] = _storage
            logger.info(
                "********* The storage type switched to %s *********", _storage
            )

    if request.cls:
        request.cls.storage = _storage
    return _storage


@pytest.fixture(scope="class")
def reset_object(request, storage):
    """
    Reset the 'self' object
    """
    self = request.node.cls
    SELF_DIR_SETUP = None

    def fin():
        SELF_DIR_TEAR = dir(self)
        new_attributes = [
            elem for elem in SELF_DIR_TEAR if elem not in SELF_DIR_SETUP
        ]
        for attr in new_attributes:
            delattr(self, attr)
    request.addfinalizer(fin)
    SELF_DIR_SETUP = dir(self)
