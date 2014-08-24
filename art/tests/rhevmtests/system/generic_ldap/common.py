__test__ = False

import os
import logging

from utilities import machine
from functools import wraps
from art.test_handler.exceptions import SkipTest
from art.rhevm_api.utils import test_utils
from rhevmtests.system.generic_ldap import config


LOGGER = logging.getLogger(__name__)
SKIP_MESSAGE = 'Configuration was not setup for this test. Skipping.'
INTERVAL = 5
ATTEMPTS = 25
TIMEOUT = 70


def enableExtensions():
    ''' just restart ovirt engine service '''
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    test_utils.restartOvirtEngine(machineObj, INTERVAL, ATTEMPTS, TIMEOUT)


def cleanExtDirectory(ext_dir):
    ''' remove all files from extension directory '''
    ext_files = os.path.join(ext_dir, '*')
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    machineObj.removeFile(ext_files)


def prepareExtensions(module_name, ext_dir, extensions, clean=True):
    '''
    prepare all extension for module_name
    Parameters:
        module_name - current test module
        ext_dir - directory where extensions should be prepared
        extensions - dictionary where is stored if setup was successfull
        clean - if True clean $ext_dir before preparing configurations
    '''
    if clean:
        cleanExtDirectory(ext_dir)

    ext_path = os.path.dirname(os.path.abspath(__file__))
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    LOGGER.info(module_name)
    files = os.listdir(os.path.join(ext_path, config.FIXTURES))
    confs = filter(lambda f: f.find(module_name) >= 0, files)
    for conf in confs:
        ext_file = os.path.join(ext_path, config.FIXTURES, conf)
        try:
            assert machineObj.copyTo(ext_file, ext_dir)
            res = machineObj.runCmd(['chown', 'ovirt:ovirt', ext_file])
            assert res[0], res[1]
            LOGGER.info('Configuration "%s" has been copied.', conf)
            extensions[conf] = True
        except AssertionError as e:
            LOGGER.error('Configuration "%s" has NOT been copied. Tests with '
                         'this configuration will be skipped. %s', conf, e)
            extensions[conf] = False

    enableExtensions()


# Check if extension was correctly copied, and could be tested.
def check(ext=None):
    def decorator(method):
        @wraps(method)
        def f(self, *args, **kwargs):
            if ext and not ext.get(self.conf['authn_file'], False):
                LOGGER.warn(SKIP_MESSAGE)
                raise SkipTest(SKIP_MESSAGE)
            return method(self, *args, **kwargs)
        return f
    return decorator
