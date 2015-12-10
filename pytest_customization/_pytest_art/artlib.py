"""
This module contains hooks which allows initialization of ART library.
"""
import time
import yaml
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
        required=True,
        dest='art_conf',
        help="Path to config file to initialize ART library.",
    )
    parser.addoption(
        '--art-spec',
        default='conf/specs/main.spec',
        dest='art_spec',
        help="Path to config file containing default values for ART library.",
    )
    parser.addoption(
        '--art-define',
        action="append",
        dest="art_define",
        default=[],
        help="Overwite varibale inside of config file. RUN.system_engine=rest",
    )
    parser.addoption(
        '--art-log',
        action="store",
        dest="art_log",
        default="/var/tmp/art_tests_%s.log" % time.strftime('%Y%m%d_%H%M%S'),
        help="Specify path to ART logs.",
    )


def pytest_configure(config):
    """
    Load ART config files, and initialize ART library.
    """
    config.art_wrapper = TestRunnerWrapper(
        None,
        log=config.getoption('art_log'),
    )
    config.ART_CONFIG = settings.ART_CONFIG
    settings.opts['confSpec'] = config.getoption('art_spec')
    settings.readTestRunOpts(
        config.getoption('art_conf'),
        config.getoption('art_define'),
    )
    # Generate Data Structures
    rhevm_api.generate_ds(settings.ART_CONFIG)

    # Generate certificates
    if settings.ART_CONFIG['RUN'].as_bool('secure'):
        ssl.configure()

    # Load GE config if relevant
    ge_path = settings.ART_CONFIG['RUN'].get('golden_environment', None)
    if ge_path:
        with open(ge_path, "r") as handle:
            env_definition = yaml.load(handle)
        settings.ART_CONFIG['prepared_env'] = env_definition

    # Let the other plugins know that ART is ready
    config.hook.pytest_artconf_ready(config=config)

    # Give a change to other plugins to instrument resources
    config.hook.pytest_art_ensure_resources(config=config)


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