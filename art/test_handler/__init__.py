import os
from utilities import getConfigFile as locate_file
import art


def __compose_files_location(env_var):
    paths = ['.']
    custom_paths = [x for x in os.environ.get(env_var, '').split(':') if x]
    paths.extend(custom_paths)
    return paths


def __compose_configs_location():
    paths = __compose_files_location('ART_CONFIG_LOCATIONS')
    paths.append(os.path.dirname(art.__file__))
    return paths


def __compose_tests_location():
    paths = __compose_files_location('ART_TEST_LOCATIONS')
    paths.append(os.path.dirname(art.__file__))
    return paths


TEST_LOCATIONS = __compose_tests_location()
CONFIG_LOCATIONS = __compose_configs_location()
TEST_LOCATIONS = __compose_tests_location()


def find_config_file(path):
    return locate_file(path, CONFIG_LOCATIONS)


def find_test_file(path):
    return locate_file(path, TEST_LOCATIONS)
