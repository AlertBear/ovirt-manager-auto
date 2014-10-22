import logging
from functools import wraps
from art.test_handler.settings import plmanager, opts, ART_CONFIG
from rhevmtests import config
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


def golden_env(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        if config.GOLDEN_ENV:
            logger.info("Running on golden env, no setup")
            return
        return f(*args, **kwds)
    return wrapper


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
    # WA: storage will be the type of storage to execute the tests in
    # wait until plugin multiplier is merged to change it
    storage = STORAGE_TYPE if STORAGE_TYPE != "none" else ISCSI


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
