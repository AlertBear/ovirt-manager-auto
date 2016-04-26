import datetime
import logging

from unittest2 import TestCase

from _pytest_art.marks import attr
from _pytest_art.marks import (
    network,
    sla,
    storage,
    coresystem,
    virt,
    integration,
)
from _pytest_art.testlogger import TestFlowInterface
from art.test_handler.exceptions import TearDownException
from art.test_handler.settings import plmanager, opts, ART_CONFIG

logger = logging.getLogger(__name__)
testflow = TestFlowInterface

# WA This will be removed after multiplier is merged
ISCSI = opts['elements_conf']['RHEVM Enums']['storage_type_iscsi']
NFS = opts['elements_conf']['RHEVM Enums']['storage_type_nfs']
GLUSTERFS = opts['elements_conf']['RHEVM Enums']['storage_type_gluster']
FCP = opts['elements_conf']['RHEVM Enums']['storage_type_fcp']
STORAGE_TYPE = ART_CONFIG['PARAMETERS'].get('storage_type', None)
NOT_APPLICABLE = 'N/A'

try:
    BZ_PLUGIN = [pl for pl in plmanager.configurables
                 if pl.name == "Bugzilla"][0]
except IndexError:
    class FakeBZPlugin(object):

        def is_state(self, *args):
            """
            Set all BZs as solved if BZ plugin is not available
            """
            return True

    BZ_PLUGIN = FakeBZPlugin()


def is_bz_state(bz_id):
    """
    Description: Decides if bz given by bz_id is in one of states given by
    const_list (CLOSED, VERIFIED) by default or taken from config file
    Parameters:
        * bz_id - BZ number
    """
    return BZ_PLUGIN.is_state(bz_id)


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
        if cls.test_failed:
            raise TearDownException("TearDown failed with errors")
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

    storages = set([NFS, ISCSI, GLUSTERFS, FCP])

    # STORAGE_TYPE value sets type of storage when running
    # without the --with-multiplier flag
    storage = STORAGE_TYPE if STORAGE_TYPE != "none" else ISCSI

    def create_unique_object_name(self, object_type):
        """
        Creates a unique object name by using the calling class name and the
        current date/time string. This can be used for any objects such as
        VMs, disks, clusters etc.

        __author__ = 'glazarov'
        :param object_type: The type of object for which the unique name
        will be created. For example: vm, disk, sd
        :type object_type: str
        :return: Returns a unique name utilizing the object_type and the
        current class name, plus the current formatted date/time stamp
        :rtype: str
        """
        current_date_time = (
            datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        return "{0}_{1}_{2}".format(
            object_type, self.__class__.__name__, current_date_time
        )


@network
@attr(team="network")
class NetworkTest(BaseTestCase):
    """
    Basic class for network tests
    """
    __test__ = False

    apis = set(["rest", "java", "sdk"])


@virt
@attr(team="virt")
class VirtTest(BaseTestCase):
    """
    Basic class for compute/virt tests
    """
    __test__ = False


@sla
@attr(team="sla")
class SlaTest(BaseTestCase):
    """
    Basic class for compute/sla tests
    """
    __test__ = False


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
