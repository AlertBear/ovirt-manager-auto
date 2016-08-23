import logging
import traceback

import pytest
from _pytest_art.marks import (
    network,
    sla,
    storage,
    coresystem,
    virt,
    upgrade,
    storages,
)
from _pytest_art.testlogger import TestFlowInterface
from art.test_handler.exceptions import TearDownException
from art.test_handler.settings import ART_CONFIG


logger = logging.getLogger(__name__)
testflow = TestFlowInterface

STORAGE_TYPE = ART_CONFIG['RUN'].get('storage_type')
NOT_APPLICABLE = 'N/A'


# @storages decorator define all storage types available that test can run
# with. NEVER change it here, but in child class, our plugin count that base
# class is decorated with NOT_APPLICABLE.
@storages((NOT_APPLICABLE,))
@pytest.mark.usefixtures('storage')
class BaseTestCase(object):
    """
    Base test case class for unittest testing
    """
    test_failed = False

    @property
    def __name__(self):
        return traceback.extract_stack(None, 2)[0][2]

    # Invokes storage fixture before all fixtures to set storage.
    @pytest.fixture(autouse=True, scope='class')
    def storage_setup(request, storage):
        pass

    @classmethod
    def teardown_exception(cls):
        try:
            if cls.test_failed:
                raise TearDownException("TearDown failed with errors")
        finally:
            cls.test_failed = False

    # current storage type on run time
    storage = None


@pytest.mark.usefixtures("reset_object")
@storage
@storages(set(ART_CONFIG['RUN']['storages']))
class StorageTest(BaseTestCase):
    """
    Basic class for storage tests
    """
    # STORAGE_TYPE value sets type of storage when running
    # without the --with-multiplier flag
    storage = STORAGE_TYPE if STORAGE_TYPE != "none" else 'iscsi'


@network
class NetworkTest(BaseTestCase):
    """
    Basic class for network tests
    """


@virt
class VirtTest(BaseTestCase):
    """
    Basic class for compute/virt tests
    """


@sla
class SlaTest(BaseTestCase):
    """
    Basic class for compute/sla tests
    """


@coresystem
class CoreSystemTest(BaseTestCase):
    """
    Basic class for core system tests
    """


@upgrade
class UpgradeTest(BaseTestCase):
    """
    Basic class for upgrade test
    """
