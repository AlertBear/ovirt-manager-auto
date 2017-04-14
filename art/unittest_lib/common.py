import logging
from unittest2 import TestCase

from _pytest_art.marks import (
    attr,
    network,
    sla,
    storage,
    coresystem,
    virt,
    integration,
    upgrade,
)
from _pytest_art.testlogger import TestFlowInterface
from art.test_handler.exceptions import TearDownException
from art.test_handler.settings import opts, ART_CONFIG

logger = logging.getLogger(__name__)
testflow = TestFlowInterface

# WA This will be removed after multiplier is merged
ISCSI = opts['elements_conf']['RHEVM Enums']['storage_type_iscsi']
NFS = opts['elements_conf']['RHEVM Enums']['storage_type_nfs']
GLUSTERFS = opts['elements_conf']['RHEVM Enums']['storage_type_gluster']
FCP = opts['elements_conf']['RHEVM Enums']['storage_type_fcp']
CEPH = opts['elements_conf']['RHEVM Enums']['storage_type_ceph']
STORAGE_TYPE = ART_CONFIG['PARAMETERS'].get('storage_type', None)
NOT_APPLICABLE = 'N/A'


class BaseTestCase(TestCase):
    """
    Base test case class for unittest testing
    """
    __test__ = False
    # All APIs available that test can run with
    apis = set(opts['engines'])
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
@attr(team="storage")
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
@attr(team="network")
class NetworkTest(object):
    """
    Basic class for network tests
    """
    apis = set(["rest", "java", "sdk"])


@virt
@attr(team="virt")
class VirtTest(object):
    """
    Basic class for compute/virt tests
    """
    apis = set(["rest", "java", "sdk"])


@sla
@attr(team="sla")
class SlaTest(object):
    """
    Basic class for compute/sla tests
    """


@coresystem
@attr(team="coresystem")
class CoreSystemTest(BaseTestCase):
    """
    Basic class for core system tests
    """
    __test__ = False


@integration
@attr(team="integration")
class IntegrationTest(BaseTestCase):
    """
    Basic class for integration test
    """
    __test__ = False


@upgrade
@attr(team="upgrade", tier="upgrade")
class UpgradeTest(BaseTestCase):
    """
    Basic class for upgrade test
    """
    __test__ = False
