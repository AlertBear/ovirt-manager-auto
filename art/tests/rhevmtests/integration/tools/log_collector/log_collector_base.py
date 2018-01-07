"""
Base class for log collector tests
"""
import config
from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import testflow


class LogCollectorTest(TestCase):
    """
    Base class for tests of log collector
    """

    @staticmethod
    def run_ovirt_log_collector():
        """
        Run ovirt-log-collector utility on engine machine
        """
        cmd = [config.LOGCOLLECTOR_UTIL, '--quiet']

        testflow.step("Running ovirt log collector")
        rc, out, err = config.ENGINE_HOST.executor().run_cmd(cmd)
        assert not rc, err
        return out
