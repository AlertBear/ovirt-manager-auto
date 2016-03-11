import datetime
import logging
from art.test_handler.exceptions import TearDownException
from art.test_handler.settings import plmanager, opts, ART_CONFIG
from unittest import TestCase
from _pytest_art.marks import attr
try:
    from unittest import SkipTest
except ImportError:
    from unittest2 import SkipTest

logger = logging.getLogger(__name__)

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


def skip_class_if(condition, reason, instance_func_l=None, class_func_l=None):
    """
    Skip run of test class, because of specific reason

    :param condition: skip test condition
    :type condition: bool
    :param reason: skip reason
    :type reason: str
    :param instance_func_l: list of instance methods
    to replace with fake method
    :type instance_func_l: list
    :param class_func_l: list of class methods
    to replace with class method
    :type class_func_l: list
    :return: wrapped class
    :rtype: class
    """
    if not class_func_l:
        class_func_l = ['setup_class', 'teardown_class']
    if not instance_func_l:
        instance_func_l = ['setUp', 'tearDown']

    def wrapper(cls):
        if condition:
            def fake_func_self(self):
                raise SkipTest(reason)

            def fake_func_cls(cls):
                logger.warning(reason)

            for func in instance_func_l:
                setattr(cls, func, fake_func_self)

            for func in class_func_l:
                setattr(cls, func, classmethod(fake_func_cls))
        return cls

    return wrapper


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


@attr(team="network")
class NetworkTest(BaseTestCase):
    """
    Basic class for network tests
    """
    __test__ = False

    apis = set(["rest", "java", "sdk"])


@attr(team="virt")
class VirtTest(BaseTestCase):
    """
    Basic class for compute/virt tests
    """
    __test__ = False


@attr(team="sla")
class SlaTest(BaseTestCase):
    """
    Basic class for compute/sla tests
    """
    __test__ = False


@attr(team="coresystem")
class CoreSystemTest(BaseTestCase):
    """
    Basic class for core system tests
    """
    __test__ = False


@attr(team="integration")
class IntegrationTest(BaseTestCase):
    """
    Basic class for integration test
    """
    __test__ = False
