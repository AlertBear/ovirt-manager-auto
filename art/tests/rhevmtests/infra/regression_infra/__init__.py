import os

from art.rhevm_api.utils.aaa import copy_extension_file
from art.rhevm_api.utils.test_utils import restart_engine
from art.rhevm_api.tests_lib.high_level import mac_pool as hl_mac_pool

from rhevmtests.infra.regression_infra import config


INSTALLED_FIXTURES = []


def setup_package():
    # Install AAA extension properties
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    for file_ in os.listdir(fixtures_dir):
        ext_file = os.path.join(fixtures_dir, file_)
        target_file = os.path.join(config.ENGINE_EXTENSIONS_DIR, file_)
        copy_extension_file(config.ENGINE_HOST, ext_file, target_file, 'ovirt')
        INSTALLED_FIXTURES.append(target_file)
    restart_engine(config.ENGINE, 5, config.ENGINE_RESTART_TIMEOUT)

    # Update the Default mac pool object with mac range from mac broker
    hl_mac_pool.update_default_mac_pool()


def teardown_package():
    # Wipe out AAA extension properties
    # the global is necessary here because of assignment in this scope
    global INSTALLED_FIXTURES
    if INSTALLED_FIXTURES:
        cmd = ['rm', '-f'] + INSTALLED_FIXTURES
        INSTALLED_FIXTURES = []
        with config.ENGINE_HOST.executor().session() as ss:
            ss.run_cmd(cmd)
    restart_engine(config.ENGINE, 5, config.ENGINE_RESTART_TIMEOUT)
