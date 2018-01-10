"""
Tests for ovirt-log-collector
"""
import time

import pytest

import config
from art.test_handler.tools import polarion
from art.unittest_lib import testflow
from art.unittest_lib import tier1
from log_collector_base import LogCollectorTest


@pytest.fixture(scope='module', autouse=True)
def module_setup(request):
    new_line = 'passwd=%s' % config.REST_CONNECTION['password']
    cmd = [
        'echo', new_line, '>>',
        '%s' % config.CONFIG_FILE_LOCATION
    ]
    testflow.setup("Add admin password to config file")
    config.ENGINE_HOST.executor().run_cmd(cmd)

    def finalizer():
        cmd = [
            'sed', '-i', '/'+new_line+'/d',
            '%s' % config.CONFIG_FILE_LOCATION
        ]
        testflow.teardown("Remove admin password from config file")
        config.ENGINE_HOST.executor().run_cmd(cmd)
        cmd = ['rm', '-f', '/tmp/sosreport-LogCollector-*']
        testflow.teardown("Remove sosreport files from directory")
        config.ENGINE_HOST.executor().run_cmd(cmd)
    request.addfinalizer(finalizer)


@tier1
class TestLogCollector(LogCollectorTest):
    """
    Test log collector without parameters and with one parameter
    """
    @polarion("RHEVM3-8003")
    def test_run(self):
        """ Test log collector with --quiet parameter"""
        self.run_ovirt_log_collector()
        current_date = time.strftime("%Y%m%d")
        testflow.step("Check created file in directory")
        assert config.ENGINE_HOST.fs.exists(
            "/tmp/sosreport-LogCollector-%s*.tar.xz" % current_date
        )
