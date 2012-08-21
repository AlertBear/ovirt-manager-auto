import os

from utilities import getConfigFile
import art

CONFIG_LOCATIONS = ('.', '/opt/art', '/opt/art/conf', os.path.dirname(art.__file__))
TEST_LOCATIONS = ('.', '/opt/art', '/opt/art/tests', os.path.dirname(art.__file__))

def find_config_file(path):
    return getConfigFile(path, CONFIG_LOCATIONS)


def find_test_file(path):
    return getConfigFile(path, TEST_LOCATIONS)

