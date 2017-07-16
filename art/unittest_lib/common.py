import logging
from unittest2 import TestCase  # only storage tests uses unittest2

from _pytest_art.marks import (
    network,
    sla,
    storage,
    coresystem,
    virt,
    upgrade,
)
from _pytest_art.testlogger import TestFlowInterface
from art.test_handler.exceptions import TearDownException
from art.test_handler.settings import ART_CONFIG

logger = logging.getLogger(__name__)
testflow = TestFlowInterface

STORAGE_TYPE = ART_CONFIG['RUN'].get('storage_type')
NOT_APPLICABLE = 'N/A'


class BaseTestCase(object):
    """
    Base test case class for unittest testing
    """
    # All APIs available that test can run with
    apis = set(ART_CONFIG['RUN']['engines'])
    # All storage types available that test can run with
    storages = NOT_APPLICABLE
    # current API on run time
    api = None
    # current storage type on run time
    storage = None


@storage
class StorageTest(TestCase):
    """
    Basic class for storage tests
    """
    __test__ = False

    apis = set(ART_CONFIG['RUN']['engines'])
    storages = set(ART_CONFIG['RUN']['storages'])
    test_failed = False

    @classmethod
    def teardown_exception(cls):
        try:
            if cls.test_failed:
                raise TearDownException("TearDown failed with errors")
        finally:
            cls.test_failed = False
    # STORAGE_TYPE value sets type of storage when running
    # without the --with-multiplier flag
    storage = STORAGE_TYPE if STORAGE_TYPE != "none" else 'iscsi'
    # current API on run time
    api = None


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


@coresystem
class IntegrationTest(BaseTestCase):
    """
    Basic class for integration test
    """


@upgrade
class UpgradeTest(BaseTestCase):
    """
    Basic class for upgrade test
    """
