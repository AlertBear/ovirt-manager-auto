import logging
from art.test_handler.exceptions import TearDownException
from art.test_handler.settings import plmanager, opts, ART_CONFIG
from unittest import TestCase
from nose.plugins.attrib import attr
logger = logging.getLogger(__name__)

# WA This will be removed after multiplier is merged
ISCSI = opts['elements_conf']['RHEVM Enums']['storage_type_iscsi']
STORAGE_TYPE = ART_CONFIG['PARAMETERS'].get('storage_type', None)

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
    apis = set(opts['engines'])
    test_failed = False

    def teardown_exception(self):
        if self.test_failed:
            raise TearDownException("TearDown failed with errors")


@attr(team="storage")
class StorageTest(BaseTestCase):
    """
    Basic class for storage tests
    """
    __test__ = False
    # WA: storage will be the type of storage to execute the tests in
    # wait until plugin multiplier is merged to change it
    storage = STORAGE_TYPE if STORAGE_TYPE != "none" else ISCSI


@attr(team="network")
class NetworkTest(BaseTestCase):
    """
    Basic class for network tests
    """
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


@attr(team="CoreSystem")
class CoreSystemTest(BaseTestCase):
    """
    Basic class for core system tests
    """
    __test__ = False
