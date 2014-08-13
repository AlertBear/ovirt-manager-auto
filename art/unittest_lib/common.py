import logging
from functools import wraps
from art.test_handler.settings import plmanager, opts
from art.test_handler.exceptions import SkipTest
from unittest import TestCase
from nose.plugins.attrib import attr

logger = logging.getLogger(__name__)

try:
    BZ_PLUGIN = [pl for pl in plmanager.configurables
                 if pl.name == "Bugzilla"][0]
except IndexError:
    class FakeBZPlugin(object):
        def __init__(self):
            self.const_list = None

        def is_state(self, *args):
            """
            Set all BZs as solved if BZ plugin is not available
            """
            return True
    BZ_PLUGIN = FakeBZPlugin()


def bz(bug_dict):
    """
    Decorator function to skip test case, when we have opened bug for it.

    :param bug_dict: mapping bug to engine.
    :type bug_dict: dictionary.
    :raises: SkipTest
    :returns: function object
    """
    def real_bz(func):
        # noinspection PyUnusedLocal
        @wraps(func)
        def skip_if_bz(*args, **kwargs):
            for bz_id, engine in bug_dict.iteritems():
                engine_in = engine is None or opts['engine'] in engine
                if not is_bz_state(bz_id) and engine_in:
                    logger.warn("Skipping test because BZ%s for engine %s",
                                bz_id, opts['engine'])
                    raise SkipTest("BZ%s" % bz_id)
            return func(*args, **kwargs)
        return skip_if_bz
    return real_bz


def is_bz_state(bz_id):
    """
    Description: Decides if bz given by bz_id is in one of states given by
    const_list (CLOSED, VERIFIED) by default or taken from config file
    Parameters:
        * bz_id - BZ number
    """
    return BZ_PLUGIN.is_state(bz_id, BZ_PLUGIN.const_list)


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