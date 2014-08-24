import logging
from art.test_handler.settings import plmanager, opts
from unittest import TestCase
from nose.plugins.attrib import attr

logger = logging.getLogger(__name__)

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


@attr(team="storage")
class StorageTest(BaseTestCase):
    """
    Basic class for storage tests
    """
    __test__ = False


@attr(team="network")
class NetworkTest(BaseTestCase):
    """
    Basic class for network tests
    """
    __test__ = False


@attr(team="compute")
class ComputeTest(BaseTestCase):
    """
    Basic class for compute tests
    """
    __test__ = False


@attr(team="CoreSystem")
class CoreSystemTest(BaseTestCase):
    """
    Basic class for core system tests
    """
    __test__ = False