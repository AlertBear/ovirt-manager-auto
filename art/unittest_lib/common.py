import logging
from unittest2 import TestCase

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

# WA This will be removed after multiplier is merged
ISCSI = ART_CONFIG['elements_conf']['RHEVM Enums']['storage_type_iscsi']
NFS = ART_CONFIG['elements_conf']['RHEVM Enums']['storage_type_nfs']
GLUSTERFS = ART_CONFIG['elements_conf']['RHEVM Enums']['storage_type_gluster']
FCP = ART_CONFIG['elements_conf']['RHEVM Enums']['storage_type_fcp']
CEPH = ART_CONFIG['elements_conf']['RHEVM Enums']['storage_type_ceph']
STORAGE_TYPE = ART_CONFIG['PARAMETERS'].get('storage_type', None)
NOT_APPLICABLE = 'N/A'


class BaseTestCase(TestCase):
    """
    Base test case class for unittest testing
    """
    __test__ = False
    # All APIs available that test can run with
    apis = set(ART_CONFIG['RUN']['engines'])
    test_failed = False

    @classmethod
    def teardown_exception(cls):
        try:
            if cls.test_failed:
                raise TearDownException("TearDown failed with errors")
        finally:
            cls.test_failed = False
    # All storage types available that test can run with
    storages = NOT_APPLICABLE
    # current API on run time
    api = None
    # current storage type on run time
    storage = None


@storage
class StorageTest(BaseTestCase):
    """
    Basic class for storage tests
    """
    __test__ = False

    storages = set([NFS, ISCSI, GLUSTERFS, CEPH, FCP])

    # STORAGE_TYPE value sets type of storage when running
    # without the --with-multiplier flag
    storage = STORAGE_TYPE if STORAGE_TYPE != "none" else ISCSI


@network
class NetworkTest(object):
    """
    Basic class for network tests
    """
    apis = set(["rest", "java", "sdk"])


@virt
class VirtTest(object):
    """
    Basic class for compute/virt tests
    """
    apis = set(["rest", "java", "sdk"])


@sla
class SlaTest(object):
    """
    Basic class for compute/sla tests
    """


@coresystem
class CoreSystemTest(object):
    """
    Basic class for core system tests
    """
    apis = set(["rest", "java", "sdk"])


@coresystem
class IntegrationTest(BaseTestCase):
    """
    Basic class for integration test
    """
    __test__ = False


@upgrade
class UpgradeTest(BaseTestCase):
    """
    Basic class for upgrade test
    """
    __test__ = False
