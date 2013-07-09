import os
from utilities import getConfigFile
import art


def __compose_files_location(env_var):
    paths = ['.']
    custom_paths = [x for x in os.environ.get(env_var, '').split(':') if x]
    paths.extend(custom_paths)
#    paths.append('/opt/art')
    return paths


def __compose_configs_location():
    paths = __compose_files_location('ART_CONFIG_LOCATIONS')
#    paths.append('/opt/art/conf')
    paths.append(os.path.dirname(art.__file__))
    return paths


def __compose_tests_location():
    paths = __compose_files_location('ART_TEST_LOCATIONS')
#    paths.append('/opt/art/tests')
    paths.append(os.path.dirname(art.__file__))
    return paths


CONFIG_LOCATIONS = __compose_configs_location()
TEST_LOCATIONS = __compose_tests_location()


def find_config_file(path):
    return getConfigFile(path, CONFIG_LOCATIONS)


def find_test_file(path):
    return getConfigFile(path, TEST_LOCATIONS)

