"""
This module contains hooks which allows initialization of ART library.
Briefly said it performs these operations:
    - Initialize ART TestRunnerWrapper
    - Read ART config
    - Process --art-define options
    - Generate DS
    - Download certificates in case of secure connection
    - Load GE yaml in case of GE job
    - Execute custom hook 'pytest_artconf_ready'
    - Execute custom hook 'pytest_art_ensure_resources'
At the end it executes custom hook 'pytest_art_release_resources'


More about CLI options added to pytest for ART purposes.
These are:
    --art-conf path/to/test-config.conf
      It is same as we had --conf in ART - MANDATORY
    --art-spec path/to/test-specification.spec
      It is same as we had --spec in ART - OPTIONAL
    --art-define NAME_OF_SECTION.name_of_option=something
      It is same as we had -D in ART - OPTIONAL
    --art-log path/to/log-file.log
      It is same as we had --log in ART - OPTIONAL
"""
import atexit
import time
import warnings
import signal

import pytest

from art import rhevm_api
from art.core_api.external_api import TestRunnerWrapper
import art.test_handler.settings as settings
from _pytest_art import ssl
from _pytest_art import newhooks


__all__ = [
    "pytest_addhooks",
    "pytest_addoption",
    "pytest_configure",
    "pytest_ignore_collect",
    "pytest_unconfigure",
]


def pytest_addoption(parser):
    """
    Add necessary options to initialize ART library.
    """
    parser.addoption(
        '--art-conf',
        dest='art_conf',
        help="Path to config file to initialize ART library.",
    )
    parser.addoption(
        '--art-define',
        action="append",
        dest="art_define",
        default=[],
        help="Overwite varibale inside of config file. RUN.storages=nfs",
    )
    parser.addoption(
        '--art-log',
        action="store",
        dest="art_log",
        default="/var/tmp/art_tests_%s.log" % time.strftime('%Y%m%d_%H%M%S'),
        help="Specify path to ART logs.",
    )
    parser.addoption(
        '--art-log-conf',
        action="store",
        dest="art_log_conf",
        help="Specify path to ART logger config.",
    )


# To make sure that we call all hooks after all plugins are loaded we run this
# as the last one.
@pytest.mark.trylast
def pytest_configure(config):
    """
    Load ART config files, and initialize ART library.
    """
    if not config.getoption('art_conf'):
        return

    # Print the first occurrence of matching warnings for each location
    # where the warning is issued
    warnings.simplefilter("default")

    config.art_wrapper = TestRunnerWrapper(
        None,
        log=config.getoption('art_log'),
        log_conf=config.getoption('art_log_conf'),
    )
    config.ART_CONFIG = settings.ART_CONFIG
    settings.create_runtime_config(
        config.getoption('art_conf'),
        config.getoption('art_define'),
    )

    # Generate certificates
    if settings.ART_CONFIG['RUN'].get('secure'):
        ssl.configure()

    # Generate Data Structures
    rhevm_api.generate_ds(settings.ART_CONFIG)

    # Let the other plugins know that ART is ready
    config.hook.pytest_artconf_ready(config=config)

    # Give a change to other plugins to instrument resources
    config.hook.pytest_art_ensure_resources(config=config)

    # Watch MainThread and report if it gets stucked.
    settings.stuck_handler()
    signal.signal(signal.SIGUSR1, settings.dump_stacks)

    # Add thread to monitor GC in ART run
    mon_gc = settings.MonitorGC()
    atexit.register(mon_gc.collect_gc)


def pytest_unconfigure(config):
    """
    Release resources
    """
    config.hook.pytest_art_release_resources(config=config)


def pytest_ignore_collect(path, config):
    """
    Ignores all config.py and helpers.py files from test's collection.
    """
    return path.basename in ('config.py', 'helpers.py')


def pytest_addhooks(pluginmanager):
    """
    Add ART's specific hooks
    """
    pluginmanager.add_hookspecs(newhooks)
