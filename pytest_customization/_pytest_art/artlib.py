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
import time
import yaml
import signal
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
    parser.addoption(
        '--art-log-conf',
        action="store",
        dest="art_log_conf",
        default="conf/logger_art.yaml",
        help="Specify path to ART logger config.",
    )


def pytest_configure(config):
    """
    Load ART config files, and initialize ART library.
    """
    if not config.getoption('art_conf'):
        return

    config.art_wrapper = TestRunnerWrapper(
        None,
        log=config.getoption('art_log'),
        log_conf=config.getoption('art_log_conf'),
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

    # Watch MainThread and report if it gets stucked.
    settings.stuck_handler()
    signal.signal(signal.SIGUSR1, settings.dump_stacks)


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
