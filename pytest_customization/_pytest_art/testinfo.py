"""
This module is responsible to collect some test information,
e.x testname, tier, team, execution times into a yaml file
"""
import yaml
import os
import pytest
from _pytest._code.code import ExceptionInfo

import marks

__all__ = [
    "pytest_addoption",
    "pytest_configure",
]


class LogTestInfo(object):
    """
    Collection of pytest item and reporter related hooks.
    We will gather all information we need for the logs
    and generate the logs here.
    """
    def __init__(self):
        self.statistics = dict()

    def pytest_runtest_makereport(self, item, call):
        if item.nodeid not in self.statistics:
            self.statistics[item.nodeid] = dict()
            self.statistics[item.nodeid]['testname'] = item.nodeid
            self.statistics[item.nodeid]['tier'] = marks.get_item_tier(item)
            self.statistics[item.nodeid]['team'] = marks.get_item_team(item)
            for when in ('setup', 'call', 'teardown'):
                self.statistics[item.nodeid][when] = (
                    {
                        'duration': 0.0,
                        'outcome': None
                    }
                )

        if not call.excinfo:
            outcome = "passed"
        else:
            if not isinstance(call.excinfo, ExceptionInfo):
                outcome = "failed"
            elif call.excinfo.errisinstance(pytest.skip.Exception):
                outcome = "skipped"
            else:
                outcome = "failed"
        self.statistics[item.nodeid][call.when]['outcome'] = outcome

        time = call.stop-call.start
        self.statistics[item.nodeid][call.when]['duration'] = time

    def pytest_sessionfinish(self, session):
        if not session.config.option.testinfo:
            return
        output = yaml.dump(self.statistics.values(),
                           explicit_start=True,
                           default_flow_style=False)
        testinfofile = session.config.option.testinfofile
        if testinfofile is not None:
            dirname = os.path.dirname(os.path.abspath(testinfofile))
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(testinfofile, 'w') as logfile:
                logfile.write(output)
        else:
            tr = session.config.pluginmanager.getplugin('terminalreporter')
            if tr:
                tr.write_line(output)


def pytest_addoption(parser):
    parser.addoption(
        '--testinfo', dest="testinfo", action="store_true", default=False,
        help="show some test info into yaml format",
    )
    parser.addoption(
        '--testinfofile', type=str, default=None, metavar="path",
        help="create a yaml style report file at given path (only valid when "
        "testinfo option is enabled)"
    )


def pytest_configure(config):
    """
    Load the test logging plugin into pytest
    """
    if not config.option.testinfo:
        return
    config.pluginmanager.register(LogTestInfo())
